#include "../include/capture/screen_capturer.h"
#include <windows.h>
#include <d3d11.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <iostream>

using Microsoft::WRL::ComPtr;

namespace nexus::capture {

class DXGICapturer : public ScreenCapturer {
public:
    bool init() override {
        D3D_FEATURE_LEVEL levels[] = { D3D_FEATURE_LEVEL_11_0 };
        D3D_FEATURE_LEVEL selected;
        
        HRESULT hr = D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0,
            levels, ARRAYSIZE(levels), D3D11_SDK_VERSION, &device_, &selected, &context_);
        if (FAILED(hr)) { std::cerr << "[DXGI] D3D11 failed\n"; return false; }
        
        ComPtr<IDXGIDevice> dxgi;
        hr = device_.As(&dxgi);
        if (FAILED(hr)) return false;
        
        ComPtr<IDXGIAdapter> adapter;
        dxgi->GetAdapter(&adapter);
        
        ComPtr<IDXGIOutput> output;
        adapter->EnumOutputs(0, &output);
        
        ComPtr<IDXGIOutput1> output1;
        output.As(&output1);
        
        DXGI_OUTPUT_DESC desc;
        output->GetDesc(&desc);
        width_ = desc.DesktopCoordinates.right - desc.DesktopCoordinates.left;
        height_ = desc.DesktopCoordinates.bottom - desc.DesktopCoordinates.top;
        
        hr = output1->DuplicateOutput(device_.Get(), &duplication_);
        if (FAILED(hr)) { std::cerr << "[DXGI] DuplicateOutput failed\n"; return false; }
        
        D3D11_TEXTURE2D_DESC staging_desc = {};
        staging_desc.Width = width_; staging_desc.Height = height_;
        staging_desc.MipLevels = 1; staging_desc.ArraySize = 1;
        staging_desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        staging_desc.SampleDesc.Count = 1;
        staging_desc.Usage = D3D11_USAGE_STAGING;
        staging_desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        device_->CreateTexture2D(&staging_desc, nullptr, &staging_);
        
        std::cout << "[DXGI] Capturer ready: " << width_ << "x" << height_ << "\n";
        return true;
    }
    
    std::unique_ptr<Frame> capture() override {
        ComPtr<IDXGIResource> res;
        DXGI_OUTDUPL_FRAME_INFO info;
        HRESULT hr = duplication_->AcquireNextFrame(16, &info, &res);
        if (hr == DXGI_ERROR_WAIT_TIMEOUT) return nullptr;
        if (FAILED(hr)) { duplication_.Reset(); init(); return nullptr; }
        
        ComPtr<ID3D11Texture2D> tex;
        res.As(&tex);
        context_->CopyResource(staging_.Get(), tex.Get());
        
        D3D11_MAPPED_SUBRESOURCE mapped;
        context_->Map(staging_.Get(), 0, D3D11_MAP_READ, 0, &mapped);
        
        auto frame = std::make_unique<Frame>();
        frame->width = width_; frame->height = height_;
        frame->stride = mapped.RowPitch;
        frame->data.resize(mapped.RowPitch * height_);
        frame->timestamp = info.LastPresentTime.QuadPart;
        
        uint8_t* src = static_cast<uint8_t*>(mapped.pData);
        uint8_t* dst = frame->data.data();
        for (uint32_t y = 0; y < height_; y++)
            memcpy(dst + y * mapped.RowPitch, src + y * mapped.RowPitch, width_ * 4);
        
        context_->Unmap(staging_.Get(), 0);
        duplication_->ReleaseFrame();
        return frame;
    }
    
    void get_resolution(uint32_t& w, uint32_t& h) override { w = width_; h = height_; }
    void release() override { duplication_.Reset(); staging_.Reset(); context_.Reset(); device_.Reset(); }

private:
    ComPtr<ID3D11Device> device_;
    ComPtr<ID3D11DeviceContext> context_;
    ComPtr<IDXGIOutputDuplication> duplication_;
    ComPtr<ID3D11Texture2D> staging_;
    uint32_t width_ = 0, height_ = 0;
};

std::unique_ptr<ScreenCapturer> create_capturer() { return std::make_unique<DXGICapturer>(); }

} // namespace nexus::capture
