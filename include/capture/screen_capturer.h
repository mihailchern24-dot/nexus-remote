#pragma once
#include <cstdint>
#include <vector>
#include <memory>
#include <string>

namespace nexus::capture {

struct Frame {
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t stride = 0;
    std::vector<uint8_t> data;
    uint64_t timestamp = 0;
};

class ScreenCapturer {
public:
    virtual ~ScreenCapturer() = default;
    virtual bool init() = 0;
    virtual std::unique_ptr<Frame> capture() = 0;
    virtual void get_resolution(uint32_t& w, uint32_t& h) = 0;
    virtual void release() = 0;
};

std::unique_ptr<ScreenCapturer> create_capturer();

} // namespace nexus::capture
