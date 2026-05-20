# TrackFlow - Automated Desktop Activity Tracking Utility

TrackFlow is a proactive automated desktop tracking utility designed to minimize manual logging. It continuously monitors active desktop applications and generates structured activity reports. It comes with a lightweight Python background tracker and a modern React dashboard for visualization.

## Architecture
- **Background Tracker (Python):** Monitors active windows, handles idle/pause states, and auto-generates `activity_logs.json`. It also runs a lightweight local API server to communicate with the frontend.
- **Frontend Dashboard (React/Vite):** A dynamic UI styled with Tailwind CSS v4 and Recharts. It fetches local logs from the Python API and visualizes focus time, app distribution, and timeline history.
- **Local Storage:** All logs are kept in `activity_logs.json` for ultimate privacy.

## Features Built
1. **Automated Window Tracking:** Auto-detects application changes and computes precise duration.
2. **Watch/Pause Privacy Mode:** Instant toggling from the UI. When paused, no data is recorded.
3. **Rich Visual Analytics:** 
   - Focus Time summaries.
   - App distribution pie charts.
   - Activity timeline bar charts.
4. **Log Review Workflow:** A streamlined "Review Logs" tab allowing users to verify daily auto-generated entries.
5. **Cross-Platform & Wayland/Hyprland Support:** Built-in active window tracker supports Windows (via `pygetwindow`), classic Linux X11 displays (via `xprop`), and modern Wayland compositors (specifically tiling window managers like **Hyprland** via native `hyprctl` queries).
6. **On-Demand Tester Mode:** Includes a gorgeous "Generate Realistic Demo Logs" CTA in the UI to instantly simulate a productive day (loaded with coding activity, streaming live cricket on Hotstar, and YouTube highlights) for immediate verification.

---

## Setup & Running the PoC

### 1. Start the Background Tracker (Backend)
The Python background tracker runs the window logging loop and hosts the local API server on port `5001`.

**Prerequisites:**
- Python 3+
- For standard Linux X11 systems, `xprop` (usually pre-installed) is required.
- For Linux Wayland systems running Hyprland, `hyprctl` (pre-installed in Hyprland) is natively used. No third-party tools like `xdotool` are needed!

```bash
cd tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python tracker.py
```

### 2. Start the UI Dashboard (Frontend)
The frontend uses Vite, React, and Tailwind CSS v4.

```bash
cd frontend
npm install
npm run dev
```

Visit **[http://localhost:5173](http://localhost:5173)** to view the dashboard!

---

### Special Testing Feature: Headless / VM Mode
If you are running this PoC on a headless virtual machine, WSL terminal, or a remote workspace where no graphical display is in focus, the dashboard will display a helper card saying **"No Active Window Logs Yet."** 

Simply click the **"Generate Realistic Demo Logs"** button. This will trigger the backend to generate a realistic user activity day:
*   **Disney+ Hotstar:** Streamed *India vs England Live Cricket Match* (90 mins).
*   **YouTube:** Watched *Cricket Highlights & Analysis* (30 mins).
*   **VS Code:** Coded the `tracker.py` active window hook (80 mins).
*   **Terminal:** Executed `git commit` and package builds (20 mins).

This lets you fully test the focus calculations, timeline bar charts, application pie charts, and the logs review and approval screen!

---

*This Proof of Concept successfully demonstrates that an automated tracker can eliminate manual entry burdens while ensuring complete local privacy and delivering rich visualization.*
