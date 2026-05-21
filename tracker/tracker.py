import time
import json
import os
import platform
import subprocess
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "activity_logs.json"))
PAUSE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "pause_status.json"))

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
                        hypr_out = subprocess.check_output(["hyprctl", "activewindow", "-j"], stderr=subprocess.DEVNULL).decode("utf-8")
                        data = json.loads(hypr_out)
                        app_name = data.get("class", "Unknown App")
                        window_title = data.get("title", "Unknown Window")
                        return app_name, window_title
                    except Exception:
                        pass
                
                import re
                root_out = subprocess.check_output(["xprop", "-root", "_NET_ACTIVE_WINDOW"], stderr=subprocess.DEVNULL).decode("utf-8")
                window_id_match = re.search(r'window id # (0x[0-9a-fA-F]+)', root_out)
                if window_id_match:
                    window_id = window_id_match.group(1)
                    if window_id != "0x0":
                        name_out = subprocess.check_output(["xprop", "-id", window_id, "_NET_WM_NAME"], stderr=subprocess.DEVNULL).decode("utf-8")
                        name_match = re.search(r'=\s+"(.*)"$', name_out, re.MULTILINE)
                        if name_match:
                            window_title = name_match.group(1)
                        
                        pid_out = subprocess.check_output(["xprop", "-id", window_id, "_NET_WM_PID"], stderr=subprocess.DEVNULL).decode("utf-8")
                        pid_match = re.search(r'=\s+([0-9]+)', pid_out)
                        if pid_match:
                            pid = pid_match.group(1)
                            with open(f"/proc/{pid}/comm", "r") as f:
                                app_name = f.read().strip()
            except Exception:
                pass
        elif system == "Darwin":
            pass
    except Exception as e:
        pass

    return app_name, window_title

def load_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_logs(logs):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    ordered_logs = []
    for log in logs:
        ordered_log = {
            "application": log.get("application"),
            "window": log.get("window"),
            "description": log.get("description"),
            "start_time": log.get("start_time"),
            "end_time": log.get("end_time"),
            "duration_minutes": log.get("duration_minutes")
        }
        # Append remaining keys (e.g., smart_narration, summary)
        for k, v in log.items():
            if k not in ordered_log and k not in ["commentary", "ai_generated_text"]:
                ordered_log[k] = v
        ordered_logs.append(ordered_log)
        
    with open(LOG_FILE, "w") as f:
        json.dump(ordered_logs, f, indent=2)

# def generate_mock_data():
#     now = datetime.now()
#     mock_logs = [
#         {
#             "application": "Visual Studio Code",
#             "window": "tracker.py - activity-tracker",
#             "start_time": (now - timedelta(hours=5)).isoformat(),
#             "end_time": (now - timedelta(hours=4, minutes=15)).isoformat(),
#             "duration_minutes": 45.0
#         },
#         {
#             "application": "Google Chrome",
#             "window": "Live Cricket: India vs England 2nd Test - Match Streaming - Disney+ Hotstar",
#             "start_time": (now - timedelta(hours=4, minutes=10)).isoformat(),
#             "end_time": (now - timedelta(hours=2, minutes=40)).isoformat(),
#             "duration_minutes": 90.0
#         },
#         {
#             "application": "Terminal",
#             "window": "git commit -m \"feat: active window tracking hook\"",
#             "start_time": (now - timedelta(hours=2, minutes=35)).isoformat(),
#             "end_time": (now - timedelta(hours=2, minutes=15)).isoformat(),
#             "duration_minutes": 20.0
#         },
#         {
#             "application": "Google Chrome",
#             "window": "T20 Cricket Match Highlights & Analysis - YouTube",
#             "start_time": (now - timedelta(hours=2, minutes=10)).isoformat(),
#             "end_time": (now - timedelta(hours=1, minutes=40)).isoformat(),
#             "duration_minutes": 30.0
#         },
#         {
#             "application": "Visual Studio Code",
#             "window": "App.jsx - activity-tracker",
#             "start_time": (now - timedelta(hours=1, minutes=35)).isoformat(),
#             "end_time": (now - timedelta(minutes=15)).isoformat(),
#             "duration_minutes": 80.0
#         }
#     ]
#     save_logs(mock_logs)
#     return mock_logs

def is_paused():
    if os.path.exists(PAUSE_FILE):
        try:
            with open(PAUSE_FILE, "r") as f:
                data = json.load(f)
                return data.get("paused", False)
        except Exception:
            return False
    return False

def set_paused(paused):
    os.makedirs(os.path.dirname(PAUSE_FILE), exist_ok=True)
    with open(PAUSE_FILE, "w") as f:
        json.dump({"paused": paused}, f)

def track_activity():
    print(f"Starting background activity tracker...")
    logs = load_logs()
    
    current_app, current_window = None, None
    start_time = None
    
    while True:
        try:
            paused = is_paused()
            if paused:
                if current_app is not None:
                    # Finalize current log before pausing
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds() / 60.0
                    if duration >= 0.05:
                        logs = load_logs() # Reload from disk to prevent memory overwrite
                        logs.append({
                            "application": current_app,
                            "window": current_window,
                            "start_time": start_time.isoformat(),
                            "end_time": end_time.isoformat(),
                            "duration_minutes": round(duration, 2),
                            "smart_narration": False,
                            "summary": None,
                            "description": None
                        })
                        save_logs(logs)
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
                    if duration >= 0.05: # At least 3 seconds
                        logs = load_logs() # Reload from disk to prevent memory overwrite
                        logs.append({
    "application": current_app,
    "window": current_window,
    "start_time": start_time.isoformat(),
    "end_time": now.isoformat(),
    "duration_minutes": round(duration, 2),
    "smart_narration": False,
    "summary": None,
    "description": None
})
                        save_logs(logs)
                        print(f"Logged: {current_app} - {current_window} ({round(duration, 2)}m)")
                
                current_app = app
                current_window = window
                start_time = now
            
        except Exception as e:
            print(f"Tracking error: {e}")
            
        time.sleep(2)


class RequestHandler(BaseHTTPRequestHandler):
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
        if self.path.startswith('/api/logs'):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            logs = load_logs()
            self.wfile.write(json.dumps(logs).encode())
        elif self.path.startswith('/api/status'):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {"paused": is_paused()}
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/pause':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            paused = data.get("paused", False)
            set_paused(paused)
            
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "paused": paused}).encode())
        elif self.path == '/api/update_logs':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            logs = data.get("logs", [])
            save_logs(logs)
            
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        elif self.path == '/api/clear':
            save_logs([])
            self.send_response(200)
            self._send_cors_headers()
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "logs": []}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('',5173)
    httpd = HTTPServer(server_address, RequestHandler)
    print("Starting local API server on port 5173...")
    httpd.serve_forever()

if __name__ == "__main__":
    # Start tracker thread
    tracker_thread = threading.Thread(target=track_activity, daemon=True)
    tracker_thread.start()
    
    # Run API server
    run_server()
