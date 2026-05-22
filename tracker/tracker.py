import time
import json
import os
import platform
import subprocess
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PAUSE_FILE = os.path.abspath(os.path.join(BASE_DIR, "pause_status.json"))


# ── Date helpers ──────────────────────────────────────────────────────────────

def today_str():
    """Returns today's date as DD-MM-YYYY  (used as filename / primary key)."""
    return datetime.now().strftime("%d-%m-%Y")

def human_date(dt: datetime) -> str:
    """Returns DD/MM/YY — the format shown to teachers / non-technical users."""
    return dt.strftime("%d/%m/%y")

def get_log_file(dt: datetime = None) -> str:
    """
    Returns the full path to the daily log file for a given datetime.
    File is named DD-MM-YYYY.json so it sorts and reads naturally.
    """
    if dt is None:
        dt = datetime.now()
    # Store files as DD-MM-YYYY.json but expose dates as DD/MM/YY
    return os.path.join(LOGS_DIR, dt.strftime("%d-%m-%Y") + ".json")


# ── Window detection ──────────────────────────────────────────────────────────

def get_active_window_title_and_app():
    system = platform.system()
    window_title = "Unknown"
    app_name = "Unknown"

    try:
        if system == "Windows":
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                window_title = window.title
                app_name = "Windows App"
        elif system == "Linux":
            try:
                import shutil
                if shutil.which("hyprctl"):
                    try:
                        hypr_out = subprocess.check_output(
                            ["hyprctl", "activewindow", "-j"],
                            stderr=subprocess.DEVNULL
                        ).decode("utf-8")
                        data = json.loads(hypr_out)
                        app_name = data.get("class", "Unknown App")
                        window_title = data.get("title", "Unknown Window")
                        return app_name, window_title
                    except Exception:
                        pass

                import re
                root_out = subprocess.check_output(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8")
                window_id_match = re.search(r'window id # (0x[0-9a-fA-F]+)', root_out)
                if window_id_match:
                    window_id = window_id_match.group(1)
                    if window_id != "0x0":
                        name_out = subprocess.check_output(
                            ["xprop", "-id", window_id, "_NET_WM_NAME"],
                            stderr=subprocess.DEVNULL
                        ).decode("utf-8")
                        name_match = re.search(r'=\s+"(.*)"$', name_out, re.MULTILINE)
                        if name_match:
                            window_title = name_match.group(1)

                        pid_out = subprocess.check_output(
                            ["xprop", "-id", window_id, "_NET_WM_PID"],
                            stderr=subprocess.DEVNULL
                        ).decode("utf-8")
                        pid_match = re.search(r'=\s+([0-9]+)', pid_out)
                        if pid_match:
                            pid = pid_match.group(1)
                            with open(f"/proc/{pid}/comm", "r") as f:
                                app_name = f.read().strip()
            except Exception:
                pass
        elif system == "Darwin":
            try:
                # Use AppleScript via osascript to safely query System Events
                script = '''
                tell application "System Events"
                    try
                        set frontApp to first application process whose frontmost is true
                        set appName to name of frontApp
                        try
                            set winName to name of window 1 of frontApp
                        on error
                            set winName to "Unknown Window"
                        end try
                        return appName & "|||" & winName
                    on error
                        return "Unknown App|||Unknown Window"
                    end try
                end tell
                '''
                mac_out = subprocess.check_output(
                    ["osascript", "-e", script],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8").strip()
                
                if "|||" in mac_out:
                    app_name, window_title = mac_out.split("|||", 1)
                    return app_name, window_title
            except Exception:
                pass
                
        # Global fallback if all specific OS checks fail or throw errors
        return "Unknown App", "Unknown Window"
    except Exception:
        pass

    return app_name, window_title


# ── Log I/O ───────────────────────────────────────────────────────────────────

def load_logs(log_file: str = None) -> list:
    """Load logs from a daily file. Defaults to today's file."""
    if log_file is None:
        log_file = get_log_file()
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def load_all_logs() -> list:
    """Aggregate every daily log file into one list (for the /api/logs endpoint)."""
    all_logs = []
    if not os.path.exists(LOGS_DIR):
        return all_logs
    for fname in sorted(os.listdir(LOGS_DIR)):
        if fname.endswith(".json"):
            fpath = os.path.join(LOGS_DIR, fname)
            try:
                with open(fpath, "r") as f:
                    all_logs.extend(json.load(f))
            except Exception:
                pass
    return all_logs

def save_logs(logs: list, log_file: str = None):
    """Save logs to a daily file. Defaults to today's file."""
    if log_file is None:
        log_file = get_log_file()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    ordered_logs = []
    for log in logs:
        ordered_log = {
            "date":             log.get("date"),           # DD/MM/YY  — primary display key
            "application":      log.get("application"),
            "window":           log.get("window"),
            "description":      log.get("description"),
            "start_time":       log.get("start_time"),
            "end_time":         log.get("end_time"),
            "duration_minutes": log.get("duration_minutes"),
            "smart_narration":  log.get("smart_narration", False),
            "summary":          log.get("summary"),
        }
        # carry any extra keys the caller may have added
        for k, v in log.items():
            if k not in ordered_log:
                ordered_log[k] = v
        ordered_logs.append(ordered_log)

    with open(log_file, "w") as f:
        json.dump(ordered_logs, f, indent=2)


def _build_entry(app, window, start: datetime, end: datetime) -> dict:
    """Build a single log entry dict with the human-readable date field."""
    duration = (end - start).total_seconds() / 60.0
    return {
        "date":             human_date(start),          # e.g. "21/05/26"
        "application":      app,
        "window":           window,
        "description":      None,
        "start_time":       start.isoformat(),
        "end_time":         end.isoformat(),
        "duration_minutes": round(duration, 2),
        "smart_narration":  False,
        "summary":          None,
    }

# ── Pause helpers ─────────────────────────────────────────────────────────────

def get_pause_data() -> dict:
    """Reads the pause file and returns both the state and the counter."""
    if os.path.exists(PAUSE_FILE):
        try:
            with open(PAUSE_FILE, "r") as f:
                data = json.load(f)
                # Ensure defaults exist if reading an old version of the file
                return {
                    "paused": data.get("paused", False),
                    "pause_count": data.get("pause_count", 0)
                }
        except Exception:
            pass
    return {"paused": False, "pause_count": 0}

def is_paused() -> bool:
    return get_pause_data().get("paused", False)

def set_paused(paused: bool) -> dict:
    """Updates pause state, increments counter if paused, and returns new data."""
    os.makedirs(os.path.dirname(PAUSE_FILE), exist_ok=True)
    
    current_data = get_pause_data()
    
    # Only increment the counter if transitioning from False (running) to True (paused)
    if paused and not current_data["paused"]:
        current_data["pause_count"] += 1
        
    current_data["paused"] = paused

    with open(PAUSE_FILE, "w") as f:
        json.dump(current_data, f, indent=2)
        
    return current_data

# # ── Pause helpers ─────────────────────────────────────────────────────────────

# def is_paused() -> bool:
#     if os.path.exists(PAUSE_FILE):
#         try:
#             with open(PAUSE_FILE, "r") as f:
#                 return json.load(f).get("paused", False)
#         except Exception:
#             return False
#     return False

# def set_paused(paused: bool):
#     os.makedirs(os.path.dirname(PAUSE_FILE), exist_ok=True)
#     with open(PAUSE_FILE, "w") as f:
#         json.dump({"paused": paused}, f)


# ── Tracker loop ──────────────────────────────────────────────────────────────

def track_activity():
    print("Starting background activity tracker…")
    current_app, current_window = None, None
    start_time = None

    while True:
        try:
            if is_paused():
                if current_app is not None:
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds() / 60.0
                    if duration >= 0.05:
                        log_file = get_log_file(start_time)
                        logs = load_logs(log_file)
                        logs.append(_build_entry(current_app, current_window, start_time, end_time))
                        save_logs(logs, log_file)
                    current_app = None
                time.sleep(2)
                continue

            app, window = get_active_window_title_and_app()

            if not app or app == "Unknown":
                time.sleep(2)
                continue

            if app != current_app or window != current_window:
                now = datetime.now()
                if current_app is not None:
                    duration = (now - start_time).total_seconds() / 60.0
                    if duration >= 0.05:
                        # Use start_time to pick the correct daily file (handles midnight crossover)
                        log_file = get_log_file(start_time)
                        logs = load_logs(log_file)
                        logs.append(_build_entry(current_app, current_window, start_time, now))
                        save_logs(logs, log_file)
                        print(f"[{human_date(start_time)}] Logged: {current_app} – {current_window} ({round(duration,2)}m)")

                current_app = app
                current_window = window
                start_time = now

        except Exception as e:
            print(f"Tracking error: {e}")

        time.sleep(2)


# ── HTTP API ──────────────────────────────────────────────────────────────────

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress noisy access log

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path.startswith("/api/logs"):
            # Optional ?date=DD/MM/YY to fetch a single day
            date_param = params.get("date", [None])[0]
            if date_param:
                normalized = date_param.replace("/", "-")
                log_file = os.path.join(LOGS_DIR, f"{normalized}.json")
                logs = load_logs(log_file)
            else:
                logs = load_all_logs()

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(logs).encode())

        elif parsed.path.startswith("/api/dates"):
            # Returns list of available log dates  e.g. ["21-05-2026", "22-05-2026"]
            dates = []
            if os.path.exists(LOGS_DIR):
                dates = sorted(
                    f.replace(".json", "")
                    for f in os.listdir(LOGS_DIR)
                    if f.endswith(".json")
                )
            # Convert dash filenames to slash format for UI
            dates = [d.replace("-", "/") for d in dates]
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(dates).encode())

        elif parsed.path.startswith("/api/status"):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"paused": is_paused()}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/api/pause":
            data = json.loads(post_data.decode("utf-8"))
            paused = data.get("paused", False)
            set_paused(paused)
            self._json_response({"success": True, "paused": paused})

        elif self.path == "/api/update_logs":
            data = json.loads(post_data.decode("utf-8"))
            logs = data.get("logs", [])
            # Optional ?date=DD-MM-YYYY in the URL
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            # Extract date param and normalize
            date_param = params.get("date", [None])[0]
            normalized = date_param.replace("/", "-") if date_param else None
            log_file = os.path.join(LOGS_DIR, f"{normalized}.json") if normalized else get_log_file()
            save_logs(logs, log_file)
            self._json_response({"success": True})

        elif self.path == "/api/clear":
            # Clears TODAY's log only (never touches historical files)
            save_logs([], get_log_file())
            self._json_response({"success": True, "logs": []})

        else:
            self.send_response(404)
            self.end_headers()

    def _json_response(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server():
    server_address = ("", 5173)
    httpd = HTTPServer(server_address, RequestHandler)
    print("Local API server running on port 5173…")
    httpd.serve_forever()


if __name__ == "__main__":
    tracker_thread = threading.Thread(target=track_activity, daemon=True)
    tracker_thread.start()
    run_server()