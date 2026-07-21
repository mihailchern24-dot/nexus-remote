#pragma once
#include <cstdint>
#include <vector>
#include <memory>

namespace nexus::video {

struct EncodedPacket {
    std::vector<uint8_t> data;
    bool keyframe = false;
    int64_t pts = 0;
};

class VideoEncoder {
public:
    virtual ~VideoEncoder() = default;
    virtual bool init(uint32_t w, uint32_t h, uint32_t fps = 30) = 0;
    virtual std::unique_ptr<EncodedPacket> encode(const std::vector<uint8_t>& bgra, uint32_t w, uint32_t h) = 0;
    virtual void release() = 0;
};

std::unique_ptr<VideoEncoder> create_encoder();

} // namespace nexus::video
