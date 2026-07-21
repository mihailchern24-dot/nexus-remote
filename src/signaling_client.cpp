#include "../include/socket_utils.h"
#include "../include/websocket_utils.h"
#include "../include/gamepad_manager.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <atomic>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <cctype>

static std::string read_http_response(socket_t s) {
    std::string response;
    char buf[512];
    while (response.find("\r\n\r\n") == std::string::npos) {
        int n = recv(s, buf, sizeof(buf), 0);
        if (n <= 0) return {};
        response.append(buf, n);
    }
    return response;
}

static bool send_websocket_upgrade(socket_t s, const std::string &host) {
    std::string request =
        "GET /ws HTTP/1.1\r\n"
        "Host: " + host + "\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n";
    return send(s, request.data(), (int)request.size(), 0) == (int)request.size();
}

static bool send_frame(socket_t s, const std::string &message) {
    std::string frame = build_websocket_frame(message, true);
    return send(s, frame.data(), (int)frame.size(), 0) == (int)frame.size();
}

static bool receive_message(socket_t s, std::string &out) {
    char buffer[4096];
    int n = recv(s, buffer, sizeof(buffer), 0);
    if (n <= 0) return false;
    std::string raw(buffer, n);
    out = read_websocket_payload(raw);
    return true;
}

static std::string make_sdp_offer(const std::string &local_id, const std::string &remote_id) {
    return "v=0\r\n"
           "o=" + local_id + " 0 0 IN IP4 127.0.0.1\r\n"
           "s=NexusRemote\r\n"
           "t=0 0\r\n"
           "m=application 9 DTLS/SCTP 5000\r\n"
           "c=IN IP4 0.0.0.0\r\n"
           "a=ice-ufrag:local\r\n"
           "a=ice-pwd:localpwd\r\n"
           "a=mid:0\r\n"
           "a=sendrecv\r\n"
           "a=peer:" + remote_id + "\r\n";
}

static std::string make_sdp_answer(const std::string &local_id, const std::string &remote_id) {
    return "v=0\r\n"
           "o=" + local_id + " 0 0 IN IP4 127.0.0.1\r\n"
           "s=NexusRemote\r\n"
           "t=0 0\r\n"
           "m=application 9 DTLS/SCTP 5000\r\n"
           "c=IN IP4 0.0.0.0\r\n"
           "a=ice-ufrag:local\r\n"
           "a=ice-pwd:localpwd\r\n"
           "a=mid:0\r\n"
           "a=sendrecv\r\n"
           "a=peer:" + remote_id + "\r\n"
           "a=rtpmap:96 VP8/90000\r\n";
}

static bool parse_server_message(const std::string &message, std::string &from, std::string &command, std::string &payload) {
    std::istringstream iss(message);
    std::string prefix;
    iss >> prefix;
    if (prefix != "FROM") return false;
    iss >> from >> command;
    size_t length = 0;
    iss >> length;
    size_t split = message.find('\n');
    if (split == std::string::npos) return false;
    payload = message.substr(split + 1);
    return payload.size() == length;
}

static std::string format_payload_command(const std::string &command, const std::string &target, const std::string &payload) {
    return command + " " + target + " " + std::to_string(payload.size()) + "\n" + payload;
}

static std::string trim(const std::string &text) {
    size_t start = 0;
    while (start < text.size() && isspace((unsigned char)text[start])) start++;
    size_t end = text.size();
    while (end > start && isspace((unsigned char)text[end - 1])) end--;
    return text.substr(start, end - start);
}

static bool load_config_file(const std::string &path, std::unordered_map<std::string, std::string> &out) {
    std::ifstream file(path);
    if (!file.is_open()) return false;
    std::string line;
    while (std::getline(file, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';') continue;
        size_t eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string key = trim(line.substr(0, eq));
        std::string value = trim(line.substr(eq + 1));
        out[key] = value;
    }
    return true;
}

static std::string get_config_value(const std::unordered_map<std::string, std::string> &config,
                                    const std::string &key,
                                    const std::string &fallback) {
    auto it = config.find(key);
    return it != config.end() ? it->second : fallback;
}

static bool has_flag(int argc, char** argv, const std::string &name) {
    for (int i = 1; i < argc; ++i) {
        if (name == argv[i]) return true;
    }
    return false;
}

static bool starts_with(const std::string &value, const std::string &prefix) {
    return value.rfind(prefix, 0) == 0;
}

static std::string parse_arg_value(int argc, char** argv, const std::string &name) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == name && i + 1 < argc) return argv[i + 1];
        std::string prefix = name + "=";
        if (starts_with(arg, prefix)) return arg.substr(prefix.size());
    }
    return {};
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: signaling_client [--config=<path>] [server_host server_port peer_id] [target_peer] [--deploy] [--gamepad-app=<name>] [--gamepad-vendor=<id>] [--gamepad-product=<id>]\n";
        return 1;
    }

    std::unordered_map<std::string, std::string> config;
    std::string config_path = parse_arg_value(argc, argv, "--config");
    if (!config_path.empty()) {
        if (load_config_file(config_path, config)) {
            std::cout << "Loaded config: " << config_path << "\n";
        } else {
            std::cerr << "Failed to load config: " << config_path << "\n";
        }
    }

    std::string host = parse_arg_value(argc, argv, "--server_host");
    if (host.empty() && argc > 1 && argv[1][0] != '-') host = argv[1];
    host = get_config_value(config, "server_host", host);

    std::string port_arg = parse_arg_value(argc, argv, "--server_port");
    if (port_arg.empty() && argc > 2 && argv[2][0] != '-') port_arg = argv[2];
    port_arg = get_config_value(config, "server_port", port_arg);
    if (port_arg.empty()) {
        std::cerr << "Missing server port. Provide --server_port or positional server_port.\n";
        return 1;
    }
    uint16_t port = static_cast<uint16_t>(std::stoi(port_arg));

    std::string peer_id = parse_arg_value(argc, argv, "--peer_id");
    if (peer_id.empty() && argc > 3 && argv[3][0] != '-') peer_id = argv[3];
    peer_id = get_config_value(config, "peer_id", peer_id);
    if (peer_id.empty()) {
        std::cerr << "Missing peer_id. Provide --peer_id or positional peer_id.\n";
        return 1;
    }

    std::string auto_target = parse_arg_value(argc, argv, "--auto_target");
    if (auto_target.empty() && argc >= 5 && argv[4][0] != '-') auto_target = argv[4];
    auto_target = get_config_value(config, "auto_target", auto_target);

    if (host.empty()) {
        std::cerr << "Missing server_host. Provide --server_host or positional server_host.\n";
        return 1;
    }

    bool deploy_mode = has_flag(argc, argv, "--deploy") || get_config_value(config, "deploy", "false") == "true";
    GamepadManagerConfig gamepad_config;
    gamepad_config.filter.appName = get_config_value(config, "gamepad_app", "");
    gamepad_config.filter.vendorId = get_config_value(config, "gamepad_vendor", "");
    gamepad_config.filter.productId = get_config_value(config, "gamepad_product", "");
    for (int i = 4; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--deploy") {
            deploy_mode = true;
        } else if (starts_with(arg, "--gamepad-app=")) {
            gamepad_config.filter.appName = arg.substr(strlen("--gamepad-app="));
        } else if (starts_with(arg, "--gamepad-vendor=")) {
            gamepad_config.filter.vendorId = arg.substr(strlen("--gamepad-vendor="));
        } else if (starts_with(arg, "--gamepad-product=")) {
            gamepad_config.filter.productId = arg.substr(strlen("--gamepad-product="));
        }
    }
    if (!gamepad_config.filter.appName.empty() || !gamepad_config.filter.vendorId.empty() || !gamepad_config.filter.productId.empty()) {
        initialize_gamepad_manager(gamepad_config);
        std::cout << "Gamepad filter: " << get_gamepad_filter_summary() << "\n";
        if (!should_show_gamepad()) {
            std::cout << "Gamepad hidden: current app/device does not match filter\n";
        } else {
            std::cout << "Gamepad allowed for current app/device\n";
        }
    }
    std::atomic<bool> running(true);

    sockets_init();
    socket_t s = connect_to_host(host, port);
    if (s < 0) {
        std::cerr << "Failed to connect to signaling server\n";
        sockets_cleanup();
        return 1;
    }

    if (!send_websocket_upgrade(s, host)) {
        std::cerr << "WebSocket upgrade failed\n";
        close_socket(s);
        sockets_cleanup();
        return 1;
    }

    if (read_http_response(s).empty()) {
        std::cerr << "Invalid WebSocket response\n";
        close_socket(s);
        sockets_cleanup();
        return 1;
    }

    if (!send_frame(s, "REGISTER " + peer_id)) {
        std::cerr << "REGISTER failed\n";
        close_socket(s);
        sockets_cleanup();
        return 1;
    }

    std::string reply;
    if (!receive_message(s, reply)) {
        std::cerr << "No response from signaling server\n";
        close_socket(s);
        sockets_cleanup();
        return 1;
    }

    std::cout << "Server reply: " << reply << "\n";
    if (deploy_mode) {
        std::cout << "Deploy mode enabled\n";
    }

    std::thread receiver([&]() {
        while (running) {
            std::string incoming;
            if (!receive_message(s, incoming)) break;
            std::string from, command, payload;
            if (parse_server_message(incoming, from, command, payload)) {
                if (command == "OFFER") {
                    std::cout << "\nReceived OFFER from " << from << "\n";
                    std::cout << payload << "\n";
                    std::string answer = make_sdp_answer(peer_id, from);
                    std::string response = format_payload_command("ANSWER", from, answer);
                    send_frame(s, response);
                    std::cout << "Sent automatic ANSWER to " << from << "\n";
                } else if (command == "ANSWER") {
                    std::cout << "\nReceived ANSWER from " << from << "\n";
                    std::cout << payload << "\n";
                } else {
                    std::cout << "\nMessage from " << from << ": " << command << "\n";
                }
            } else {
                std::cout << "\nServer: " << incoming << "\n";
            }
        }
        running = false;
    });

    if (!send_frame(s, "LIST")) {
        std::cerr << "Failed to request peer list\n";
    }

    if (!auto_target.empty()) {
        std::string offer = make_sdp_offer(peer_id, auto_target);
        std::string command = format_payload_command("OFFER", auto_target, offer);
        if (send_frame(s, command)) {
            std::cout << "Sent automatic OFFER to " << auto_target << "\n";
        }
    }

    std::cout << "Commands: list | call <target> | unregister | quit\n";
    std::string line;
    while (running && std::getline(std::cin, line)) {
        if (line.empty()) continue;
        if (line == "list") {
            send_frame(s, "LIST");
            continue;
        }
        if (line == "unregister" || line == "quit") {
            send_frame(s, "UNREGISTER");
            break;
        }
        if (line.rfind("call ", 0) == 0) {
            std::string target = line.substr(5);
            std::string offer = make_sdp_offer(peer_id, target);
            std::string command = format_payload_command("OFFER", target, offer);
            send_frame(s, command);
            continue;
        }
        std::cerr << "Unknown command\n";
    }

    running = false;
    close_socket(s);
    if (receiver.joinable()) receiver.join();
    sockets_cleanup();
    return 0;
}
