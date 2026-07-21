#include "../include/video/video_encoder.h"
#include <iostream>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavutil/opt.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}

namespace nexus::video {

class FFmpegEncoder : public VideoEncoder {
public:
    bool init(uint32_t w, uint32_t h, uint32_t fps) override {
        const AVCodec* codec = avcodec_find_encoder_by_name("h264_mf");
        if (!codec) codec = avcodec_find_encoder(AV_CODEC_ID_H264);
        if (!codec) { std::cerr << "[FFmpeg] No H264 encoder\n"; return false; }
        
        ctx_ = avcodec_alloc_context3(codec);
        ctx_->width = w; ctx_->height = h;
        ctx_->time_base = {1, (int)fps};
        ctx_->framerate = {(int)fps, 1};
        ctx_->pix_fmt = AV_PIX_FMT_YUV420P;
        ctx_->bit_rate = 2000000;
        ctx_->gop_size = fps * 2;
        ctx_->max_b_frames = 0;
        av_opt_set(ctx_->priv_data, "preset", "ultrafast", 0);
        av_opt_set(ctx_->priv_data, "tune", "zerolatency", 0);
        
        if (avcodec_open2(ctx_, codec, nullptr) < 0) { std::cerr << "[FFmpeg] Open failed\n"; return false; }
        
        frame_ = av_frame_alloc();
        frame_->format = ctx_->pix_fmt;
        frame_->width = w; frame_->height = h;
        av_frame_get_buffer(frame_, 0);
        
        pkt_ = av_packet_alloc();
        sws_ = sws_getContext(w, h, AV_PIX_FMT_BGRA, w, h, AV_PIX_FMT_YUV420P, SWS_BILINEAR, nullptr, nullptr, nullptr);
        
        std::cout << "[FFmpeg] Encoder: " << codec->name << " " << w << "x" << h << "\n";
        return true;
    }
    
    std::unique_ptr<EncodedPacket> encode(const std::vector<uint8_t>& bgra, uint32_t w, uint32_t h) override {
        const uint8_t* src[1] = { bgra.data() };
        int stride[1] = { (int)w * 4 };
        sws_scale(sws_, src, stride, 0, h, frame_->data, frame_->linesize);
        frame_->pts = pts_++;
        
        avcodec_send_frame(ctx_, frame_);
        int ret = avcodec_receive_packet(ctx_, pkt_);
        if (ret == AVERROR(EAGAIN)) return nullptr;
        if (ret < 0) return nullptr;
        
        auto out = std::make_unique<EncodedPacket>();
        out->data.assign(pkt_->data, pkt_->data + pkt_->size);
        out->keyframe = (pkt_->flags & AV_PKT_FLAG_KEY);
        out->pts = pkt_->pts;
        av_packet_unref(pkt_);
        return out;
    }
    
    void release() override {
        if (pkt_) av_packet_free(&pkt_);
        if (frame_) av_frame_free(&frame_);
        if (sws_) sws_freeContext(sws_);
        if (ctx_) avcodec_free_context(&ctx_);
    }

private:
    AVCodecContext* ctx_ = nullptr;
    AVFrame* frame_ = nullptr;
    AVPacket* pkt_ = nullptr;
    SwsContext* sws_ = nullptr;
    int64_t pts_ = 0;
};

std::unique_ptr<VideoEncoder> create_encoder() { return std::make_unique<FFmpegEncoder>(); }

} // namespace nexus::video
