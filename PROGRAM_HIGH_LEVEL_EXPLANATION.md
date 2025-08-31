# Ray’s FFmpeg Commander Toolbox — High‑Level Execution  
  
Overview  
- Desktop GUI for ffmpeg built with Python + GTK (PyGObject).  
- GPU‑first conversions (NVENC) with smart fallbacks to keep jobs running.  
- Handles single files and DVD VIDEO_TS folders.  
- Live log, file ETA and overall ETA; no size estimator UI.  
  
Startup sequence  
1. Import modules and apply the Solaris‑8/CDE‑style CSS via load_style().  
2. Construct the main window and build all controls:  
   - File/folder pickers, output name, container/encoder selectors.  
   - Preset + rate control (VBR/CBR for NVENC), CRF/CQ slider, bitrate box.  
   - Toggles: Spatial AQ (NVENC) and Black‑and‑White.  
   - Audio encoder, action buttons, log view, ETAs, progress bar.  
3. Detect hardware/capabilities:  
   - Query nvidia-smi for GPU names.  
   - Query ffmpeg for encoders/decoders/filters/hwaccels.  
   - Probe NVENC feature flags (temporal AQ, lookahead, p010).  
   - Prune missing NVENC options from the codec list and show a capability summary.  
4. Auto‑select the best available NVENC encoder (HEVC, else H.264) once.  
  
Typical user flow  
1. Choose files or VIDEO_TS folders.  
2. Pick container and video encoder; adjust preset, CRF/CQ or bitrate, toggles, and audio codec.  
3. Click Convert (use current settings) or Super Convert (auto‑tuned, GPU‑first).  
4. Watch live log, progress bar, File ETA and Overall ETA. Optionally Cancel.  
  
Super Convert  
- Probes the first item and chooses sensible settings:  
  - Prefer NVENC (HEVC or H.264) with CQ and preset scaled by resolution.  
  - Use main10 for HEVC when p010 is supported and source/bit‑depth match.  
  - If no NVENC, choose libx265 with fast, multi‑thread‑friendly parameters.  
- Applies those settings to the UI and starts a normal conversion.  
  
Conversion thread (process_batch)  
1. Precompute per‑item durations and total content seconds; update ETAs.  
2. For each item in the batch:  
   - Derive output name and container flags (+faststart for MP4; hvc1 tag for HEVC in MP4/MOV).  
   - Build video args via build_video_args():  
     - NVENC: map presets to p1–p7, set VBR/CBR, CQ/bitrate, Spatial AQ, and (when supported) temporal AQ / lookahead; choose yuv420p/p010 and main10 as applicable.  
     - CPU (x264/x265): set preset/CRF and pix_fmt; optional extra x265 speed params.  
   - Input handling:  
     - Regular files: use CUDA decode + hardware frames when available and no filter is applied; otherwise CPU decode. Optional grayscale filter.  
     - VIDEO_TS: concatenate VOBs with filter_complex concat, then encode.  
   - Run ffmpeg (run_ffmpeg_sync):  
     - Stream and log stderr.  
     - Parse time= and speed= to update progress and ETAs in real time.  
     - Respect Cancel by terminating the ffmpeg process group.  
   - Fallbacks on failure, in order:  
     1) Retry NVENC in “safe mode” (no temporal AQ/lookahead).  
     2) If CUDA frames path fails, retry CPU decode → NVENC.  
     3) If HEVC NVENC fails, fall back to H.264 NVENC.  
     4) Fall back to CPU x264 veryfast.  
   - On success, mark file as done, update progress/ETAs, and optionally show a “Completed” dialog for single‑item runs.  
  
Post‑run and reset  
- After the batch: log final status, clear the selection, reset all UI controls, and leave the full ffmpeg log visible.  
  
Key helpers  
- Hardware probing: _detect_gpu(), _query_nvenc_help().  
- Media probing: get_duration(), get_input_bit_depth(), probe_stream().  
- DVD support: is_videots(), get_videos(), compute_item_duration().  
- UI utilities: update_progress(), update_file_eta(), update_overall_eta(), reset_ui().  
  
Dependencies  
- Python 3, GTK 3 (PyGObject), ffmpeg and ffprobe in PATH.  
- Optional for GPU: NVIDIA driver, nvidia-smi, ffmpeg built with NVENC/NVDEC/CUDA support.  
  
Notes  
- Theme emulates Solaris‑8/CDE look within GTK CSS constraints.  
- The Size Estimator feature has been removed in this build; the app focuses on conversion, logging, and ETA.
