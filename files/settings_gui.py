"""
settings_gui.py
Setup / Settings screen for the File Monitor app.

Features:
- Sender email + "Generate App Password" button (opens Google's app password page)
- Receiver email
- Folders Listbox + Add Folder / Remove Selected controls
- File extension checkboxes (customizable, compact 3-column layout)
- Preset quick select buttons
- Event type checkboxes (created / deleted / modified)
- General options: Run in Background on close, Start with Windows Boot
- Save button -> writes to config_manager and triggers startup registry config
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import os

from config_manager import load_config, save_config

# Common file types users may want to monitor.
AVAILABLE_EXTENSIONS = {
    # Documents
    ".txt": "Plain Text (.txt)",
    ".pdf": "PDF Document (.pdf)",
    ".rtf": "Rich Text (.rtf)",
    # MS Word
    ".docx": "Word Doc (.docx)",
    ".doc": "Word 97-03 (.doc)",
    ".docm": "Word Macro (.docm)",
    # MS Excel
    ".xlsx": "Excel Sheet (.xlsx)",
    ".xls": "Excel 97-03 (.xls)",
    ".xlsm": "Excel Macro (.xlsm)",
    ".xlsb": "Excel Binary (.xlsb)",
    ".csv": "CSV Sheet (.csv)",
    # MS PowerPoint
    ".pptx": "PowerPoint (.pptx)",
    ".ppt": "PowerPoint 97-03 (.ppt)",
    ".pptm": "PowerPoint Macro (.pptm)",
    # MS Access & OneNote & Outlook
    ".accdb": "Access DB (.accdb)",
    ".mdb": "Access 97-03 (.mdb)",
    ".one": "OneNote (.one)",
    ".msg": "Outlook Msg (.msg)",
    # Images
    ".jpg": "JPEG Image (.jpg)",
    ".png": "PNG Image (.png)",
    ".gif": "GIF Image (.gif)",
    # Scripts & Executables
    ".exe": "Executable (.exe)",
    ".msi": "Installer (.msi)",
    ".bat": "Batch Script (.bat)",
    ".cmd": "CMD Script (.cmd)",
    ".ps1": "PowerShell (.ps1)",
    ".vbs": "VBScript (.vbs)",
    ".py": "Python Script (.py)",
    # Archives
    ".zip": "Zip Archive (.zip)",
    ".rar": "RAR Archive (.rar)",
    ".7z": "7-Zip Archive (.7z)",
}

APP_PASSWORD_URL = "https://myaccount.google.com/apppasswords"


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


def set_startup(enabled: bool):
    """Enable or disable silent boot launching in HKCU Registry Run key."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    value_name = "FileFolderMonitor"
    
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vbs_path = os.path.abspath(os.path.join(project_root, "run.vbs"))
        
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        if enabled:
            # Command: wscript.exe "C:\path\to\run.vbs"
            cmd_value = f'wscript.exe "{vbs_path}"'
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, cmd_value)
        else:
            try:
                winreg.DeleteValue(key, value_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error setting registry startup: {e}")


class SettingsWindow:
    def __init__(self, root, on_save_callback=None, close_on_save=False):
        self.root = root
        self.on_save_callback = on_save_callback
        self.close_on_save = close_on_save
        self.config = load_config()

        self.root.title("File Monitor - Setup")
        self.root.geometry("520x680")
        self.root.minsize(440, 450)
        self.root.resizable(True, True)
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

        self.ext_vars = {}  # extension -> BooleanVar

        # --- TTK Styles ---
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Vertical.TScrollbar",
            gripcount=0,
            background="#313244",
            troughcolor="#1e1e2e",
            bordercolor="#1e1e2e",
            arrowcolor="#cdd6f4",
            lightcolor="#313244",
            darkcolor="#313244"
        )
        style.configure("TSeparator", background="#313244")

        # --- Scrollable area setup ---
        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0, bg="#1e1e2e")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#1e1e2e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Fixed footer (always visible, holds Save button)
        footer = tk.Frame(self.root, bg="#181825", height=60)
        footer.pack(side="bottom", fill="x")
        
        save_btn = tk.Button(
            footer,
            text="Save Settings",
            command=self._save,
            bg="#a6e3a1",
            fg="#11111b",
            activebackground="#bbf7b6",
            activeforeground="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            borderwidth=0,
            padx=16,
            pady=6
        )
        save_btn.pack(pady=10)
        bind_fade_hover(save_btn, "#a6e3a1", "#bbf7b6")

        self._build_ui()
        self._load_values_into_ui()

    # ---------- UI construction ----------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}
        root = self.scrollable_frame

        # Helper to style Entry fields with beautiful borders
        def create_entry(parent, var, width=35, show=None):
            entry = tk.Entry(
                parent,
                textvariable=var,
                width=width,
                show=show,
                bg="#313244",
                fg="#cdd6f4",
                insertbackground="#cdd6f4",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#45475a",
                highlightcolor="#89b4fa"
            )
            # Bind focus outlines
            entry.bind("<FocusIn>", lambda e: entry.config(highlightbackground="#89b4fa"))
            entry.bind("<FocusOut>", lambda e: entry.config(highlightbackground="#45475a"))
            return entry

        # Helper to style labels
        def create_label(parent, text, font=("Segoe UI", 9), fg="#cdd6f4"):
            return tk.Label(parent, text=text, font=font, bg="#1e1e2e", fg=fg)

        # Helper to style check buttons
        def create_check(parent, text, var):
            return tk.Checkbutton(
                parent,
                text=text,
                variable=var,
                bg="#1e1e2e",
                fg="#cdd6f4",
                selectcolor="#313244",
                activebackground="#1e1e2e",
                activeforeground="#cdd6f4",
                relief="flat"
            )

        # --- Settings Header description ---
        create_label(root, "File Monitor Configuration", font=("Segoe UI", 13, "bold"), fg="#89b4fa").pack(
            anchor="w", padx=12, pady=(15, 2)
        )
        create_label(root, "Configure SMTP credentials, folders to watch, and path exclusions below.", font=("Segoe UI", 9), fg="#a6adc8").pack(
            anchor="w", padx=12, pady=(0, 15)
        )

        # --- Sender email section ---
        create_label(root, "Sender Email Setup", font=("Segoe UI", 11, "bold"), fg="#f5c2e7").pack(
            anchor="w", **pad
        )

        frame_sender = tk.Frame(root, bg="#1e1e2e")
        frame_sender.pack(fill="x", **pad)
        
        create_label(frame_sender, "Sender Email:").grid(row=0, column=0, sticky="w", pady=4)
        self.sender_email_var = tk.StringVar()
        create_entry(frame_sender, self.sender_email_var, width=35).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )

        create_label(frame_sender, "App Password:").grid(row=1, column=0, sticky="w", pady=4)
        self.sender_password_var = tk.StringVar()
        create_entry(frame_sender, self.sender_password_var, width=35, show="*").grid(
            row=1, column=1, sticky="w", padx=8, pady=4
        )

        create_label(frame_sender, "SMTP Server:").grid(row=2, column=0, sticky="w", pady=4)
        self.smtp_server_var = tk.StringVar()
        create_entry(frame_sender, self.smtp_server_var, width=35).grid(
            row=2, column=1, sticky="w", padx=8, pady=4
        )

        create_label(frame_sender, "SMTP Port:").grid(row=3, column=0, sticky="w", pady=4)
        self.smtp_port_var = tk.StringVar()
        create_entry(frame_sender, self.smtp_port_var, width=10).grid(
            row=3, column=1, sticky="w", padx=8, pady=4
        )

        btn_gen = tk.Button(
            frame_sender,
            text="Generate Gmail App Password (opens browser)",
            command=self._open_app_password_page,
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            activeforeground="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=4
        )
        btn_gen.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 4), padx=4)
        bind_fade_hover(btn_gen, "#89b4fa", "#9cc4ff")

        btn_test = tk.Button(
            frame_sender,
            text="Send Test Email to Alert Address",
            command=self._send_test_email_click,
            bg="#f9e2af",
            fg="#11111b",
            activebackground="#f9e2af",
            activeforeground="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=4
        )
        btn_test.grid(row=5, column=0, columnspan=2, sticky="w", pady=4, padx=4)
        bind_fade_hover(btn_test, "#f9e2af", "#ffe7af")

        create_label(
            root,
            "Note: Google App Passwords require 2-Step Verification\n"
            "to be enabled on the sender Gmail account first.",
            font=("Segoe UI", 8),
            fg="#a6adc8"
        ).pack(anchor="w", padx=12, pady=4)

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # --- Receiver email ---
        frame_recv = tk.Frame(root, bg="#1e1e2e")
        frame_recv.pack(fill="x", **pad)
        create_label(frame_recv, "Alert me at (Receiver Email):").grid(row=0, column=0, sticky="w", pady=4)
        self.receiver_email_var = tk.StringVar()
        create_entry(frame_recv, self.receiver_email_var, width=35).grid(
            row=0, column=1, sticky="w", padx=8, pady=4
        )

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # --- Folders to watch ---
        create_label(root, "Folders to Monitor", font=("Segoe UI", 11, "bold"), fg="#f5c2e7").pack(
            anchor="w", **pad
        )
        frame_folder = tk.Frame(root, bg="#1e1e2e")
        frame_folder.pack(fill="x", **pad)

        # Left side: Listbox of folders
        list_container = tk.Frame(frame_folder, bg="#1e1e2e")
        list_container.pack(side="left", fill="both", expand=True)

        self.folder_listbox = tk.Listbox(
            list_container,
            height=4,
            bg="#313244",
            fg="#cdd6f4",
            selectbackground="#45475a",
            selectforeground="#cdd6f4",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=1,
            highlightbackground="#45475a"
        )
        self.folder_listbox.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(list_container, orient="vertical", command=self.folder_listbox.yview)
        scroll_y.pack(side="right", fill="y")
        self.folder_listbox.config(yscrollcommand=scroll_y.set)

        # Right side: Control buttons
        btn_container = tk.Frame(frame_folder, bg="#1e1e2e")
        btn_container.pack(side="right", fill="y", padx=(10, 0))

        btn_add = tk.Button(
            btn_container,
            text="Add Folder...",
            command=self._add_folder,
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            activeforeground="#cdd6f4",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=3
        )
        btn_add.pack(fill="x", pady=(0, 4))
        bind_fade_hover(btn_add, "#313244", "#45475a")

        btn_remove = tk.Button(
            btn_container,
            text="Remove Selected",
            command=self._remove_folder,
            bg="#313244",
            fg="#f38ba8",
            activebackground="#45475a",
            activeforeground="#f38ba8",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=3
        )
        btn_remove.pack(fill="x")
        bind_fade_hover(btn_remove, "#313244", "#45475a")

        create_label(root, "Excluded Folders (comma-separated):", font=("Segoe UI", 9), fg="#a6adc8").pack(
            anchor="w", padx=12, pady=(6, 0)
        )
        self.excluded_paths_var = tk.StringVar()
        create_entry(root, self.excluded_paths_var, width=48).pack(
            anchor="w", padx=12, pady=(4, 0)
        )

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # --- Event types ---
        create_label(root, "What to alert on", font=("Segoe UI", 11, "bold"), fg="#f5c2e7").pack(
            anchor="w", **pad
        )
        frame_events = tk.Frame(root, bg="#1e1e2e")
        frame_events.pack(fill="x", **pad)
        self.watch_created_var = tk.BooleanVar()
        self.watch_deleted_var = tk.BooleanVar()
        self.watch_modified_var = tk.BooleanVar()
        create_check(frame_events, "New file created", self.watch_created_var).pack(anchor="w", pady=2)
        create_check(frame_events, "File deleted", self.watch_deleted_var).pack(anchor="w", pady=2)
        create_check(frame_events, "File modified", self.watch_modified_var).pack(anchor="w", pady=2)

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # --- General settings ---
        create_label(root, "General Options", font=("Segoe UI", 11, "bold"), fg="#f5c2e7").pack(
            anchor="w", **pad
        )
        frame_general = tk.Frame(root, bg="#1e1e2e")
        frame_general.pack(fill="x", **pad)
        
        self.run_background_var = tk.BooleanVar()
        create_check(frame_general, "Run in background when closed", self.run_background_var).pack(anchor="w", pady=2)
        
        self.run_startup_var = tk.BooleanVar()
        create_check(frame_general, "Start monitoring on system startup", self.run_startup_var).pack(anchor="w", pady=2)

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=10)

        # --- File extensions ---
        create_label(root, "File Types to Monitor", font=("Segoe UI", 11, "bold"), fg="#f5c2e7").pack(
            anchor="w", **pad
        )

        # --- Extension Presets Buttons ---
        frame_presets = tk.Frame(root, bg="#1e1e2e")
        frame_presets.pack(fill="x", padx=12, pady=(4, 10))

        # Helper to create preset button
        def create_preset_btn(parent, text, command):
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg="#313244",
                fg="#cdd6f4",
                activebackground="#45475a",
                activeforeground="#cdd6f4",
                font=("Segoe UI", 8, "bold"),
                relief="flat",
                borderwidth=0,
                padx=8,
                pady=3
            )
            btn.pack(side="left", padx=(0, 6))
            bind_fade_hover(btn, "#313244", "#45475a")
            return btn

        # Presets callbacks
        def preset_all():
            for var in self.ext_vars.values():
                var.set(True)

        def preset_none():
            for var in self.ext_vars.values():
                var.set(False)

        def preset_office():
            office_exts = {".doc", ".docx", ".docm", ".xls", ".xlsx", ".xlsm", ".xlsb", ".ppt", ".pptx", ".pptm", ".accdb", ".mdb", ".one", ".msg"}
            for ext, var in self.ext_vars.items():
                var.set(ext in office_exts)

        def preset_scripts():
            script_exts = {".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".py"}
            for ext, var in self.ext_vars.items():
                var.set(ext in script_exts)

        def preset_defaults():
            default_exts = {".txt", ".pdf", ".docx", ".xlsx", ".csv", ".jpg", ".png", ".zip"}
            for ext, var in self.ext_vars.items():
                var.set(ext in default_exts)

        create_preset_btn(frame_presets, "Select All", preset_all)
        create_preset_btn(frame_presets, "Clear All", preset_none)
        create_preset_btn(frame_presets, "MS Office Only", preset_office)
        create_preset_btn(frame_presets, "Scripts/Execs", preset_scripts)
        create_preset_btn(frame_presets, "Defaults", preset_defaults)

        frame_ext = tk.Frame(root, bg="#1e1e2e")
        frame_ext.pack(fill="x", padx=12)

        col = 0
        row = 0
        for ext, label in AVAILABLE_EXTENSIONS.items():
            var = tk.BooleanVar()
            self.ext_vars[ext] = var
            create_check(frame_ext, label, var).grid(
                row=row, column=col, sticky="w", padx=4, pady=3
            )
            col += 1
            if col >= 3:
                col = 0
                row += 1

        # Extra bottom spacing so last checkbox isn't hidden behind footer
        tk.Frame(root, height=30, bg="#1e1e2e").pack()

    # ---------- Helpers ----------
    def _open_app_password_page(self):
        webbrowser.open(APP_PASSWORD_URL)
        messagebox.showinfo(
            "Generate App Password",
            "Google Account page has been opened in your browser.\n\n"
            "1. Sign in with your sender Gmail account.\n"
            "2. Generate a 16-character App Password.\n"
            "3. Return here and paste it into the 'App Password' field.",
        )

    def _send_test_email_click(self):
        sender_email = self.sender_email_var.get().strip()
        sender_password = self.sender_password_var.get().strip()
        receiver_email = self.receiver_email_var.get().strip()
        smtp_server = self.smtp_server_var.get().strip()
        
        if not sender_email or not sender_password or not receiver_email or not smtp_server:
            messagebox.showerror("Missing info", "Please enter Sender Email, App Password, Receiver Email, and SMTP Server configurations first.")
            return
            
        try:
            smtp_port = int(self.smtp_port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid info", "SMTP Port must be a valid number.")
            return
            
        import threading
        
        def run_test():
            self.root.config(cursor="wait")
            self.root.update()
            
            cfg = {
                "sender_email": sender_email,
                "sender_app_password": sender_password,
                "receiver_email": receiver_email,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port
            }
            
            from monitor_engine import send_email_alert
            subject = "File Monitor Verification"
            body = "Hello!\n\nThis is a verification alert sent by your File Monitor application. If you received this email, your configuration settings are fully correct."
            
            success = send_email_alert(cfg, subject, body)
            
            self.root.config(cursor="")
            if success:
                messagebox.showinfo("Email Sent", f"Test email successfully dispatched to:\n{receiver_email}\n\nPlease check your inbox/spam folder!")
            else:
                messagebox.showerror("Send Failed", "Failed to send verification email. Please confirm your SMTP credentials and network connection.")
                
        threading.Thread(target=run_test, daemon=True).start()

    def _add_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            existing = self.folder_listbox.get(0, "end")
            if folder not in existing:
                self.folder_listbox.insert("end", folder)

    def _remove_folder(self):
        try:
            selected_idx = self.folder_listbox.curselection()[0]
            self.folder_listbox.delete(selected_idx)
        except IndexError:
            messagebox.showwarning("No selection", "Please select a folder from the list to remove.")

    def _load_values_into_ui(self):
        self.sender_email_var.set(self.config.get("sender_email", ""))
        self.sender_password_var.set(self.config.get("sender_app_password", ""))
        self.receiver_email_var.set(self.config.get("receiver_email", ""))
        
        # Load watch_folders list
        self.folder_listbox.delete(0, "end")
        watch_folders = self.config.get("watch_folders", [])
        if not watch_folders and self.config.get("watch_folder"):
            watch_folders = [self.config.get("watch_folder")]
        for folder in watch_folders:
            self.folder_listbox.insert("end", folder)

        self.watch_created_var.set(self.config.get("watch_created", True))
        self.watch_deleted_var.set(self.config.get("watch_deleted", True))
        self.watch_modified_var.set(self.config.get("watch_modified", False))
        
        self.smtp_server_var.set(self.config.get("smtp_server", "smtp.gmail.com"))
        self.smtp_port_var.set(str(self.config.get("smtp_port", 587)))
        self.excluded_paths_var.set(", ".join(self.config.get("excluded_paths", [])))
        self.run_background_var.set(self.config.get("run_in_background_on_close", False))
        self.run_startup_var.set(self.config.get("run_on_startup", False))

        selected_exts = set(self.config.get("file_extensions", []))
        for ext, var in self.ext_vars.items():
            var.set(ext in selected_exts)

    def _save(self):
        if not self.sender_email_var.get().strip():
            messagebox.showerror("Missing info", "Sender email is required.")
            return
        if not self.receiver_email_var.get().strip():
            messagebox.showerror("Missing info", "Receiver email is required.")
            return
            
        # Get folders list
        watch_folders = list(self.folder_listbox.get(0, "end"))
        if not watch_folders:
            messagebox.showerror("Missing info", "Please add at least one folder to monitor.")
            return
            
        if not self.sender_password_var.get().strip():
            messagebox.showerror("Missing info", "App Password is required.")
            return

        smtp_server = self.smtp_server_var.get().strip()
        if not smtp_server:
            messagebox.showerror("Missing info", "SMTP Server is required.")
            return

        try:
            smtp_port = int(self.smtp_port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid info", "SMTP Port must be a valid number.")
            return

        selected_exts = [ext for ext, var in self.ext_vars.items() if var.get()]
        if not selected_exts:
            messagebox.showerror("Missing info", "Please select at least one file type to monitor.")
            return

        sender_email = self.sender_email_var.get().strip()
        sender_password = self.sender_password_var.get().strip()

        # --- Validate email credentials by actually logging in to SMTP server ---
        from monitor_engine import test_smtp_connection

        self.root.config(cursor="wait")
        self.root.update()
        success, error_msg = test_smtp_connection(sender_email, sender_password, smtp_server, smtp_port)
        self.root.config(cursor="")

        if not success:
            messagebox.showerror(
                "Connection Failed",
                f"Failed to connect to SMTP server:\n\n{error_msg}\n\n"
                "Please verify your sender email, app password, and SMTP configurations.",
            )
            return

        # Parse excluded paths
        excluded_raw = self.excluded_paths_var.get().split(",")
        excluded_list = [p.strip() for p in excluded_raw if p.strip()]

        new_config = {
            "sender_email": sender_email,
            "sender_app_password": sender_password,
            "receiver_email": self.receiver_email_var.get().strip(),
            "watch_folder": watch_folders[0],  # legacy backward compatibility
            "watch_folders": watch_folders,
            "file_extensions": selected_exts,
            "watch_created": self.watch_created_var.get(),
            "watch_deleted": self.watch_deleted_var.get(),
            "watch_modified": self.watch_modified_var.get(),
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "excluded_paths": excluded_list,
            "run_in_background_on_close": self.run_background_var.get(),
            "run_on_startup": self.run_startup_var.get(),
        }
        save_config(new_config)
        
        # Trigger registry boot updates
        set_startup(new_config["run_on_startup"])

        if self.close_on_save:
            # Caller (callback) decides when/how to close this window -
            # avoids nested-mainloop issues when switching to a new root window.
            if self.on_save_callback:
                self.on_save_callback(new_config)
        else:
            messagebox.showinfo("Saved", "Settings saved and connection verified successfully!")
            if self.on_save_callback:
                self.on_save_callback(new_config)


if __name__ == "__main__":
    root = tk.Tk()
    app = SettingsWindow(root)
    root.mainloop()
