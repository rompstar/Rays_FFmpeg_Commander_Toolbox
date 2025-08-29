# Rays_FFmpeg_Commander_Toolbox
GUI front-end for the FFMpeg tool / tested on Ubuntu Linux 25.04

note: always read the CHANGELOG.md for latest revision info and Download the latest software version...

![Screenshot description](<Screenshot From 2025-08-24 14-17-21.png>)

## Demo Video

[Video: Rays FFmpeg Commander Tool Beta 0.9.0](https://www.youtube.com/watch?v=Hm3cHSqLoLc)


## Overview

Ray’s FFmpeg Commander Toolbox is a user-friendly graphical interface for FFmpeg developed in Ubuntu Linux 25.04 version, designed to simplify video conversion and encoding tasks. It supports batch processing of files and VIDEO_TS folders, hardware GPU detection, multiple video and audio codec selections, customizable encoding presets, and more.

The tool provides an intuitive GUI front-end to leverage FFmpeg’s powerful command-line capabilities without needing to write commands manually.

## Testing Notes

I have only tested this on Ubuntu Linux 25.04 / it might work on Mac or PC too, if you fullfill all the Dependencies.

## Features

- Select individual files or VIDEO_TS folders for batch conversion
- Choose from multiple video codecs (H264, HEVC, VP8/VP9, MJPEG, NVENC hardware codecs)
- Select audio codec (AAC, MP3, Opus, AC3, etc.) for output
- Configure encoding presets, bitrate, constant quality (CRF), and rate control modes
- Enable or disable spatial adaptive quantization
- Convert videos to mp4, mkv, mov, avi, webm containers
- Black & white (grayscale) conversion option
- Real-time progress bar and detailed logs
- NVIDIA GPU detection and support for NVENC encoding

## Dependencies

- Python 3.x
- GTK 3 (PyGObject bindings)
- FFmpeg and FFprobe (must be installed and accessible in system PATH)
- NVIDIA drivers and `nvidia-smi` (if using GPU hardware acceleration)
- Standard Python libraries (`subprocess`, `threading`, `re`, `webbrowser`)

## Installation

1. Install Python 3 and GTK 3 with PyGObject:
   - On Ubuntu/Debian:
     ```
     sudo apt install python3 python3-gi gir1.2-gtk-3.0 ffmpeg
     ```
   - On macOS, use Homebrew:
     ```
     brew install python3 pygobject3 ffmpeg
     ```

2. Ensure FFmpeg and FFprobe are installed and in your system PATH.

3. Clone or download this repository:

