#pragma once
#include <string>
#include <functional>
#include <memory>
#include <thread>
#include <atomic>
#include "../include/socket_utils.h"
#include "../include/websocket_utils.h"

namespace nexus::client {

struct Device {
    std::string id;
    std::string name;
    bool online;
};

class NexusClient {
public:
    using DeviceCallback = std::function<void(const std::vector<Device>&)>;
    using FrameCallback = std::function<void(const uint8_t*, size_t, uint32_t w, uint32_t h)>;
    
    NexusClient(const std::string& serverHost, uint16_t serverPort);
    ~NexusClient();
    
    bool connect(const std::string& deviceId, const std::string& password);
    void disconnect();
    void setDeviceCallback(DeviceCallback cb) { onDevices = cb; }
    void setFrameCallback(FrameCallback cb) { onFrame = cb; }
    bool isConnected() const { return connected; }

private:
    void readLoop();
    void sendFrame(const std::string& msg);
    
    std::string serverHost;
    uint16_t serverPort;
    socket_t sock = -1;
    std::atomic<bool> connected{false}, running{false};
    std::unique_ptr<std::thread> recvThread;
    
    DeviceCallback onDevices;
    FrameCallback onFrame;
};

} // namespace nexus::client
