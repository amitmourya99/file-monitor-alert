"""
dashboard.py
Main window shown after setup is complete. Shows monitoring status,
a live/historical activity log, and Start/Stop + Edit Settings controls.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os

import config_manager
import event_store
from monitor_engine import MonitorEngine

POLL_INTERVAL_MS = 500  # how often we check the event queue


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def bind_fade_hover(widget, normal_bg, hover_bg):
    """Binds a smooth color interpolation hover effect to a flat Tkinter widget."""
    try:
        widget.config(cursor="hand2")
    except Exception:
        pass
    widget.active_hover_anim = None
    
    def fade(target_color):
        current_bg = widget.cget("bg")
        try:
            start_rgb = hex_to_rgb(current_bg)
        except Exception:
            start_rgb = hex_to_rgb(normal_bg)
        end_rgb = hex_to_rgb(target_color)
        
        steps = 6
        delay = 10  # ms
        
        def step(i):
            if not widget.winfo_exists():
                return
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * (i / steps))
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * (i / steps))
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * (i / steps))
            widget.config(bg=rgb_to_hex((r, g, b)))
            if i < steps:
                widget.active_hover_anim = widget.after(delay, lambda: step(i + 1))
        
        if widget.active_hover_anim:
            widget.after_cancel(widget.active_hover_anim)
        step(1)

    widget.bind("<Enter>", lambda e: fade(hover_bg))
    widget.bind("<Leave>", lambda e: fade(normal_bg))


class Dashboard:
    def __init__(self, root):
        self.root = root
        self.config = config_manager.load_config()
        self.engine = MonitorEngine(self.config)

        self.root.title("File Monitor - Dashboard")
        self.root.geometry("820x600")
        self.root.minsize(680, 480)
        self.root.config(bg="#1e1e2e")

        # --- Load and Set Window Icon ---
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
            if os.path.exists(icon_path):
                pil_img = Image.open(icon_path)
                self.icon_img = ImageTk.PhotoImage(pil_img)
                self.root.iconphoto(False, self.icon_img)
        except Exception:
            pass

        # Batch email scheduler state
        self.pending_email_events = []
        self.email_timer_id = None
        self.pulse_timer = None
        self.tray_icon = None

        # Style configurations
        self._setup_styles()

        self._build_ui()
        self._load_history()
        self.pulse_step()  # Start the status light pulsing animation
        self._poll_events()  # start polling loop (safe even before monitoring starts)

        # Bind window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)
        
        # Check for updates in the background
        self._check_for_updates()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Style the Treeview
        style.configure("Treeview",
            background="#252538",
            foreground="#cdd6f4",
            rowheight=26,
            fieldbackground="#252538",
            borderwidth=0
        )
        style.map("Treeview",
            background=[("selected", "#313244")],
            foreground=[("selected", "#ffffff")]
        )
        
        # Style the Headings
        style.configure("Treeview.Heading",
            background="#181825",
            foreground="#cdd6f4",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0
        )
        
        # Style the Scrollbar
        style.configure("Vertical.TScrollbar",
            gripcount=0,
            background="#313244",
            troughcolor="#1e1e2e",
            bordercolor="#1e1e2e",
            arrowcolor="#cdd6f4",
            lightcolor="#313244",
            darkcolor="#313244"
        )

    # ---------- UI ----------
    def _build_ui(self):
        # --- Top status bar ---
        top = tk.Frame(self.root, bg="#181825")
        top.pack(fill="x")

        self.status_var = tk.StringVar(value="Stopped")
        tk.Label(
            top, text="Status:", fg="#cdd6f4", bg="#181825", font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(12, 4), pady=12)
        
        # Canvas status pulse light next to the status word
        self.status_canvas = tk.Canvas(top, width=16, height=16, bg="#181825", highlightthickness=0)
        self.status_canvas.pack(side="left", padx=4, pady=12)

        self.status_label = tk.Label(
            top, textvariable=self.status_var, fg="#f38ba8", bg="#181825", font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(side="left", pady=12)

        # Buttons
        self.start_stop_btn = tk.Button(
            top, text="Start Monitoring", bg="#a6e3a1", fg="#11111b",
            activebackground="#bbf7b6", activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
            padx=12, pady=4, command=self._toggle_monitoring
        )
        self.start_stop_btn.pack(side="right", padx=10, pady=8)
        self._update_start_stop_btn_hover()

        btn_settings = tk.Button(
            top, text="Edit Settings", bg="#89b4fa", fg="#11111b",
            activebackground="#b4befe", activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
            padx=12, pady=4, command=self._open_settings
        )
        btn_settings.pack(side="right", padx=4, pady=8)
        bind_fade_hover(btn_settings, "#89b4fa", "#9cc4ff")

        btn_clear = tk.Button(
            top, text="Clear History", bg="#f5c2e7", fg="#11111b",
            activebackground="#ffcff2", activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
            padx=12, pady=4, command=self._clear_history_click
        )
        btn_clear.pack(side="right", padx=4, pady=8)
        bind_fade_hover(btn_clear, "#f5c2e7", "#ffcff2")

        btn_export = tk.Button(
            top, text="Export Logs", bg="#89dceb", fg="#11111b",
            activebackground="#a6e3a1", activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
            padx=12, pady=4, command=self._export_history_click
        )
        btn_export.pack(side="right", padx=4, pady=8)
        bind_fade_hover(btn_export, "#89dceb", "#a6e3a1")

        # --- Stats cards panel ---
        stats_frame = tk.Frame(self.root, bg="#1e1e2e")
        stats_frame.pack(fill="x", padx=10, pady=(10, 0))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)

        def create_card(col, title, value_var, accent_color="#89b4fa"):
            card = tk.Frame(stats_frame, bg="#252538", highlightthickness=1, highlightbackground="#313244")
            card.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
            tk.Label(card, text=title.upper(), fg="#a6adc8", bg="#252538", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
            val_label = tk.Label(card, textvariable=value_var, bg="#252538", font=("Segoe UI", 12, "bold"), fg=accent_color)
            val_label.pack(anchor="w", padx=10, pady=(2, 8))
            return card

        # Card 1: Monitored Directory
        self.folder_card_var = tk.StringVar()
        create_card(0, "Monitored Directory", self.folder_card_var, "#89b4fa")
        self._update_folder_card_display()

        # Card 2: Event count
        self.event_count_card_var = tk.StringVar(value="0")
        create_card(1, "Total Events Logged", self.event_count_card_var, "#f9e2af")

        # Card 3: SMTP Host details
        smtp_details = f"{self.config.get('smtp_server', 'smtp.gmail.com')}:{self.config.get('smtp_port', 587)}"
        self.smtp_card_var = tk.StringVar(value=smtp_details)
        create_card(2, "Alert SMTP Service", self.smtp_card_var, "#f5c2e7")

        # --- Table Section Title ---
        title_frame = tk.Frame(self.root, bg="#1e1e2e")
        title_frame.pack(fill="x", padx=10, pady=(15, 0))
        tk.Label(
            title_frame,
            text="LIVE ACTIVITY FEED",
            font=("Segoe UI", 9, "bold"),
            fg="#89b4fa",
            bg="#1e1e2e"
        ).pack(side="left")

        # --- Activity log table ---
        table_frame = tk.Frame(self.root, bg="#1e1e2e")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        columns = ("time", "event", "path", "email_status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("time", text="Time")
        self.tree.heading("event", text="Event")
        self.tree.heading("path", text="File Path")
        self.tree.heading("email_status", text="Email Status")
        self.tree.column("time", width=140, anchor="w")
        self.tree.column("event", width=90, anchor="center")
        self.tree.column("path", width=340, anchor="w")
        self.tree.column("email_status", width=110, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Color configurations for cell tags
        self.tree.tag_configure("created", foreground="#a6e3a1")
        self.tree.tag_configure("deleted", foreground="#f38ba8")
        self.tree.tag_configure("modified", foreground="#f9e2af")

        # --- Footer ---
        footer = tk.Frame(self.root, bg="#1e1e2e")
        footer.pack(fill="x", padx=10, pady=(0, 10))
        self.count_var = tk.StringVar(value="0 events recorded")
        tk.Label(footer, textvariable=self.count_var, fg="#a6adc8", bg="#1e1e2e").pack(side="left")

    def _update_start_stop_btn_hover(self):
        """Bind correct hover coloring based on active monitoring state."""
        if self.engine.running:
            bind_fade_hover(self.start_stop_btn, "#f38ba8", "#ff9eb8")
        else:
            bind_fade_hover(self.start_stop_btn, "#a6e3a1", "#bbf7b6")

    def _update_folder_card_display(self):
        """Set dynamic folder statistics label text in the monitored directory card."""
        watch_folders = self.config.get("watch_folders", [])
        if not watch_folders and self.config.get("watch_folder"):
            watch_folders = [self.config.get("watch_folder")]
            
        if len(watch_folders) == 1:
            path_str = watch_folders[0]
            if len(path_str) > 35:
                path_str = "..." + path_str[-32:]
        elif len(watch_folders) > 1:
            path_str = f"{len(watch_folders)} Folders Active"
        else:
            path_str = "Not Configured"
        self.folder_card_var.set(path_str)

    # ---------- Animations ----------
    def pulse_step(self, step=0):
        """Draw an expanding/fading green radar ring or a static red light."""
        if not self.status_canvas.winfo_exists():
            return
            
        self.status_canvas.delete("all")
        
        if not self.engine.running:
            # Stopped: Static red circle
            self.status_canvas.create_oval(3, 3, 13, 13, fill="#f38ba8", outline="")
            self.pulse_timer = self.root.after(500, lambda: self.pulse_step(0))
            return
            
        # Active: Glowing radar ring
        # Draw solid green core
        self.status_canvas.create_oval(4, 4, 12, 12, fill="#a6e3a1", outline="")
        
        # Draw expanding pulsing ring
        max_steps = 15
        radius = 4 + (step / max_steps) * 6
        
        # Color math: fade from green (#a6e3a1) to status bar bg (#181825)
        start_rgb = hex_to_rgb("#a6e3a1")
        end_rgb = hex_to_rgb("#181825")
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * (step / max_steps))
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * (step / max_steps))
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * (step / max_steps))
        ring_color = rgb_to_hex((r, g, b))
        
        cx, cy = 8, 8
        self.status_canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=ring_color, width=1)
        
        next_step = (step + 1) % max_steps
        self.pulse_timer = self.root.after(70, lambda: self.pulse_step(next_step))

    # ---------- Background Tray Manager ----------
    def on_close_window(self):
        """Handle window close event: withdraw to tray or exit fully."""
        self.config = config_manager.load_config()
        if self.config.get("run_in_background_on_close", False):
            self.root.withdraw()
            if self.tray_icon is None:
                self.setup_tray()
            else:
                self.tray_icon.visible = True
            try:
                self.tray_icon.notify("File Monitor is running in the background.", "File Monitor Alert")
            except Exception:
                pass
        else:
            self.exit_app()

    def _check_for_updates(self):
        """Asynchronously queries GitHub Releases API to check for newer version releases."""
        import threading
        
        def run_check():
            import urllib.request
            import json
            import webbrowser
            
            # Note: The user will replace this with their actual GitHub repository details
            repo_owner = "amitm"  # Placeholder, change when creating repo
            repo_name = "file-monitor-alert"  # Placeholder, change when creating repo
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
            
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        github_version = data.get("tag_name", "").strip().lstrip("v")
                        html_url = data.get("html_url", "")
                        
                        if github_version:
                            local_ver = config_manager.APP_VERSION
                            
                            try:
                                local_parts = [int(p) for p in local_ver.split(".")]
                                github_parts = [int(p) for p in github_version.split(".")]
                                
                                max_len = max(len(local_parts), len(github_parts))
                                local_parts += [0] * (max_len - len(local_parts))
                                github_parts += [0] * (max_len - len(github_parts))
                                
                                if github_parts > local_parts:
                                    def prompt_user():
                                        if messagebox.askyesno(
                                            "Update Available",
                                            f"A new version (v{github_version}) is available!\n\n"
                                            f"Your current version: v{local_ver}\n\n"
                                            "Would you like to open the download page now?"
                                        ):
                                            webbrowser.open(html_url)
                                            
                                    self.root.after(0, prompt_user)
                            except ValueError:
                                if github_version != local_ver:
                                    def prompt_user_fallback():
                                        if messagebox.askyesno(
                                            "Update Available",
                                            f"A different version ({github_version}) is available on GitHub!\n\n"
                                            "Would you like to open the download page?"
                                        ):
                                            webbrowser.open(html_url)
                                    self.root.after(0, prompt_user_fallback)
            except Exception:
                pass
                
        threading.Thread(target=run_check, daemon=True).start()

    def setup_tray(self):
        """Initialize the background taskbar notification tray icon."""
        try:
            import pystray
            from PIL import Image
            
            icon_path = os.path.join(os.path.dirname(__file__), "app_icon.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = Image.new('RGB', (64, 64), color=(30, 30, 46))
            
            menu = pystray.Menu(
                pystray.MenuItem('Show Dashboard', lambda icon, item: self.show_from_tray(), default=True),
                pystray.MenuItem('Exit', lambda icon, item: self.exit_from_tray())
            )
            
            self.tray_icon = pystray.Icon("file_monitor", image, "File Monitor Alert", menu)
            
            import threading
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Error setting up tray icon: {e}")

    def show_from_tray(self):
        """Restore window from tray."""
        self.root.after(0, self.root.deiconify)
        if self.tray_icon:
            self.tray_icon.visible = False

    def exit_from_tray(self):
        """Terminate app from tray menu."""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.exit_app)

    def exit_app(self):
        """Proper cleanup and process termination."""
        if self.engine.running:
            self.engine.stop()
        if self.email_timer_id:
            self.root.after_cancel(self.email_timer_id)
        if self.pulse_timer:
            self.root.after_cancel(self.pulse_timer)
        self.root.destroy()

    # ---------- Data ----------
    def _load_history(self):
        """Populate the table with past events from the database."""
        rows = event_store.get_recent_events(limit=200)
        for timestamp, event_type, file_path, email_sent in rows:
            status_str = "Sent" if email_sent == 1 else "Failed" if email_sent == 0 else "Pending"
            tag = "modified" if event_type == "renamed" else event_type
            self.tree.insert(
                "", "end", values=(timestamp, event_type, file_path, status_str), tags=(tag,)
            )
        self.count_var.set(f"{len(rows)} events recorded")
        self.event_count_card_var.set(str(len(rows)))

    def _clear_history_click(self):
        """Clear sqlite history records and update table."""
        if messagebox.askyesno("Clear History", "Are you sure you want to permanently delete all event history?"):
            event_store.clear_history()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.count_var.set("0 events recorded")
            self.event_count_card_var.set("0")

    def _export_history_click(self):
        """Export all events recorded in SQLite to a CSV file."""
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Event Logs"
        )
        if not filename:
            return
            
        try:
            # Query all logs from SQLite
            rows = event_store.get_recent_events(limit=100000) # Fetch up to 100k events
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header row
                writer.writerow(["Timestamp", "Event Type", "File Path", "Email Sent Status"])
                for timestamp, event_type, file_path, email_sent in rows:
                    status_str = "Sent" if email_sent == 1 else "Failed" if email_sent == 0 else "Pending"
                    writer.writerow([timestamp, event_type, file_path, status_str])
            messagebox.showinfo("Export Successful", f"Logs successfully exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while saving the file:\n{e}")

    # ---------- Monitoring control ----------
    def _toggle_monitoring(self):
        if not self.engine.running:
            # Check watch_folders list
            watch_folders = self.config.get("watch_folders", [])
            if not watch_folders and self.config.get("watch_folder"):
                watch_folders = [self.config.get("watch_folder")]
            if not watch_folders:
                messagebox.showerror("No folder set", "Please select a folder to watch in Settings first.")
                return
            self.engine.start()
            self.status_var.set("Monitoring...")
            self.status_label.config(fg="#a6e3a1")
            self.start_stop_btn.config(text="Stop Monitoring", bg="#f38ba8", activebackground="#ff9eb8")
        else:
            self.engine.stop()
            self.status_var.set("Stopped")
            self.status_label.config(fg="#f38ba8")
            self.start_stop_btn.config(text="Start Monitoring", bg="#a6e3a1", activebackground="#bbf7b6")
        self._update_start_stop_btn_hover()

    def _poll_events(self):
        """Runs on the main thread every POLL_INTERVAL_MS; drains any new events."""
        while True:
            item = self.engine.get_event(block=False)
            if item is None:
                break
            event_type, val = item

            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if event_type == "moved":
                src_path, dest_path = val
                updated = False
                # Look for a pending creation of the src_path to rename it in-place
                for evt in self.pending_email_events:
                    if evt["file_path"] == src_path:
                        evt["file_path"] = dest_path
                        event_store.update_event_path(evt["db_row_id"], dest_path)
                        if self.tree.exists(evt["tree_item_id"]):
                            self.tree.set(evt["tree_item_id"], "path", dest_path)
                        updated = True
                
                # If we couldn't match a pending creation, log it as a separate renamed event
                if not updated:
                    db_row_id = event_store.add_event("renamed", f"{src_path} -> {dest_path}", email_sent=2)
                    item_id = self.tree.insert(
                        "", 0, values=(ts, "renamed", f"{src_path} -> {dest_path}", "Pending"), tags=("modified",)
                    )
                    
                    current = int(self.event_count_card_var.get())
                    self.event_count_card_var.set(str(current + 1))
                    self.count_var.set(f"{current + 1} events recorded")

                    self.pending_email_events.append({
                        "tree_item_id": item_id,
                        "db_row_id": db_row_id,
                        "event_type": "renamed",
                        "file_path": f"{src_path} -> {dest_path}",
                        "timestamp": ts
                    })
                    
                    if self.email_timer_id is not None:
                        self.root.after_cancel(self.email_timer_id)
                    self.email_timer_id = self.root.after(5000, self._send_batched_emails)
            else:
                file_path = val
                db_row_id = event_store.add_event(event_type, file_path, email_sent=2)
                item_id = self.tree.insert(
                    "", 0, values=(ts, event_type, file_path, "Pending"), tags=(event_type,)
                )

                current = int(self.event_count_card_var.get())
                self.event_count_card_var.set(str(current + 1))
                self.count_var.set(f"{current + 1} events recorded")

                self.pending_email_events.append({
                    "tree_item_id": item_id,
                    "db_row_id": db_row_id,
                    "event_type": event_type,
                    "file_path": file_path,
                    "timestamp": ts
                })

                if self.email_timer_id is not None:
                    self.root.after_cancel(self.email_timer_id)
                self.email_timer_id = self.root.after(5000, self._send_batched_emails)

        self.root.after(POLL_INTERVAL_MS, self._poll_events)

    def _send_batched_emails(self):
        """Prepares the consolidated batch of events to send on a background thread."""
        self.email_timer_id = None
        events_to_send = self.pending_email_events.copy()
        self.pending_email_events.clear()

        if not events_to_send:
            return

        import threading
        threading.Thread(target=self._run_batch_email_thread, args=(events_to_send,), daemon=True).start()

    def _run_batch_email_thread(self, events):
        """Sends the grouped events email summary in background."""
        count = len(events)
        subject = f"File Monitor Alert: {count} Event{'s' if count > 1 else ''} Detected"

        body_lines = ["The following file system changes were detected:\n"]
        for evt in events:
            body_lines.append(f"[{evt['timestamp']}] {evt['event_type'].upper()} - {evt['file_path']}")
        body = "\n".join(body_lines)

        from monitor_engine import send_email_alert
        success = send_email_alert(self.config, subject, body)

        status_val = 1 if success else 0
        status_str = "Sent" if success else "Failed"

        # Update event statuses in SQLite
        db_ids = [evt["db_row_id"] for evt in events]
        event_store.update_email_status(db_ids, status_val)

        # Safely update table in GUI thread
        def _update_ui():
            for evt in events:
                try:
                    if self.tree.exists(evt["tree_item_id"]):
                        self.tree.set(evt["tree_item_id"], "email_status", status_str)
                except Exception as err:
                     print(f"Error updating UI: {err}")

        self.root.after(0, _update_ui)

    # ---------- Settings ----------
    def _open_settings(self):
        # Import here to avoid circular import at module load time
        from settings_gui import SettingsWindow

        was_running = self.engine.running
        if was_running:
            self.engine.stop()

        top = tk.Toplevel(self.root)

        def on_settings_saved(new_config):
            self.config = new_config
            self._update_folder_card_display()
            
            smtp_details = f"{self.config.get('smtp_server', 'smtp.gmail.com')}:{self.config.get('smtp_port', 587)}"
            self.smtp_card_var.set(smtp_details)

            self.engine = MonitorEngine(self.config)  # rebuild engine with fresh config
            self.status_var.set("Stopped")
            self.status_label.config(fg="#f38ba8")
            self.start_stop_btn.config(text="Start Monitoring", bg="#a6e3a1", activebackground="#bbf7b6")
            self._update_start_stop_btn_hover()
            top.destroy()

        SettingsWindow(top, on_save_callback=on_settings_saved, close_on_save=True)
        top.grab_set()  # modal-ish: focus stays on settings until closed


if __name__ == "__main__":
    root = tk.Tk()
    app = Dashboard(root)
    root.mainloop()
