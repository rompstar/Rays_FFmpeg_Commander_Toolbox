import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk

import subprocess
import os
import threading
import re
import webbrowser
import signal

def load_style():
    css = b"""
    window, GtkWindow {
        background-color: #C0C0C0;
        font-family: monospace, 'Courier New', Courier, monospace;
        font-size: 10pt;
        color: black;
    }
    button {
        background: #E0E0E0;
        border: 2px solid #FFFFFF;
        border-bottom-color: #808080;
        border-right-color: #808080;
        border-radius: 0;
        padding: 3px 8px;
        box-shadow: none;
    }
    button:active {
        border: 2px solid #808080;
        border-bottom-color: #FFFFFF;
        border-right-color: #FFFFFF;
        background: #A0A0A0;
    }
    entry, combobox {
        background: #FFFFFF;
        border: 1px solid #808080;
        border-radius: 0;
        color: black;
        padding: 2px;
    }
    scrolledwindow {
        background: #FFFFFF;
        border: 1px solid #808080;
    }
    progressbar {
        border: 1px solid #808080;
        border-radius: 0;
        background: #E0E0E0;
        min-height: 40px;
    }
    progressbar > trough {
        background: #FFFFFF;
        padding: 0;
        margin: 0;
        min-height: 40px;
    }
    progressbar > trough > progress {
        background-image: none;
        background-color: #4CAF50;
        margin: 0;
        padding: 0;
        border: none;
        min-height: 40px;
    }
    label {
        font-family: monospace, 'Courier New', Courier, monospace;
        font-size: 10pt;
        color: black;
    }
    textview {
        background: #FFFFFF;
        border: 1px solid #808080;
        font-family: monospace, 'Courier New', Courier, monospace;
        font-size: 10pt;
    }
    messagedialog {
        background: #C0C0C0;
        border: 1px solid #808080;
    }
    filechooser dialog {
        background: #C0C0C0;
        border: 1px solid #808080;
    }
    #donate-button {
        background-image: none;
        background-color: #ff4500;
        color: white;
        font-weight: bold;
    }
    #donate-button:hover {
        background-color: #ff6347;
    }
    """
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(css)
    screen = Gdk.Screen.get_default()
    Gtk.StyleContext.add_provider_for_screen(
        screen, style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


class FFmpegGUI(Gtk.Window):
    VERSION = "0.9.1 Beta"

    def __init__(self):
        super().__init__(title=f"Ray’s FFmpeg Commander Toolbox - v{self.VERSION}")

        self.set_border_width(8)
        self.set_default_size(1200, 900)
        self.set_resizable(True)

        # Initialize important variables here without launching ffmpeg
        self.batch_files = []
        self.process = None
        self.duration_seconds = 0

        load_style()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add(vbox)

        self.gpu_label = Gtk.Label(label="", xalign=0, wrap=True)
        vbox.pack_start(self.gpu_label, False, False, 0)
        self.update_gpu_info()

        hbox1 = Gtk.Box(spacing=6)
        vbox.pack_start(hbox1, False, False, 0)

        self.btn_files = Gtk.Button(label="Choose Files")
        self.btn_files.connect("clicked", self.on_choose_files)
        hbox1.pack_start(self.btn_files, False, False, 0)

        self.btn_folders = Gtk.Button(label="Choose VIDEO_TS Folders")
        self.btn_folders.connect("clicked", self.on_choose_folders)
        hbox1.pack_start(self.btn_folders, False, False, 0)

        self.btn_clear = Gtk.Button(label="Clear Selection")
        self.btn_clear.connect("clicked", self.on_clear_selection)
        hbox1.pack_start(self.btn_clear, False, False, 0)

        self.label_selected = Gtk.Label(label="No files or folders selected", xalign=0)
        vbox.pack_start(self.label_selected, False, False, 0)

        # output naming section
        out_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(out_box, False, False, 0)

        out_label = Gtk.Label(label="Output filename (suffix added automatically)", xalign=0)
        out_box.pack_start(out_label, False, False, 0)

        self.entry_output = Gtk.Entry()
        self.entry_output.set_hexpand(True)
        out_box.pack_start(self.entry_output, False, False, 0)

        # format chooser box
        format_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(format_box, False, False, 0)

        format_label = Gtk.Label(label="Format - refers to the container format for the output video file.", xalign=0)
        format_box.pack_start(format_label, False, False, 0)

        self.store_format = Gtk.ListStore(str)
        for fmt in ['mp4', 'mkv', 'mov', 'avi', 'webm']:
            self.store_format.append([fmt])
        self.combo_format = Gtk.ComboBox.new_with_model(self.store_format)
        renderer = Gtk.CellRendererText()
        self.combo_format.pack_start(renderer, True)
        self.combo_format.add_attribute(renderer, "text", 0)
        self.combo_format.set_active(0)
        self.combo_format.set_hexpand(True)
        self.combo_format.connect("changed", self.on_format_changed)
        format_box.pack_start(self.combo_format, False, False, 0)

        # Codec selection box
        codec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(codec_box, False, False, 0)

        codec_label = Gtk.Label(label="Codec - dropdown lets users select the video compression format used by FFmpeg to encode the video.", xalign=0)
        codec_box.pack_start(codec_label, False, False, 0)

        self.store_codec = Gtk.ListStore(str)
        for c in ['h264', 'hevc', 'mjpeg', 'vp8', 'vp9', 'libx264',
                  'libx265', 'h264_nvenc', 'hevc_nvenc']:
            self.store_codec.append([c])
        self.combo_codec = Gtk.ComboBox.new_with_model(self.store_codec)
        renderer2 = Gtk.CellRendererText()
        self.combo_codec.pack_start(renderer2, True)
        self.combo_codec.add_attribute(renderer2, "text", 0)
        self.combo_codec.set_active(0)
        self.combo_codec.set_hexpand(True)
        codec_box.pack_start(self.combo_codec, False, False, 0)

        # Preset selection box
        preset_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(preset_box, False, False, 0)

        preset_label = Gtk.Label(label="Preset - controls the tradeoff between encoding speed and compression efficiency during video encoding.", xalign=0)
        preset_box.pack_start(preset_label, False, False, 0)

        self.store_preset = Gtk.ListStore(str)
        for p in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',
                  'medium', 'slow', 'slower', 'veryslow', 'placebo']:
            self.store_preset.append([p])
        self.combo_preset = Gtk.ComboBox.new_with_model(self.store_preset)
        renderer3 = Gtk.CellRendererText()
        self.combo_preset.pack_start(renderer3, True)
        self.combo_preset.add_attribute(renderer3, "text", 0)
        self.combo_preset.set_active(5)  # default medium
        self.combo_preset.set_hexpand(True)
        preset_box.pack_start(self.combo_preset, False, False, 0)

        # Rate Control selection box
        rc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(rc_box, False, False, 0)

        rc_label = Gtk.Label(label="Rate Control - choose the encode video bitrate. VBR (Variable Bitrate), CBR (Constant Bitrate).", xalign=0)
        rc_box.pack_start(rc_label, False, False, 0)

        self.store_rc = Gtk.ListStore(str)
        for rc in ['vbr', 'cbr']:
            self.store_rc.append([rc])
        self.combo_rc = Gtk.ComboBox.new_with_model(self.store_rc)
        renderer4 = Gtk.CellRendererText()
        self.combo_rc.pack_start(renderer4, True)
        self.combo_rc.add_attribute(renderer4, "text", 0)
        self.combo_rc.set_active(0)  # default vbr
        self.combo_rc.set_hexpand(True)
        rc_box.pack_start(self.combo_rc, False, False, 0)

        # Constant Quality (CQ) scale box
        cq_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(cq_box, False, False, 0)

        cq_label = Gtk.Label(label="Constant Quality (CQ value, typically 0-51)", xalign=0)
        cq_box.pack_start(cq_label, False, False, 0)

        self.adj_cq = Gtk.Adjustment(value=23, lower=0, upper=51, step_increment=1)
        self.scale_cq = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_cq)
        self.scale_cq.set_digits(0)
        self.scale_cq.set_value(23)
        self.scale_cq.set_value_pos(Gtk.PositionType.RIGHT)
        cq_box.pack_start(self.scale_cq, False, False, 0)

        # Bitrate input box
        bitrate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(bitrate_box, False, False, 0)

        bitrate_label = Gtk.Label(label="Bitrate (kbps) - data rate control", xalign=0)
        bitrate_box.pack_start(bitrate_label, False, False, 0)

        self.entry_bitrate = Gtk.Entry()
        self.entry_bitrate.set_text("0")
        self.entry_bitrate.set_hexpand(True)
        bitrate_box.pack_start(self.entry_bitrate, False, False, 0)

        # Checkboxes for Spatial Adaptive Quantization and Black & White (Grayscale)
        self.chk_spatial = Gtk.CheckButton(label="Enable Spatial Adaptive Quantization")
        self.chk_spatial.set_active(True)
        vbox.pack_start(self.chk_spatial, False, False, 0)

        self.chk_bw = Gtk.CheckButton(label="Black & White (Grayscale)")
        self.chk_bw.set_active(False)
        vbox.pack_start(self.chk_bw, False, False, 0)

        # Audio codec selection box
        audio_codec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.pack_start(audio_codec_box, False, False, 0)

        audio_codec_label = Gtk.Label(label="Audio Codec", xalign=0)
        audio_codec_box.pack_start(audio_codec_label, False, False, 0)

        self.store_audio_codec = Gtk.ListStore(str)
        for ac in ['aac', 'mp3', 'libmp3lame', 'opus', 'ac3']:
            self.store_audio_codec.append([ac])
        self.combo_audio_codec = Gtk.ComboBox.new_with_model(self.store_audio_codec)
        renderer_audio = Gtk.CellRendererText()
        self.combo_audio_codec.pack_start(renderer_audio, True)
        self.combo_audio_codec.add_attribute(renderer_audio, "text", 0)
        self.combo_audio_codec.set_active(0)
        self.combo_audio_codec.set_hexpand(True)
        audio_codec_box.pack_start(self.combo_audio_codec, False, False, 0)

        # Buttons box with Convert, Cancel, Donate
        btn_box = Gtk.Box(spacing=6)
        vbox.pack_start(btn_box, False, False, 0)

        self.btn_convert = Gtk.Button(label="Convert")
        self.btn_convert.connect("clicked", self.on_convert)
        btn_box.pack_start(self.btn_convert, False, False, 0)

        self.btn_cancel = Gtk.Button(label="Cancel")
        self.btn_cancel.connect("clicked", self.on_cancel)
        self.btn_cancel.set_sensitive(False)
        btn_box.pack_start(self.btn_cancel, False, False, 0)

        self.btn_donate = Gtk.Button(label="Donate (PayPal) - buy me a coffee!")
        self.btn_donate.set_name("donate-button")
        self.btn_donate.connect("clicked", self.on_donate_clicked)
        btn_box.pack_start(self.btn_donate, False, False, 0)

        # TextView for ffmpeg output with horizontal scroll
        self.textbuffer = Gtk.TextBuffer()
        self.textview = Gtk.TextView(buffer=self.textbuffer)
        self.textview.set_editable(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.NONE)
        self.textview.set_monospace(True)
        self.textview.set_vexpand(True)
        self.textview.set_hexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.textview)
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scroll, True, True, 0)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(-1, 40)
        vbox.pack_start(self.progressbar, False, False, 0)

        self.show_all()

    def append_log(self, text: str):
        def _append():
            end_iter = self.textbuffer.get_end_iter()
            self.textbuffer.insert(end_iter, text)
            mark = self.textbuffer.create_mark(None, self.textbuffer.get_end_iter(), False)
            self.textview.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
            return False
        GLib.idle_add(_append)

    def get_combo_text(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            return model[tree_iter][0]
        else:
            return None

    def on_choose_files(self, widget):
        dialog = Gtk.FileChooserDialog(title="Select Files", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            files = dialog.get_filenames()
            self.batch_files.clear()
            if files:
                self.batch_files.extend(files)
                self.label_selected.set_text(f"{len(self.batch_files)} files selected")
                self.append_log(f"Selected files: {files}\n")
                if not self.entry_output.get_text():
                    first = files[0]
                    base = os.path.basename(first)
                    ext = self.get_combo_text(self.combo_format) or "mp4"
                    self.entry_output.set_text(f"{base}_converted.{ext}")
            else:
                self.label_selected.set_text("No files selected.")
                self.append_log("No files selected from dialog\n")
        else:
            self.append_log("File selection cancelled\n")
        dialog.destroy()

    def on_choose_folders(self, widget):
        dialog = Gtk.FileChooserDialog(title="Select Folders", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_select_multiple(True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folders = dialog.get_filenames()
            self.batch_files.clear()
            self.batch_files.extend(folders)
            self.label_selected.set_text(f"{len(self.batch_files)} folders selected")
            self.append_log(f"Selected folders: {folders}\n")
            for folder in folders:
                if self.is_videots(folder):
                    video_ts_path = folder if os.path.basename(folder).upper() == "VIDEO_TS" else os.path.join(folder, "VIDEO_TS")
                    if os.path.isdir(video_ts_path):
                        files = os.listdir(video_ts_path)
                        self.append_log(f"VIDEO_TS folder found: {video_ts_path}\nContents: {files}\n")
                    else:
                        self.append_log(f"Warning: Expected VIDEO_TS folder inside {folder} not found\n")
                else:
                    self.append_log(f"Selected folder {folder} is not a VIDEO_TS folder\n")
            if not self.entry_output.get_text() and folders:
                first = folders[0]
                if self.is_videots(first):
                    first = os.path.dirname(first)
                base = os.path.basename(first)
                ext = self.get_combo_text(self.combo_format) or "mp4"
                self.entry_output.set_text(f"{base}_converted.{ext}")
        else:
            self.append_log("Folder selection cancelled\n")
        dialog.destroy()

    def on_clear_selection(self, widget):
        self.batch_files.clear()
        self.label_selected.set_text("No files or folders selected")
        self.append_log("Selection cleared by user\n")

    def on_convert(self, widget):
        if not self.batch_files:
            self.label_selected.set_text("No files or folders selected.")
            return
        self.btn_convert.set_sensitive(False)
        self.btn_cancel.set_sensitive(True)
        self.btn_convert.set_label("Converting...")
        threading.Thread(target=self.process_batch, daemon=True).start()

    def on_cancel(self, widget):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            GLib.idle_add(self.append_log, "Conversion cancelled.\n")
            self.process = None
            GLib.idle_add(self.reset_ui)

    def on_donate_clicked(self, widget):
        url = "https://www.paypal.com/donate?business=rompstar@gmail.com&amount=5.00"
        webbrowser.open(url)

    def is_videots(self, path):
        if os.path.isdir(path):
            if os.path.basename(path).upper() == "VIDEO_TS":
                return True
            if os.path.isdir(os.path.join(path, "VIDEO_TS")):
                return True
        return False

    def get_videos(self, ts_path):
        return sorted([os.path.join(ts_path, f) for f in os.listdir(ts_path) if f.upper().endswith(".VOB")])

    def get_duration(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return 0
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", filepath],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(proc.stdout.strip())
        except (ValueError, TypeError):
            return 0

    def process_batch(self):
        nvenc_presets_map = {
            "ultrafast": "default",
            "superfast": "llhp",
            "faster": "ll",
            "fast": "hp",
            "medium": "hq",
            "slow": "hq",
            "slower": "hq",
            "veryslow": "hq",
            "placebo": "hq",
        }

        self.append_log(f"Starting batch of {len(self.batch_files)} items\n")
        for idx, path in enumerate(self.batch_files):
            self.append_log(f"Processing item {idx + 1}: {path}\n")
            original_path = path
            work_path = os.path.dirname(path) if os.path.basename(path).upper() == "VIDEO_TS" else path
            base = os.path.basename(work_path)
            ext = self.get_combo_text(self.combo_format) or "mp4"

            bitrate = self.entry_bitrate.get_text()
            if not bitrate.isdigit():
                GLib.idle_add(self.label_selected.set_text, "Bitrate must be numeric")
                return
            bitrate_value = int(bitrate)

            cq = int(self.scale_cq.get_value())
            codec = self.get_combo_text(self.combo_codec) or "libx264"
            preset = self.get_combo_text(self.combo_preset) or "medium"
            audio_codec = self.get_combo_text(self.combo_audio_codec) or "aac"

            filters = ["scale=iw:ih"]
            if self.chk_bw.get_active():
                filters.append("hue=s=0")
            vf = ",".join(filters)

            if len(self.batch_files) > 1:
                out_file_name = f"{base}_converted_{idx + 1}.{ext}"
            else:
                out_file_name = self.entry_output.get_text() or f"{base}_converted.{ext}"

            if self.is_videots(work_path):
                parent_dir = os.path.dirname(work_path)
                out_file = os.path.join(parent_dir, out_file_name)
            else:
                out_file = out_file_name

            if codec in ["hevc_nvenc", "h264_nvenc"]:
                preset_to_use = nvenc_presets_map.get(preset, "default")
            else:
                preset_to_use = preset

            if self.is_videots(work_path):
                ts_path = os.path.join(work_path, "VIDEO_TS")
                if not os.path.isdir(ts_path):
                    ts_path = work_path
                self.append_log(f"Detected VIDEO_TS path: {ts_path}\n")
                vobs = self.get_videos(ts_path)
                if not vobs:
                    GLib.idle_add(self.label_selected.set_text, f"No VOB files found in {ts_path}")
                    self.append_log(f"Warning: No VOB files found in {ts_path}\n")
                    continue

                input_args = []
                for vob in vobs:
                    input_args.extend(["-i", vob])

                n = len(vobs)
                filter_complex = f"concat=n={n}:v=1:a=1 [v] [a]; [v] scale=iw:ih [vout]"

                cmd = [
                    "ffmpeg", "-y",
                    *input_args,
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", "[a]",
                    "-c:v", codec,
                    "-preset", preset_to_use
                ]

                if preset_to_use in ['fast', 'faster', 'veryfast', 'superfast', 'ultrafast', "default", "llhp", "ll", "hp"]:
                    cmd.extend([
                        "-b:v", str(bitrate_value),
                        "-maxrate", str(bitrate_value * 2),
                        "-bufsize", str(bitrate_value * 4),
                        "-c:a", audio_codec,
                        "-b:a", "192k",
                        "-movflags", "+faststart",
                        "-f", ext,
                        out_file,
                    ])
                else:
                    cmd.extend([
                        "-crf", str(cq),
                        "-b:v", str(bitrate_value),
                        "-c:a", audio_codec,
                        "-b:a", "192k",
                        "-movflags", "+faststart",
                        "-f", ext,
                        out_file,
                    ])

                input_for_duration = vobs[0]
            else:
                self.append_log(f"Processing single file: {original_path}\n")

                cmd = [
                    "ffmpeg", "-y",
                    "-i", original_path,
                    "-c:v", codec,
                    "-preset", preset_to_use,
                ]

                if preset_to_use in ['fast', 'faster', 'veryfast', 'superfast', 'ultrafast', "default", "llhp", "ll", "hp"]:
                    cmd.extend([
                        "-b:v", str(bitrate_value),
                        "-maxrate", str(bitrate_value * 2),
                        "-bufsize", str(bitrate_value * 4),
                        "-c:a", audio_codec,
                        "-b:a", "192k",
                        "-movflags", "+faststart",
                        "-f", ext,
                        out_file,
                    ])
                else:
                    cmd.extend([
                        "-crf", str(cq),
                        "-b:v", str(bitrate_value),
                        "-vf", vf,
                        "-c:a", audio_codec,
                        "-b:a", "192k",
                        "-movflags", "+faststart",
                        "-f", ext,
                        out_file,
                    ])

                input_for_duration = original_path

            # Run ffmpeg synchronously here sequentially
            self.run_ffmpeg_sync(cmd, input_for_duration)

        self.batch_files.clear()
        GLib.idle_add(self.label_selected.set_text, "No files or folders selected")
        GLib.idle_add(self.reset_ui)

    def run_ffmpeg_sync(self, cmd, input_file):
        self.append_log("Running: " + " ".join(cmd) + "\n\n")
        self.duration_seconds = self.get_duration(input_file)
        GLib.idle_add(self.progressbar.set_fraction, 0)
        GLib.idle_add(self.progressbar.set_text, "0%")
        GLib.idle_add(self.progressbar.set_show_text, True)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
            )
            self.process = process

            pattern = re.compile(r"time=(\d+):(\d+):(\d+).(\d+)")
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                GLib.idle_add(self.append_log, line)
                m = pattern.search(line)
                if m and self.duration_seconds:
                    h, m_, s, cs = map(int, m.groups())
                    elapsed = h * 3600 + m_ * 60 + s + cs / 100
                    progress = min(elapsed / self.duration_seconds, 1.0)
                    GLib.idle_add(self.update_progress, progress)

            ret = process.wait()
            if ret == 0:
                GLib.idle_add(self.append_log, "\n✅ Conversion completed successfully.\n")
                GLib.idle_add(self.update_progress, 1.0)
                GLib.idle_add(self.show_dialog)
            else:
                GLib.idle_add(self.append_log, f"\n❌ Conversion failed (code {ret}).\n")
                GLib.idle_add(self.update_progress, 0.0)
        except Exception as e:
            GLib.idle_add(self.append_log, f"\nError: {str(e)}\n")
        finally:
            GLib.idle_add(self.reset_ui)
            self.process = None

    def update_progress(self, fraction):
        self.progressbar.set_fraction(fraction)
        self.progressbar.set_text(f"{int(fraction * 100)}%")
        while Gtk.events_pending():
            Gtk.main_iteration()
        return False

    def show_dialog(self, filename=""):
        dlg = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"Conversion Completed: {filename}"
        )
        dlg.format_secondary_text("The video file was processed successfully.")
        dlg.run()
        dlg.destroy()

    def update_gpu_info(self):
        self.gpu_label.set_text("Detecting hardware...")
        GLib.idle_add(self._detect_gpu)

    def _detect_gpu(self):
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                text=True)
            gpus = output.strip().splitlines()
        except Exception:
            gpus = ["Nvidia not found"]

        try:
            output = subprocess.check_output(["ffmpeg", "-hide_banner", "-encoders"],
                                             text=True)
            nvenc = []
            if "h264_nvenc" in output:
                nvenc.append("h264_nvenc")
            if "hevc_nvenc" in output:
                nvenc.append("hevc_nvenc")
        except Exception:
            nvenc = ["NVENC not detected"]

        self.gpu_label.set_text("GPUs: " + ", ".join(gpus) + "\nNVENC: " +
                                ", ".join(nvenc))

    def reset_ui(self):
        self.process = None
        self.btn_convert.set_sensitive(True)
        self.btn_cancel.set_sensitive(False)
        self.btn_convert.set_label("Convert")
        self.label_selected.set_text("No files or folders selected")
        while Gtk.events_pending():
            Gtk.main_iteration()
        return False

    def on_format_changed(self, combo):
        if self.entry_output.get_text():
            base = self.entry_output.get_text()
            if "." in base:
                base = base.rsplit(".", 1)[0]
            ext = self.get_combo_text(combo) or "mp4"
            self.entry_output.set_text(f"{base}.{ext}")


if __name__ == "__main__":
    def signal_handler(sig, frame):
        Gtk.main_quit()

    signal.signal(signal.SIGINT, signal_handler)
    window = FFmpegGUI()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
