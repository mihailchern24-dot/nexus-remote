cmake_minimum_required(VERSION 3.20)
project(NexusRemote VERSION 2.0.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)

if(WIN32)
    set(CMAKE_TOOLCHAIN_FILE "C:/vcpkg/scripts/buildsystems/vcpkg.cmake")
    find_package(Boost REQUIRED COMPONENTS system)
    set(PLATFORM_SOURCES src/capture/dxgi_capturer.cpp src/video/ffmpeg_encoder.cpp)
    set(PLATFORM_LIBS d3d11 dxgi "C:/vcpkg/installed/x64-windows/lib/avcodec.lib" "C:/vcpkg/installed/x64-windows/lib/avformat.lib" "C:/vcpkg/installed/x64-windows/lib/avutil.lib" "C:/vcpkg/installed/x64-windows/lib/swscale.lib" "C:/vcpkg/installed/x64-windows/lib/swresample.lib")
    set(PLATFORM_INCLUDES "C:/vcpkg/installed/x64-windows/include")
else()
    find_package(Boost REQUIRED COMPONENTS system)
    set(PLATFORM_SOURCES "")
    set(PLATFORM_LIBS "")
    set(PLATFORM_INCLUDES "")
endif()

add_library(nexus_core STATIC
    src/base64.cpp src/crypto_utils.cpp src/sha1.cpp
    src/socket_utils.cpp src/websocket_utils.cpp
    src/stun.cpp src/turn.cpp src/tls_utils.cpp
    src/input_filter.cpp src/gamepad_manager.cpp
    src/nexus_client.cpp
    
)
target_include_directories(nexus_core PUBLIC include )
target_link_libraries(nexus_core PUBLIC Boost::system )

if(WIN32)
    add_executable(nexus_remote WIN32 src/main.cpp)
    target_link_libraries(nexus_remote PRIVATE nexus_core user32 gdi32 gdiplus)
endif()

add_executable(client src/client.cpp)
target_link_libraries(client PRIVATE nexus_core)

add_executable(relay_server src/relay_server.cpp)
target_link_libraries(relay_server PRIVATE nexus_core)

add_executable(signaling_client src/signaling_client.cpp)
target_link_libraries(signaling_client PRIVATE nexus_core)

add_executable(signaling_server src/signaling_server.cpp)
target_link_libraries(signaling_server PRIVATE nexus_core)

add_executable(stun_client src/stun_client.cpp)
target_link_libraries(stun_client PRIVATE nexus_core)
