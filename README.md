# Nexus Remote — MVP (C++)

This repository contains a minimal C++ MVP demonstrating a simple TCP relay server and a client.

Goals:
- Provide a basic relay that forwards data between two connected peers.
- Cross-platform (Windows / Linux / macOS) source using native sockets.

Build (Linux / macOS):

```sh
mkdir -p build && cd build
cmake ..
cmake --build . --config Release
```

Build (Windows, cmd / PowerShell):

```powershell
mkdir build; cd build
cmake ..
cmake --build . --config Release
```

Run relay server:

```sh
./relay_server 9000
```

Run client:

```sh
./client 127.0.0.1 9000
```

Notes:
- This is a skeleton for the full Nexus Remote system. Next steps: signaling, TLS/XTLS, video/audio codecs, input sync, file transfer, and platform agents.
