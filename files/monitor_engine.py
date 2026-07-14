"""
monitor_engine.py
Core file-watching engine (uses the `watchdog` library) + email alert sending.

Runs the watcher in a background thread so the GUI never freezes.
Detected events are pushed into a thread-safe queue; the GUI polls this
queue on the main thread (via root.after) to update itself safely.
"""
import os
import smtplib
import threading
import queue
from email.mime.text import MIMEText

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import event_store

SMTP_TIMEOUT = 10  # seconds


def test_smtp_connection(sender_email: str, app_password: str, smtp_server: str, smtp_port: int):
    """
    Try to actually log in to Gmail's or custom SMTP server with the given credentials.
    Returns (True, None) on success, (False, error_message) on failure.
    """
    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=SMTP_TIMEOUT) as smtp:
                smtp.login(sender_email, app_password)
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=SMTP_TIMEOUT) as smtp:
                smtp.starttls()
                smtp.login(sender_email, app_password)
        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Authentication failed. Please verify your email and app password. "
            "Also check if 2-Step Verification is enabled on the sender account."
        )
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except OSError as e:
        return False, f"Network/connection error: {e}"


def send_email_alert(config: dict, subject: str, body: str):
    """Send a single email using the sender credentials in config. Returns True/False."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config["sender_email"]
    msg["To"] = config["receiver_email"]
    
    server = config.get("smtp_server", "smtp.gmail.com")
    port = int(config.get("smtp_port", 587))
    
    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port, timeout=SMTP_TIMEOUT) as smtp:
                smtp.login(config["sender_email"], config["sender_app_password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(server, port, timeout=SMTP_TIMEOUT) as smtp:
                smtp.starttls()
                smtp.login(config["sender_email"], config["sender_app_password"])
                smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"[!] Failed to send email: {e}")
        return False


class _Handler(FileSystemEventHandler):
    """Translates raw watchdog filesystem events into our filtered event queue."""

    def __init__(self, config: dict, event_queue: queue.Queue):
        super().__init__()
        self.config = config
        self.event_queue = event_queue
        self.allowed_exts = set(e.lower() for e in config.get("file_extensions", []))
        self.excluded_paths = [p.strip().lower() for p in config.get("excluded_paths", []) if p.strip()]

    def _matches_filter(self, path: str) -> bool:
        import fnmatch
        path_lower = path.lower()
        file_name = os.path.basename(path).lower()
        
        for pattern in self.excluded_paths:
            pattern_lower = pattern.lower()
            if '*' in pattern_lower or '?' in pattern_lower:
                # Wildcard pattern matches file name OR full path substring
                if fnmatch.fnmatch(file_name, pattern_lower) or fnmatch.fnmatch(path_lower, f"*{pattern_lower}*"):
                    return False
            else:
                # Regular folder substring matching
                if pattern_lower in path_lower:
                    return False
                    
        ext = os.path.splitext(path)[1].lower()
        return ext in self.allowed_exts

    def on_created(self, event):
        if event.is_directory:
            return
        if self.config.get("watch_created") and self._matches_filter(event.src_path):
            self.event_queue.put(("created", event.src_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self.config.get("watch_deleted") and self._matches_filter(event.src_path):
            self.event_queue.put(("deleted", event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        if self.config.get("watch_modified") and self._matches_filter(event.src_path):
            self.event_queue.put(("modified", event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        if self._matches_filter(event.src_path) or self._matches_filter(event.dest_path):
            self.event_queue.put(("moved", (event.src_path, event.dest_path)))


class MonitorEngine:
    """
    Wraps a watchdog Observer. Start/stop it, and drain new events via get_event().
    Email sending happens in its own short-lived thread per event, so a slow
    network call never blocks file-event detection.
    """

    def __init__(self, config: dict):
        self.config = config
        self.event_queue = queue.Queue()
        self._observer = None
        self.running = False

    def start(self):
        if self.running:
            return
        handler = _Handler(self.config, self.event_queue)
        self._observer = Observer()
        
        watch_folders = self.config.get("watch_folders", [])
        if not watch_folders and self.config.get("watch_folder"):
            watch_folders = [self.config.get("watch_folder")]
            
        scheduled_any = False
        for folder in watch_folders:
            if folder and os.path.exists(folder):
                self._observer.schedule(handler, folder, recursive=True)
                scheduled_any = True
                
        if not scheduled_any:
            return
            
        self._observer.start()
        self.running = True

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        self.running = False

    def get_event(self, block=False, timeout=None):
        """Pop one (event_type, path) from the queue, or None if empty."""
        try:
            return self.event_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def handle_event_and_notify(self, event_type: str, file_path: str):
        """
        Called by the GUI after pulling an event off the queue:
        - saves it to permanent history (SQLite)
        - fires off an email alert in a background thread
        """
        subject = f"File Monitor Alert: {event_type.upper()}"
        body = f"Event: {event_type}\nFile: {file_path}"

        def _send_and_record():
            sent = send_email_alert(self.config, subject, body)
            event_store.add_event(event_type, file_path, email_sent=sent)

        threading.Thread(target=_send_and_record, daemon=True).start()
