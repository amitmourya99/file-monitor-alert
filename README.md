# File & Folder Activity Monitor with Email Alerts

A modern, high-performance folder surveillance desktop utility for Windows. Tracks folder events (created, deleted, modified, renamed) across multiple directories and sends consolidated email alert summaries on a batch timer.

---

## 🛠️ Installation & Setup (प्रोग्राम को कैसे सेटअप करें)

Follow these simple steps to install and start using the application:

### Step 1: Install Python (यदि कंप्यूटर में Python नहीं है)
Ensure Python 3.x is installed on your Windows machine:
1. Download Python from the [official website](https://www.python.org/downloads/).
2. **IMPORTANT**: During installation, check the box that says **"Add Python to PATH"** before clicking Install.

### Step 2: Install Dependencies (ज़रूरी फाइल्स इनस्टॉल करें)
1. Open Command Prompt (`cmd`) or PowerShell in this project folder.
2. Run the following command to install the required libraries:
   ```cmd
   pip install -r files/requirements.txt
   ```
   *This automatically installs `watchdog` (monitoring engine), `pillow` (icon loader), and `pystray` (system tray helper).*

---

## 🚀 How to Run (प्रोग्राम ko kaise chalayein)

### Option A: Silent Mode (बिना CMD Window के - Recommended)
* **Double-click the `run.vbs`** file at the root of the folder.
* *This launches the application completely silently in the background with zero terminal screens flashing on your monitor.*

### Option B: Standard Mode
* Double-click `run.bat` to launch the application.

---

## ⚙️ Configuration & Features (फीचर्स और उनका उपयोग)

1. **First-Time Setup (पहली बार सेटअप)**:
   - On the very first launch, the Setup screen opens.
   - Fill in your **Sender Email** and **Google App Password**.
   - Enter **SMTP settings** (preconfigured for Gmail: `smtp.gmail.com` on port `587`).
   - Add directories to watch under **Folders to Monitor** using the **Add Folder** button.
   - Configure **Excluded Folders/Files** (supports wildcards like `*.tmp` or `~$*` to avoid lock file alerts).
   - Click **Send Test Email** to verify your setup, then click **Save Settings** to launch the Dashboard.

2. **Dashboard Overview (डैशबोर्ड)**:
   - **Start/Stop Monitoring**: Toggles folder watching.
   - **SaaS Stats Cards**: Displays real-time watch folder paths, SMTP details, and total event logs.
   - **Export Logs**: Exports all sqlite event logs as an Excel-compatible `.csv` sheet.
   - **Edit Settings**: Change emails, passwords, exclusions, or file types at any time.

3. **Background Tray (टास्कबार बैकग्राउंड सर्विस)**:
   - If **"Run in background when closed"** is checked in Settings: clicking the window close button (`X`) will withdraw the window to the bottom-right taskbar System Tray.
   - Right-click the shield tray icon and select **Show Dashboard** to restore the window, or **Exit** to shut down.

4. **System Startup (कंप्यूटर ऑन होते ही चालू होना)**:
   - Check **"Start monitoring on system startup"** in Settings.
   - The program will automatically run silently in the background whenever Windows boots up!
