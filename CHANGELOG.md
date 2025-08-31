Changelog  
  
[0.9.1] – 2025-08-28  
Added  
Implemented a progress bar update  
Added a Clear Selection button  
Fixed the Cancel button  
Fixed  
Resolved indentation errors  
Fixed threading issues in ffmpeg monitor  
  
[0.9.2] – 2025-08-29  
Added  
Per-file ETA label and calculation alongside overall ETA for batch jobs  
Precomputation of item durations via ffprobe for accurate overall ETA  
NVENC enhancements:  
Preset mapping from x264/x265 presets to NVENC p1–p7  
Proper NVENC rate control support (vbr/cbr), using -cq for VBR and -b:v / -maxrate / -bufsize where appropriate  
Spatial AQ toggle (NVENC only)  
Pixel format enforcement: yuv420p for h264_nvenc; p010le + main10 profile for hevc_nvenc when source is ≥10-bit  
GPU/NVENC detection via nvidia-smi  
Detection of available NVENC encoders via ffmpeg, with hiding of unavailable NVENC options from the codec list  
Conditional +faststart (movflags) for MP4/MOV-like containers only  
Batch status label displaying current file (i of N)  
Output naming improvements for batch conversions  
Optional Black & White (grayscale) filter  
Changed  
Quality slider/label adapts to selected encoder (CRF for x264/x265, CQ for NVENC)  
Rate control and Spatial AQ controls enabled only when an NVENC encoder is selected  
Fixed  
Eliminated “crf has not been used for this encoder” warnings by switching NVENC to -cq/-rc options  
Improved cancellation reliability by terminating the entire ffmpeg process group  
Better input validation for bitrate (numeric kbps)  
Miscellaneous logging and UI stability improvements  
  
[0.9.3] – 2025-08-31  
Added  
Super Convert button next to Convert for one‑click “smaller with great quality”  
Explanatory label clarifying: Convert = use current settings; Super Convert = auto‑optimal settings  
Super Convert recipe:  
- MP4 container  
- HEVC (libx265) video encoder  
- Slow preset  
- CRF by resolution (≈22 for 4K, 23 for 1440p, 24 for 1080p, 26 for 720p, 28 for SD)  
- Bitrate forced to 0 (quality‑based)  
- 10‑bit encode when source pix_fmt is 10/12‑bit; otherwise 8‑bit  
- Respects existing audio choice and optional Black & White filter  
HEVC-in-MP4/MOV is tagged hvc1 for better macOS/iOS compatibility (libx265 and hevc_nvenc)  
CPU encoders enforce pixel formats: yuv420p for libx264; yuv420p10le + x265-params profile=main10 when doing 10‑bit x265  
Changed  
Super Convert is disabled during processing and re‑enabled on completion  
Bit‑depth probing reused to drive x265 10‑bit selection automatically  
Fixed  
Super Convert honors batch naming/ETA/cancel behavior  
Minor command-construction edge cases around tagging/pixel format  
