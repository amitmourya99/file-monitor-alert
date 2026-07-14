"""
main.py
Entry point for the File Monitor application.

- If no valid settings exist yet -> show Setup screen first.
- Once setup is saved (and email verified) -> Dashboard opens automatically.
- If settings already exist from a previous run -> go straight to Dashboard.

Run this file to start the app:  python main.py
"""
import tkinter as tk

from config_manager import load_config
from settings_gui import SettingsWindow
from dashboard import Dashboard


def _launch_dashboard():
    """Open a fresh Tk root running the Dashboard."""
    root = tk.Tk()
    Dashboard(root)
    root.mainloop()


def main():
    # Tell Windows to treat this as a unique app on the taskbar to display custom icon
    try:
        import ctypes
        myappid = 'antigravity.filemonitor.detector.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    config = load_config()
    has_valid_setup = bool(config.get("sender_email") and config.get("watch_folder"))

    if has_valid_setup:
        _launch_dashboard()
    else:
        root = tk.Tk()

        def on_setup_done(_config):
            # Hide the setup window immediately, then open the Dashboard.
            # (We use withdraw + destroy-after instead of destroying root
            # right away, since we're still inside root's own callback here.)
            root.withdraw()
            _launch_dashboard()
            root.destroy()

        SettingsWindow(root, on_save_callback=on_setup_done, close_on_save=True)
        root.mainloop()


if __name__ == "__main__":
    main()
