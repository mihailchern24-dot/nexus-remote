#!/usr/bin/env python3
# codec_config.py - астройки кодеков для всех платформ
import json

CODEC_CONFIGS = {
    "windows": {
        "primary": "h264_nvenc",     # NVIDIA GPU
        "fallback": "h264_mf",       # Media Foundation
        "software": "libx264",       # рограммный
        "max_bitrate": 50000,        # 50 Mbps
        "preset": "p2"               # Самая быстрая
    },
    "linux": {
        "primary": "h264_vaapi",     # Intel/AMD GPU
        "fallback": "h264_v4l2m2m",  # V4L2
        "software": "libx264",
        "max_bitrate": 50000,
        "preset": "ultrafast"
    },
    "macos": {
        "primary": "h264_videotoolbox",  # Apple Hardware
        "software": "libx264",
        "max_bitrate": 50000,
        "preset": "ultrafast"
    },
    "android": {
        "primary": "h264_mediacodec",    # Android Hardware
        "software": "libx264",
        "max_bitrate": 30000,
        "preset": "ultrafast"
    },
    "ios": {
        "primary": "h264_videotoolbox",  # Apple Hardware
        "software": "libx264",
        "max_bitrate": 30000,
        "preset": "ultrafast"
    },
    "playstation": {
        "primary": "libx264",            # рограммный (PS4/PS5)
        "max_bitrate": 40000,
        "preset": "veryfast"
    },
    "xbox": {
        "primary": "h264_amf",           # AMD GPU в Xbox
        "software": "libx264",
        "max_bitrate": 40000,
        "preset": "ultrafast"
    },
    "nintendo": {
        "primary": "libx264",            # рограммный (Switch)
        "max_bitrate": 15000,
        "preset": "superfast",
        "resolution": "720p"
    },
    "android_tv": {
        "primary": "h264_mediacodec",
        "software": "libx264",
        "max_bitrate": 40000,
        "preset": "ultrafast"
    },
    "android_auto": {
        "primary": "libx264",            # Слабое железо
        "max_bitrate": 5000,             # 5 Mbps
        "preset": "ultrafast",
        "resolution": "480p"
    }
}

# даптивные настройки качества
QUALITY_PRESETS = {
    "ultra": {"bitrate": 50000, "fps": 60, "resolution": "4K"},
    "high": {"bitrate": 25000, "fps": 60, "resolution": "1080p"},
    "medium": {"bitrate": 10000, "fps": 30, "resolution": "720p"},
    "low": {"bitrate": 5000, "fps": 24, "resolution": "480p"},
    "minimal": {"bitrate": 2000, "fps": 15, "resolution": "360p"}
}

def get_codec_config(platform):
    return CODEC_CONFIGS.get(platform, CODEC_CONFIGS["linux"])

def get_quality_preset(quality="auto"):
    return QUALITY_PRESETS.get(quality, QUALITY_PRESETS["medium"])
