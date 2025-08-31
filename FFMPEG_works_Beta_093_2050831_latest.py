# ffmpeg_commander.py — v0.9.3  
# Note: This is the full program in one block. Window styling is unchanged.  
# Adds “Super Convert” with faster, visually‑transparent x265 settings and better CPU scaling.  
  
import gi  
gi.require_version('Gtk', '3.0')  
from gi.repository import Gtk, GLib, Gdk  
  
import subprocess  
import os  
import threading  
import re  
import webbrowser  
import signal  
import json  
  
def load_style():  
    # Original light/retro style kept as-is (per your request)  
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
    VERSION = "0.9.3"  
  
    def __init__(self):  
        super().__init__(title=f"Ray’s FFmpeg Commander Toolbox - v{self.VERSION} Beta")  
        self.set_border_width(8)  
        self.set_default_size(1200, 900)  
        self.set_resizable(True)  
  
        # State  
        self.batch_files = []  
        self.process = None  
        self.duration_seconds = 0  
        self.cancel_requested = False  
  
        # Batch/ETA tracking  
        self.total_items = 0  
        self.current_index = 0  
        self.item_durations = []  
        self.total_content_seconds = 0.0  
        self.completed_content_seconds = 0.0  
        self.current_item_duration = 0.0  
        self.last_speed = 1.0  
  
        # NVENC availability  
        self._nvenc_available = set()  
  
        # Super Convert helpers  
        self._super_bit_depth = None     # desired encode bit depth when Super is used  
        self._super_x265_params = None   # extra x265 params for speed scaling  
  
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
  
        # Batch status  
        self.label_batch_status = Gtk.Label(label="", xalign=0)  
        vbox.pack_start(self.label_batch_status, False, False, 0)  
  
        # Output naming  
        out_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(out_box, False, False, 0)  
  
        out_label = Gtk.Label(label="Output filename (suffix added automatically)", xalign=0)  
        out_box.pack_start(out_label, False, False, 0)  
  
        self.entry_output = Gtk.Entry()  
        self.entry_output.set_hexpand(True)  
        out_box.pack_start(self.entry_output, False, False, 0)  
  
        # Container  
        format_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(format_box, False, False, 0)  
  
        format_label = Gtk.Label(  
            label="Container (file format for the output file: mp4, mkv, mov, avi, webm).",  
            xalign=0  
        )  
        format_box.pack_start(format_label, False, False, 0)  
  
        self.store_format = Gtk.ListStore(str)  
        for fmt in ['mp4', 'mkv', 'mov', 'avi', 'webm']:  
            self.store_format.append([fmt])  
        self.combo_format = Gtk.ComboBox.new_with_model(self.store_format)  
        renderer = Gtk.CellRendererText()  
        self.combo_format.pack_start(renderer, True)  
        self.combo_format.add_attribute(renderer, "text", 0)  
        self.combo_format.set_active(0)  # mp4  
        self.combo_format.set_hexpand(True)  
        self.combo_format.connect("changed", self.on_format_changed)  
        format_box.pack_start(self.combo_format, False, False, 0)  
  
        # Video encoder  
        codec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(codec_box, False, False, 0)  
  
        codec_label = Gtk.Label(  
            label="Video encoder (codec implementation used by FFmpeg to produce the video stream).",  
            xalign=0  
        )  
        codec_box.pack_start(codec_label, False, False, 0)  
  
        self.store_codec = Gtk.ListStore(str, str)  # display text, ffmpeg name  
        codec_items = [  
            ("H.264 / AVC (libx264 – CPU)", "libx264"),  
            ("H.265 / HEVC (libx265 – CPU)", "libx265"),  
            ("H.264 / AVC (NVENC – NVIDIA GPU)", "h264_nvenc"),  
            ("H.265 / HEVC (NVENC – NVIDIA GPU)", "hevc_nvenc"),  
            ("VP8 (libvpx)", "libvpx"),  
            ("VP9 (libvpx-vp9)", "libvpx-vp9"),  
            ("Motion JPEG (mjpeg)", "mjpeg"),  
        ]  
        for disp, enc in codec_items:  
            self.store_codec.append([disp, enc])  
        self.combo_codec = Gtk.ComboBox.new_with_model(self.store_codec)  
        renderer2 = Gtk.CellRendererText()  
        self.combo_codec.pack_start(renderer2, True)  
        self.combo_codec.add_attribute(renderer2, "text", 0)  
        self.combo_codec.set_active(0)  
        self.combo_codec.set_hexpand(True)  
        codec_box.pack_start(self.combo_codec, False, False, 0)  
  
        # Preset  
        preset_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(preset_box, False, False, 0)  
  
        preset_label = Gtk.Label(  
            label="Preset (speed/quality trade‑off; x264/x265 and NVENC).",  
            xalign=0  
        )  
        preset_box.pack_start(preset_label, False, False, 0)  
  
        self.store_preset = Gtk.ListStore(str)  
        for p in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast',  
                  'medium', 'slow', 'slower', 'veryslow', 'placebo']:  
            self.store_preset.append([p])  
        self.combo_preset = Gtk.ComboBox.new_with_model(self.store_preset)  
        renderer3 = Gtk.CellRendererText()  
        self.combo_preset.pack_start(renderer3, True)  
        self.combo_preset.add_attribute(renderer3, "text", 0)  
        self.combo_preset.set_active(5)  # medium  
        self.combo_preset.set_hexpand(True)  
        preset_box.pack_start(self.combo_preset, False, False, 0)  
  
        # Rate control (NVENC only)  
        rc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(rc_box, False, False, 0)  
  
        rc_label = Gtk.Label(label="Rate control (NVENC only here): VBR or CBR.", xalign=0)  
        rc_box.pack_start(rc_label, False, False, 0)  
  
        self.store_rc = Gtk.ListStore(str)  
        for rc in ['vbr', 'cbr']:  
            self.store_rc.append([rc])  
        self.combo_rc = Gtk.ComboBox.new_with_model(self.store_rc)  
        renderer4 = Gtk.CellRendererText()  
        self.combo_rc.pack_start(renderer4, True)  
        self.combo_rc.add_attribute(renderer4, "text", 0)  
        self.combo_rc.set_active(0)  # vbr  
        self.combo_rc.set_hexpand(True)  
        rc_box.pack_start(self.combo_rc, False, False, 0)  
  
        # Quality slider  
        cq_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(cq_box, False, False, 0)  
  
        self.cq_label = Gtk.Label(label="Quality (CRF/CQ 0–51; lower = higher quality)", xalign=0)  
        cq_box.pack_start(self.cq_label, False, False, 0)  
  
        self.adj_cq = Gtk.Adjustment(value=23, lower=0, upper=51, step_increment=1)  
        self.scale_cq = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj_cq)  
        self.scale_cq.set_digits(0)  
        self.scale_cq.set_value(23)  
        self.scale_cq.set_value_pos(Gtk.PositionType.RIGHT)  
        cq_box.pack_start(self.scale_cq, False, False, 0)  
  
        # Bitrate  
        bitrate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(bitrate_box, False, False, 0)  
  
        bitrate_label = Gtk.Label(label="Bitrate (kbps) - set 0 for quality-based", xalign=0)  
        bitrate_box.pack_start(bitrate_label, False, False, 0)  
  
        self.entry_bitrate = Gtk.Entry()  
        self.entry_bitrate.set_text("0")  
        self.entry_bitrate.set_hexpand(True)  
        bitrate_box.pack_start(self.entry_bitrate, False, False, 0)  
  
        # Checkboxes  
        self.chk_spatial = Gtk.CheckButton(label="Enable Spatial AQ (NVENC encoders only)")  
        self.chk_spatial.set_active(True)  
        vbox.pack_start(self.chk_spatial, False, False, 0)  
  
        self.chk_bw = Gtk.CheckButton(label="Black & White (Grayscale)")  
        self.chk_bw.set_active(False)  
        vbox.pack_start(self.chk_bw, False, False, 0)  
  
        # Audio encoder  
        audio_codec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)  
        vbox.pack_start(audio_codec_box, False, False, 0)  
  
        audio_codec_label = Gtk.Label(label="Audio encoder", xalign=0)  
        audio_codec_box.pack_start(audio_codec_label, False, False, 0)  
  
        self.store_audio_codec = Gtk.ListStore(str, str)  
        for disp, enc in [("AAC (aac)", "aac"),  
                          ("MP3 (libmp3lame)", "libmp3lame"),  
                          ("Opus (libopus)", "libopus"),  
                          ("AC-3 (ac3)", "ac3")]:  
            self.store_audio_codec.append([disp, enc])  
        self.combo_audio_codec = Gtk.ComboBox.new_with_model(self.store_audio_codec)  
        renderer_audio = Gtk.CellRendererText()  
        self.combo_audio_codec.pack_start(renderer_audio, True)  
        self.combo_audio_codec.add_attribute(renderer_audio, "text", 0)  
        self.combo_audio_codec.set_active(0)  
        self.combo_audio_codec.set_hexpand(True)  
        audio_codec_box.pack_start(self.combo_audio_codec, False, False, 0)  
  
        # Buttons row  
        btn_box = Gtk.Box(spacing=6)  
        vbox.pack_start(btn_box, False, False, 0)  
  
        self.btn_convert = Gtk.Button(label="Convert")  
        self.btn_convert.connect("clicked", self.on_convert)  
        btn_box.pack_start(self.btn_convert, False, False, 0)  
  
        # Super Convert (to the right of Convert)  
        self.btn_super = Gtk.Button(label="Super Convert")  
        self.btn_super.connect("clicked", self.on_super_convert)  
        btn_box.pack_start(self.btn_super, False, False, 0)  
  
        self.btn_cancel = Gtk.Button(label="Cancel")  
        self.btn_cancel.connect("clicked", self.on_cancel)  
        self.btn_cancel.set_sensitive(False)  
        btn_box.pack_start(self.btn_cancel, False, False, 0)  
  
        self.btn_donate = Gtk.Button(label="Donate (PayPal) - buy me a coffee!")  
        self.btn_donate.set_name("donate-button")  
        self.btn_donate.connect("clicked", self.on_donate_clicked)  
        btn_box.pack_start(self.btn_donate, False, False, 0)  
  
        # Info label: Convert vs Super Convert  
        info = ("Convert = use the settings above.  "  
                "Super Convert = optimized for speed + size while staying visually transparent "  
                "(MP4 + HEVC/x265, faster preset by resolution, CRF tuned, parallel search; "  
                "10‑bit only when source is 10/12‑bit).")  
        self.label_modes = Gtk.Label(label=info, xalign=0)  
        self.label_modes.set_line_wrap(True)  
        vbox.pack_start(self.label_modes, False, False, 0)  
  
        # Output view  
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
  
        # ETA labels  
        self.label_file_eta = Gtk.Label(label="File ETA: —", xalign=0)  
        vbox.pack_start(self.label_file_eta, False, False, 0)  
  
        self.label_eta = Gtk.Label(label="Overall ETA: —", xalign=0)  
        vbox.pack_start(self.label_eta, False, False, 0)  
  
        self.progressbar = Gtk.ProgressBar()  
        self.progressbar.set_size_request(-1, 40)  
        vbox.pack_start(self.progressbar, False, False, 0)  
  
        self.combo_codec.connect("changed", self.on_codec_changed)  
        self.on_codec_changed(self.combo_codec)  
  
        self.show_all()  
  
    # ---------------- UI helpers ----------------  
  
    def append_log(self, text: str):  
        def _append():  
            end_iter = self.textbuffer.get_end_iter()  
            self.textbuffer.insert(end_iter, text)  
            mark = self.textbuffer.create_mark(None, self.textbuffer.get_end_iter(), False)  
            self.textview.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)  
            return False  
        GLib.idle_add(_append)  
  
    def get_combo_text(self, combo):  
        it = combo.get_active_iter()  
        if it is not None:  
            model = combo.get_model()  
            return model[it][0]  
        return None  
  
    def get_combo_value(self, combo, column=0):  
        it = combo.get_active_iter()  
        if it is not None:  
            model = combo.get_model()  
            return model[it][column]  
        return None  
  
    def on_codec_changed(self, combo):  
        enc = self.get_combo_value(self.combo_codec, 1)  
        is_x26x = enc in ("libx264", "libx265")  
        is_nvenc = enc in ("h264_nvenc", "hevc_nvenc")  
        self.combo_preset.set_sensitive(is_x26x or is_nvenc)  
        self.combo_rc.set_sensitive(is_nvenc)  
        self.chk_spatial.set_sensitive(is_nvenc)  
        if is_x26x:  
            self.cq_label.set_text("Quality (CRF 0–51, x264/x265; lower = higher quality)")  
            self.scale_cq.set_sensitive(True)  
        elif is_nvenc:  
            self.cq_label.set_text("Quality (NVENC CQ 0–51; used with VBR/RC)")  
            self.scale_cq.set_sensitive(True)  
        else:  
            self.cq_label.set_text("Quality control not used by this encoder")  
            self.scale_cq.set_sensitive(False)  
  
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
  
    # ---------------- Super Convert ----------------  
  
    def _x265_speed_params(self, ultra=False, add_no_sao=False):  
        # Build x265 param string that scales to many cores with minimal visual impact  
        ncpu = os.cpu_count() or 8  
        frame_threads = 4 if ncpu >= 16 else 3  
        lookahead = 12 if ultra else 15  
        parts = [  
            "pmode=1",          # parallel mode decision  
            "pme=1",            # parallel motion estimation  
            f"frame-threads={frame_threads}",  
            "pools=full",  
            f"rc-lookahead={lookahead}",  
        ]  
        if add_no_sao:  
            parts.append("no-sao=1")  
        return ":".join(parts)  
  
    def probe_stream(self, path):  
        try:  
            j = subprocess.check_output([  
                "ffprobe","-v","error","-select_streams","v:0",  
                "-show_entries","stream=codec_name,bit_rate,width,height,pix_fmt",  
                "-of","json", path  
            ], text=True)  
            s = json.loads(j)["streams"][0]  
            return {  
                "codec": s.get("codec_name"),  
                "bit_rate": int(s.get("bit_rate") or 0),  
                "w": int(s.get("width") or 0),  
                "h": int(s.get("height") or 0),  
                "pix_fmt": s.get("pix_fmt") or ""  
            }  
        except Exception:  
            return {"codec": None, "bit_rate": 0, "w": 0, "h": 0, "pix_fmt": ""}  
  
    def choose_super_settings(self, info):  
        # Faster presets by resolution with small CRF offsets to keep size/quality balanced  
        h = int(info.get("h") or 0)  
        if h >= 2000:            # 4K  
            preset = "fast"  
            crf = 24  
            xparams = self._x265_speed_params(ultra=True, add_no_sao=True)  # push harder for 4K  
        elif h >= 1000:          # 1080–1440p  
            preset = "medium"  
            crf = 25  
            xparams = self._x265_speed_params()  
        elif h >= 700:           # 720p  
            preset = "medium"  
            crf = 27  
            xparams = self._x265_speed_params()  
        else:                    # SD  
            preset = "fast"  
            crf = 29  
            xparams = self._x265_speed_params()  
        # Prefer 10-bit only when the source is 10/12-bit; otherwise 8-bit for speed  
        bit_depth = 10 if re.search(r"10|12", info.get("pix_fmt","")) else 8  
        return {"codec":"libx265","preset":preset,"crf":crf,"bit_depth":bit_depth,"x265_params":xparams}  
  
    def on_super_convert(self, _):  
        if not self.batch_files:  
            self.label_selected.set_text("No files or folders selected.")  
            return  
        # Super Convert forces MP4 container for broad compatibility  
        self.combo_format.set_active(0)  # mp4  
        # Probe first item (or first VOB inside VIDEO_TS) to guide settings  
        first = self.batch_files[0]  
        probe_target = first  
        if self.is_videots(first):  
            ts = first if os.path.basename(first).upper() == "VIDEO_TS" else os.path.join(first, "VIDEO_TS")  
            vobs = self.get_videos(ts if os.path.isdir(ts) else first)  
            if vobs:  
                probe_target = vobs[0]  
        info = self.probe_stream(probe_target)  
        rec = self.choose_super_settings(info)  
  
        # Select libx265  
        it = self.store_codec.get_iter_first()  
        while it:  
            if self.store_codec[it][1] == rec["codec"]:  
                self.combo_codec.set_active_iter(it); break  
            it = self.store_codec.iter_next(it)  
  
        # Preset and CRF  
        it = self.store_preset.get_iter_first()  
        while it:  
            if self.store_preset[it][0] == rec["preset"]:  
                self.combo_preset.set_active_iter(it); break  
            it = self.store_preset.iter_next(it)  
        self.scale_cq.set_value(rec["crf"])  
        self.entry_bitrate.set_text("0")  
  
        # Save Super hints  
        self._super_bit_depth = rec["bit_depth"]  
        self._super_x265_params = rec.get("x265_params")  
  
        # Launch conversion  
        self.on_convert(None)  
  
    # ---------------- Convert / Build args ----------------  
  
    def on_convert(self, widget):  
        if not self.batch_files:  
            self.label_selected.set_text("No files or folders selected.")  
            return  
        self.cancel_requested = False  
        self.total_items = len(self.batch_files)  
        self.current_index = 0  
        self.completed_content_seconds = 0.0  
        self.last_speed = 1.0  
  
        self.precompute_batch_durations()  
        if self.total_content_seconds > 0:  
            self.label_eta.set_text("Overall ETA: calculating…")  
        else:  
            self.label_eta.set_text("Overall ETA: unknown")  
  
        self.label_file_eta.set_text("File ETA: calculating…")  
        self.label_batch_status.set_text(f"Preparing… (0 of {self.total_items})")  
        self.btn_convert.set_sensitive(False)  
        self.btn_super.set_sensitive(False)  
        self.btn_cancel.set_sensitive(True)  
        self.btn_convert.set_label("Converting...")  
        threading.Thread(target=self.process_batch, daemon=True).start()  
  
    def _spawn_kwargs(self):  
        if os.name == 'posix':  
            return {'preexec_fn': os.setsid}  
        elif os.name == 'nt':  
            return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}  
        return {}  
  
    def _terminate_current_ffmpeg(self, force=False):  
        p = self.process  
        if not p or p.poll() is not None:  
            return  
        try:  
            if os.name == 'posix':  
                os.killpg(os.getpgid(p.pid), signal.SIGKILL if force else signal.SIGTERM)  
            else:  
                p.kill() if force else p.terminate()  
        except Exception:  
            pass  
  
    def on_cancel(self, widget):  
        self.cancel_requested = True  
        self.append_log("Cancellation requested…\n")  
        self._terminate_current_ffmpeg()  
  
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
  
    def get_input_bit_depth(self, path):  
        try:  
            out = subprocess.check_output(  
                ["ffprobe", "-v", "error", "-select_streams", "v:0",  
                 "-show_entries", "stream=pix_fmt",  
                 "-of", "default=nw=1:nk=1", path],  
                text=True).strip()  
            m = re.search(r"(\d+)", out)  
            return int(m.group(1)) if m else 8  
        except Exception:  
            return 8  
  
    def build_video_args(self, codec, preset, rc_mode, cq, bitrate_kbps, desired_bit_depth, use_spatial_aq, container_ext):  
        args = ["-c:v", codec]  
  
        if codec in ("h264_nvenc", "hevc_nvenc"):  
            nvenc_preset_map = {  
                "ultrafast": "p1", "superfast": "p1", "veryfast": "p2", "faster": "p3",  
                "fast": "p4", "medium": "p5", "slow": "p6", "slower": "p6",  
                "veryslow": "p7", "placebo": "p7",  
            }  
            args += ["-preset", nvenc_preset_map.get(preset, "p5")]  
            if use_spatial_aq:  
                args += ["-spatial-aq", "1"]  
            args += ["-rc:v", rc_mode]  
            if rc_mode == "cbr":  
                br = bitrate_kbps if bitrate_kbps and bitrate_kbps > 0 else 4000  
                args += ["-b:v", f"{br}k", "-maxrate", f"{br}k", "-bufsize", f"{br*2}k"]  
            else:  
                args += ["-cq:v", str(int(cq))]  
                if bitrate_kbps and bitrate_kbps > 0:  
                    args += ["-b:v", f"{bitrate_kbps}k",  
                             "-maxrate", f"{bitrate_kbps*2}k",  
                             "-bufsize", f"{bitrate_kbps*4}k"]  
                else:  
                    args += ["-b:v", "0"]  
            if codec == "h264_nvenc":  
                args += ["-pix_fmt", "yuv420p"]  
            else:  # hevc_nvenc  
                if desired_bit_depth >= 10:  
                    args += ["-pix_fmt", "p010le", "-profile:v", "main10"]  
                else:  
                    args += ["-pix_fmt", "yuv420p"]  
            # Tagging will be added in outer command for MP4/MOV  
  
        else:  
            if codec in ("libx264", "libx265"):  
                args += ["-preset", preset]  
            if bitrate_kbps and bitrate_kbps > 0:  
                args += ["-b:v", f"{bitrate_kbps}k",  
                         "-maxrate", f"{bitrate_kbps*2}k",  
                         "-bufsize", f"{bitrate_kbps*4}k"]  
            else:  
                if codec in ("libx264", "libx265"):  
                    args += ["-crf", str(int(cq))]  
  
            if codec == "libx265":  
                params = []  
                if desired_bit_depth >= 10:  
                    args += ["-pix_fmt", "yuv420p10le"]  
                    params.append("profile=main10")  
                else:  
                    args += ["-pix_fmt", "yuv420p"]  
                if self._super_x265_params:  
                    params.append(self._super_x265_params)  
                if params:  
                    args += ["-x265-params", ":".join(params)]  
            elif codec == "libx264":  
                args += ["-pix_fmt", "yuv420p"]  
  
        return args  
  
    # ---------------- ETA helpers ----------------  
  
    def format_seconds(self, secs):  
        secs = max(0, int(round(secs)))  
        h = secs // 3600  
        m = (secs % 3600) // 60  
        s = secs % 60  
        return f"{h:d}:{m:02d}:{s:02d}"  
  
    def compute_item_duration(self, path):  
        if self.is_videots(path):  
            ts_path = path if os.path.basename(path).upper() == "VIDEO_TS" else os.path.join(path, "VIDEO_TS")  
            if not os.path.isdir(ts_path):  
                ts_path = path  
            total = 0.0  
            for v in self.get_videos(ts_path):  
                total += self.get_duration(v) or 0.0  
            return total  
        else:  
            return self.get_duration(path) or 0.0  
  
    def precompute_batch_durations(self):  
        self.item_durations = []  
        total = 0.0  
        for p in self.batch_files:  
            d = self.compute_item_duration(p)  
            self.item_durations.append(d)  
            total += max(d, 0.0)  
        self.total_content_seconds = total  
  
    def update_overall_eta(self, elapsed_in_current, speed):  
        if self.total_content_seconds > 0:  
            processed = self.completed_content_seconds + min(elapsed_in_current, self.current_item_duration)  
            remaining_content = max(self.total_content_seconds - processed, 0.0)  
            eff_speed = speed if speed and speed > 0 else (self.last_speed if self.last_speed > 0 else 1.0)  
            eta_wall = remaining_content / eff_speed  
            text = f"Overall ETA: {self.format_seconds(eta_wall)} at ~{eff_speed:.2f}x"  
        else:  
            done_units = (self.current_index - 1)  
            part = min(1.0, elapsed_in_current / self.current_item_duration) if self.current_item_duration > 0 else 0.0  
            overall_frac = ((done_units + part) / self.total_items) if self.total_items else 0.0  
            text = f"Overall progress: {int(overall_frac * 100)}% (ETA unknown)"  
        GLib.idle_add(self.label_eta.set_text, text)  
  
    def update_file_eta(self, elapsed_in_current, speed):  
        dur = self.duration_seconds or self.current_item_duration  
        eff_speed = speed if speed and speed > 0 else (self.last_speed if self.last_speed > 0 else 1.0)  
        if dur and eff_speed > 0:  
            remaining = max(dur - elapsed_in_current, 0.0) / eff_speed  
            text = f"File ETA: {self.format_seconds(remaining)} at ~{eff_speed:.2f}x"  
        else:  
            text = "File ETA: unknown"  
        GLib.idle_add(self.label_file_eta.set_text, text)  
  
    # ---------------- Core processing ----------------  
  
    def process_batch(self):  
        self.append_log(f"Starting batch of {len(self.batch_files)} items\n")  
        for idx, path in enumerate(self.batch_files):  
            if self.cancel_requested:  
                break  
  
            self.current_index = idx + 1  
            GLib.idle_add(self.update_batch_status, self.current_index, self.total_items, path)  
            self.append_log(f"Processing item {idx + 1}: {path}\n")  
  
            original_path = path  
            work_path = os.path.dirname(path) if os.path.basename(path).upper() == "VIDEO_TS" else path  
            base = os.path.basename(work_path)  
            ext = (self.get_combo_text(self.combo_format) or "mp4").lower()  
  
            # duration for ETAs  
            self.current_item_duration = self.item_durations[idx] if idx < len(self.item_durations) else self.compute_item_duration(path)  
            GLib.idle_add(self.label_file_eta.set_text, "File ETA: calculating…")  
  
            bitrate_txt = self.entry_bitrate.get_text().strip()  
            if not bitrate_txt.isdigit():  
                GLib.idle_add(self.label_selected.set_text, "Bitrate must be numeric (kbps, e.g., 3000).")  
                break  
            bitrate_value = int(bitrate_txt)  
  
            cq = int(self.scale_cq.get_value())  
            codec = self.get_combo_value(self.combo_codec, 1) or "libx264"  
            preset = self.get_combo_text(self.combo_preset) or "medium"  
            audio_codec = self.get_combo_value(self.combo_audio_codec, 1) or "aac"  
            rc_mode = self.get_combo_text(self.combo_rc) or "vbr"  
  
            # Build optional video filter chain (skip scale=iw:ih no-op)  
            vf = None  
            if self.chk_bw.get_active():  
                vf = "hue=s=0"  
  
            if len(self.batch_files) > 1:  
                out_file_name = f"{base}_converted_{idx + 1}.{ext}"  
            else:  
                out_file_name = self.entry_output.get_text() or f"{base}_converted.{ext}"  
  
            if self.is_videots(work_path):  
                parent_dir = os.path.dirname(work_path)  
                out_file = os.path.join(parent_dir, out_file_name)  
            else:  
                out_file = out_file_name  
  
            movflags_args = ["-movflags", "+faststart"] if ext in ("mp4", "mov", "m4a", "3gp", "3g2", "mj2", "m4v") else []  
            tag_args = ["-tag:v", "hvc1"] if (ext in ("mp4","mov","m4v") and codec in ("libx265","hevc_nvenc")) else []  
  
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
                if self.chk_bw.get_active():  
                    filter_complex = f"concat=n={n}:v=1:a=1 [v] [a]; [v] hue=s=0 [vout]"  
                    vmap = "[vout]"  
                else:  
                    filter_complex = f"concat=n={n}:v=1:a=1 [v] [a]"  
                    vmap = "[v]"  
  
                bit_depth = 8  
                if self._super_bit_depth is not None and codec in ("libx265","hevc_nvenc"):  
                    bit_depth = max(bit_depth, int(self._super_bit_depth))  
                video_args = self.build_video_args(codec, preset, rc_mode, cq, bitrate_value, bit_depth, self.chk_spatial.get_active(), ext)  
  
                cmd = [  
                    "ffmpeg", "-y",  
                    *input_args,  
                    "-filter_complex", filter_complex,  
                    "-map", vmap,  
                    "-map", "[a]",  
                    *video_args,  
                    *tag_args,  
                    "-c:a", audio_codec,  
                    "-b:a", "192k",  
                    *movflags_args,  
                    "-f", ext,  
                    out_file,  
                ]  
                input_for_duration = vobs[0]  
            else:  
                self.append_log(f"Processing single file: {original_path}\n")  
  
                bit_depth = self.get_input_bit_depth(original_path)  
                if self._super_bit_depth is not None and codec in ("libx265","hevc_nvenc"):  
                    bit_depth = max(bit_depth, int(self._super_bit_depth))  
                video_args = self.build_video_args(codec, preset, rc_mode, cq, bitrate_value, bit_depth, self.chk_spatial.get_active(), ext)  
  
                cmd = [  
                    "ffmpeg", "-y",  
                    "-i", original_path,  
                    *video_args,  
                    *tag_args,  
                ]  
                if vf:  
                    cmd += ["-vf", vf]  
                cmd += [  
                    "-c:a", audio_codec,  
                    "-b:a", "192k",  
                    *movflags_args,  
                    "-f", ext,  
                    out_file,  
                ]  
                input_for_duration = original_path  
  
            self.run_ffmpeg_sync(cmd, input_for_duration, duration_override=self.current_item_duration)  
  
            if self.cancel_requested:  
                break  
  
            self.completed_content_seconds += max(self.current_item_duration, 0.0)  
  
        self.batch_files.clear()  
        if self.cancel_requested:  
            self.append_log("Batch cancelled. No more files will be processed.\n")  
            GLib.idle_add(self.progressbar.set_text, "Cancelled")  
            GLib.idle_add(self.label_file_eta.set_text, "File ETA: cancelled")  
        else:  
            self.append_log("Batch finished.\n")  
            GLib.idle_add(self.label_eta.set_text, "Overall ETA: 0:00:00 (done)")  
            GLib.idle_add(self.label_file_eta.set_text, "File ETA: 0:00:00 (done)")  
        GLib.idle_add(self.label_selected.set_text, "No files or folders selected")  
        GLib.idle_add(self.reset_ui)  
  
    def run_ffmpeg_sync(self, cmd, input_file, duration_override=None):  
        self.append_log("Running: " + " ".join(cmd) + "\n\n")  
        if duration_override and duration_override > 0:  
            self.duration_seconds = duration_override  
        else:  
            self.duration_seconds = self.get_duration(input_file)  
  
        GLib.idle_add(self.progressbar.set_fraction, 0)  
        GLib.idle_add(self.progressbar.set_show_text, True)  
  
        try:  
            process = subprocess.Popen(  
                cmd,  
                stdout=subprocess.PIPE,  
                stderr=subprocess.PIPE,  
                universal_newlines=True,  
                bufsize=1,  
                **self._spawn_kwargs()  
            )  
            self.process = process  
  
            re_time = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")  
            re_speed = re.compile(r"speed=\s*([\d\.]+)x")  
  
            for line in iter(process.stderr.readline, ''):  
                if not line:  
                    break  
                self.append_log(line)  
  
                if self.cancel_requested:  
                    self._terminate_current_ffmpeg()  
                    break  
  
                ms = re_speed.search(line)  
                if ms:  
                    try:  
                        self.last_speed = float(ms.group(1))  
                    except Exception:  
                        pass  
  
                mt = re_time.search(line)  
                if mt:  
                    try:  
                        h = int(mt.group(1))  
                        m_ = int(mt.group(2))  
                        s = int(mt.group(3))  
                        frac = float("0." + mt.group(4))  
                        elapsed = h * 3600 + m_ * 60 + s + frac  
                    except Exception:  
                        elapsed = 0.0  
  
                    if self.duration_seconds:  
                        progress = min(elapsed / self.duration_seconds, 1.0)  
                        GLib.idle_add(self.update_progress, progress)  
  
                    self.update_file_eta(elapsed, self.last_speed)  
                    self.update_overall_eta(elapsed, self.last_speed)  
  
            ret = process.wait()  
  
            if self.cancel_requested:  
                self.append_log("\n🛑 Cancelled by user.\n")  
                return  
  
            if ret == 0:  
                GLib.idle_add(self.append_log, "\n✅ Conversion completed successfully.\n")  
                GLib.idle_add(self.update_progress, 1.0)  
                GLib.idle_add(self.label_file_eta.set_text, "File ETA: 0:00:00 (done)")  
                if self.total_items <= 1:  
                    GLib.idle_add(self.show_dialog)  
            else:  
                GLib.idle_add(self.append_log, f"\n❌ Conversion failed (code {ret}).\n")  
                GLib.idle_add(self.update_progress, 0.0)  
        except Exception as e:  
            GLib.idle_add(self.append_log, f"\nError: {str(e)}\n")  
        finally:  
            self.process = None  
  
    def update_batch_status(self, index, total, path):  
        self.label_batch_status.set_text(f"File ({index} of {total}): {os.path.basename(path)}")  
        return False  
  
    def update_progress(self, fraction):  
        self.progressbar.set_fraction(fraction)  
        if self.total_items > 1:  
            self.progressbar.set_text(f"{int(fraction * 100)}% — File {self.current_index}/{self.total_items}")  
        else:  
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
            text=f"Conversion Completed"  
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
            output = subprocess.check_output(["ffmpeg", "-hide_banner", "-encoders"], text=True)  
            nvenc = []  
            if "h264_nvenc" in output:  
                nvenc.append("h264_nvenc")  
            if "hevc_nvenc" in output:  
                nvenc.append("hevc_nvenc")  
            self._nvenc_available = set(nvenc)  
            nvenc_label = ", ".join(nvenc) if nvenc else "not detected"  
        except Exception:  
            self._nvenc_available = set()  
            nvenc_label = "not detected"  
  
        self.gpu_label.set_text("GPUs: " + ", ".join(gpus) + "\nNVENC: " + nvenc_label)  
        self._prune_nvenc_from_codec_combo()  
  
    def _prune_nvenc_from_codec_combo(self):  
        avail = self._nvenc_available  
        to_remove_paths = []  
        it = self.store_codec.get_iter_first()  
        while it:  
            enc = self.store_codec[it][1]  
            if enc in ("h264_nvenc", "hevc_nvenc") and enc not in avail:  
                to_remove_paths.append(self.store_codec.get_path(it))  
            it = self.store_codec.iter_next(it)  
        for path in reversed(to_remove_paths):  
            it = self.store_codec.get_iter(path)  
            self.store_codec.remove(it)  
        if self.combo_codec.get_active() < 0 and len(self.store_codec) > 0:  
            self.combo_codec.set_active(0)  
        return False  
  
    def reset_ui(self):  
        self.process = None  
        self.btn_convert.set_sensitive(True)  
        self.btn_super.set_sensitive(True)  
        self.btn_cancel.set_sensitive(False)  
        self.btn_convert.set_label("Convert")  
        self.label_selected.set_text("No files or folders selected")  
        self.label_batch_status.set_text("")  
        # Reset ETA tracking  
        self.total_items = 0  
        self.current_index = 0  
        self.item_durations = []  
        self.total_content_seconds = 0.0  
        self.completed_content_seconds = 0.0  
        self.current_item_duration = 0.0  
        self.last_speed = 1.0  
        self.label_eta.set_text("Overall ETA: —")  
        self.label_file_eta.set_text("File ETA: —")  
        # Clear Super hints for next run  
        self._super_bit_depth = None  
        self._super_x265_params = None  
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
