# Changelog

## [0.9.1] - 2025-08-28
### Added
- Implemented a Progress bar update
- Added a Clear Selection button
- Fixed the Cancel Button

### Fixed
- Resolved indentation errors.
- Fixed threading issues in ffmpeg monitor.

[0.9.2] - 2025-08-29
Added

Per-file ETA label and calculation alongside Overall ETA for batch jobs.
Precomputation of item durations via ffprobe for accurate Overall ETA.
NVENC enhancements:
Preset mapping from x264/x265 presets to NVENC p1–p7.
Proper NVENC rate control support (vbr/cbr), using -cq for VBR and -b:v/-maxrate/-bufsize where appropriate.
Spatial AQ toggle (NVENC only).
Pixel format enforcement: yuv420p for h264_nvenc; p010le + main10 profile for hevc_nvenc when source is ≥10‑bit.
GPU/NVENC detection:
Detect NVIDIA GPUs via nvidia-smi.
Detect available NVENC encoders via ffmpeg and hide unavailable NVENC options from the codec list.
Conditional +faststart (movflags) for MP4/MOV-like containers only.
Batch status label displaying current file (i of N).
Output naming improvements for batch conversions.
Optional Black & White (grayscale) filter.
Changed

Quality slider/label adapt to selected encoder (CRF for x264/x265, CQ for NVENC).
Rate control and Spatial AQ controls enabled only when an NVENC encoder is selected.
Fixed

Eliminated "crf has not been used for this encoder" warnings by switching NVENC to -cq/-rc options.
Improved cancellation reliability by terminating the entire ffmpeg process group.
Better input validation for bitrate (numeric kbps).
Miscellaneous logging and UI stability improvements.
[0.9.1] - 2025-08-28
Added

Implemented a progress bar update.
Added a Clear Selection button.
Fixed

Fixed the Cancel button.
Resolved indentation errors.
Fixed threading issues in the ffmpeg monitor.


