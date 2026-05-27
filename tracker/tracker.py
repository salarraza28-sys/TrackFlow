import time
import json
import os
import platform
import subprocess
import threading
import math  # Added for mouse distance calculation
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Import pynput safely. Ensure you run: pip install pynput
from pynput import mouse, keyboard

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")



# ── Activity Metrics Hooks (Item 1 Implementation) ───────────────────────────

_keystroke_count = 0
_mouse_click_count = 0
_mouse_distance_pixels = 0.0
_last_mouse_pos = None
metrics_lock = threading.Lock()

def _on_press(key):
    global _keystroke_count
    with metrics_lock:
        _keystroke_count += 1

def _on_click(x, y, button, pressed):
    global _mouse_click_count
    if pressed:
        with metrics_lock:
            _mouse_click_count += 1

def _on_move(x, y):
    global _mouse_distance_pixels, _last_mouse_pos
    with metrics_lock:
        if _last_mouse_pos is not None:
            dx = x - _last_mouse_pos[0]
            dy = y - _last_mouse_pos[1]
            _mouse_distance_pixels += math.sqrt(dx**2 + dy**2)
        _last_mouse_pos = (x, y)

def get_and_reset_metrics() -> dict:
    """Collects gathered input metrics and resets counters for the next window track cycle."""
    global _keystroke_count, _mouse_click_count, _mouse_distance_pixels
    with metrics_lock:
        metrics = {
            "keystrokes": _keystroke_count,
            "mouse_clicks": _mouse_click_count,
            "mouse_distance_px": int(_mouse_distance_pixels)
        }
        _keystroke_count = 0
        _mouse_click_count = 0
        _mouse_distance_pixels = 0.0
    return metrics

def _evdev_listen(dev):
    global _keystroke_count, _mouse_click_count, _mouse_distance_pixels
    import evdev
    import time
    
    caps = dev.capabilities()
    has_keys = evdev.ecodes.EV_KEY in caps
    key_codes = caps.get(evdev.ecodes.EV_KEY, [])
    
    is_keyboard_device = has_keys and (evdev.ecodes.KEY_A in key_codes)
    has_btn_touch = has_keys and (evdev.ecodes.BTN_TOUCH in key_codes)
    
    has_abs_x = (evdev.ecodes.EV_ABS in caps) and (evdev.ecodes.ABS_X in caps[evdev.ecodes.EV_ABS])
    has_abs_y = (evdev.ecodes.EV_ABS in caps) and (evdev.ecodes.ABS_Y in caps[evdev.ecodes.EV_ABS])
    
    # Scale factors for absolute coordinates (touchpad/touchscreen)
    scale_x = 1.0
    scale_y = 1.0
    if has_abs_x:
        abs_info_x = dev.absinfo(evdev.ecodes.ABS_X)
        range_x = abs_info_x.max - abs_info_x.min
        if range_x > 0:
            scale_x = 1920.0 / range_x
    if has_abs_y:
        abs_info_y = dev.absinfo(evdev.ecodes.ABS_Y)
        range_y = abs_info_y.max - abs_info_y.min
        if range_y > 0:
            scale_y = 1080.0 / range_y

    last_abs_x = None
    last_abs_y = None
    
    # Tracking touch state for absolute devices to avoid jumps and detect tap-to-clicks
    is_touching = not has_btn_touch
    touch_start_time = None
    touch_start_x = None
    touch_start_y = None

    try:
        for event in dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                # Track mouse buttons
                if event.code in [evdev.ecodes.BTN_LEFT, evdev.ecodes.BTN_RIGHT, evdev.ecodes.BTN_MIDDLE]:
                    if event.value == 1: # Key down
                        with metrics_lock:
                            _mouse_click_count += 1
                
                # Track touchpad touch/tap heuristic
                elif event.code == evdev.ecodes.BTN_TOUCH:
                    if event.value == 1:
                        is_touching = True
                        touch_start_time = time.time()
                        touch_start_x = last_abs_x
                        touch_start_y = last_abs_y
                    elif event.value == 0:
                        is_touching = False
                        
                        # Tap-to-click heuristic: short duration, minimal movement
                        if touch_start_time is not None:
                            duration = time.time() - touch_start_time
                            curr_x = last_abs_x if last_abs_x is not None else touch_start_x
                            curr_y = last_abs_y if last_abs_y is not None else touch_start_y
                            
                            dist_x = abs(curr_x - touch_start_x) if (curr_x is not None and touch_start_x is not None) else 0
                            dist_y = abs(curr_y - touch_start_y) if (curr_y is not None and touch_start_y is not None) else 0
                            
                            # Convert dist to scaled pixels
                            scaled_dist_x = dist_x * scale_x
                            scaled_dist_y = dist_y * scale_y
                            
                            # Tap threshold: < 250ms and moved less than 15 scaled pixels
                            if duration < 0.25 and scaled_dist_x < 15 and scaled_dist_y < 15:
                                with metrics_lock:
                                    _mouse_click_count += 1
                                    
                        last_abs_x = None
                        last_abs_y = None
                        touch_start_time = None
                        touch_start_x = None
                        touch_start_y = None
                
                # Other keys (keyboard)
                elif is_keyboard_device:
                    if event.code < 0x100 and event.value == 1: # Key down
                        with metrics_lock:
                            _keystroke_count += 1
                            
            elif event.type == evdev.ecodes.EV_REL:
                # Relative motion (standard mouse)
                if event.code == evdev.ecodes.REL_X:
                    with metrics_lock:
                        _mouse_distance_pixels += abs(event.value)
                elif event.code == evdev.ecodes.REL_Y:
                    with metrics_lock:
                        _mouse_distance_pixels += abs(event.value)
                        
            elif event.type == evdev.ecodes.EV_ABS:
                # Absolute motion (touchpad/touchscreen)
                if is_touching:
                    if event.code == evdev.ecodes.ABS_X:
                        # Set initial coordinates when first event arrives
                        if touch_start_x is None:
                            touch_start_x = event.value
                        if last_abs_x is not None:
                            dx = event.value - last_abs_x
                            with metrics_lock:
                                _mouse_distance_pixels += abs(dx) * scale_x
                        last_abs_x = event.value
                    elif event.code == evdev.ecodes.ABS_Y:
                        # Set initial coordinates when first event arrives
                        if touch_start_y is None:
                            touch_start_y = event.value
                        if last_abs_y is not None:
                            dy = event.value - last_abs_y
                            with metrics_lock:
                                _mouse_distance_pixels += abs(dy) * scale_y
                        last_abs_y = event.value
    except Exception:
        pass

def start_input_listeners():
    sys_name = platform.system()
    if sys_name == "Linux":
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            started_any = False
            for dev in devices:
                caps = dev.capabilities()
                is_keyboard = evdev.ecodes.EV_KEY in caps and evdev.ecodes.KEY_A in caps[evdev.ecodes.EV_KEY]
                is_mouse = evdev.ecodes.EV_REL in caps or evdev.ecodes.EV_ABS in caps
                
                if is_keyboard or is_mouse:
                    t = threading.Thread(target=_evdev_listen, args=(dev,), daemon=True)
                    t.start()
                    started_any = True
            
            if not started_any:
                print("No evdev input devices found or accessible. Falling back to pynput...")
                _start_pynput()
            else:
                print("Linux evdev tracking successfully initialized!")
        except Exception as e:
            print(f"Evdev setup failed: {e}. Falling back to pynput...")
            _start_pynput()
    else:
        _start_pynput()

def _start_pynput():
    try:
        from pynput import mouse, keyboard
        mouse_listener = mouse.Listener(on_move=_on_move, on_click=_on_click)
        keyboard_listener = keyboard.Listener(on_press=_on_press)
        mouse_listener.start()
        keyboard_listener.start()
        print(f"{platform.system()} pynput tracking successfully initialized!")
    except Exception as e:
        print("Failed to start pynput listeners:", e)

# Start listeners on spin up
start_input_listeners()


# ── Date helpers ──────────────────────────────────────────────────────────────

def today_str():
    return datetime.now().strftime("%d-%m-%Y")

def human_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%y")

def get_log_file(dt: datetime = None) -> str:
    if dt is None:
        dt = datetime.now()
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
                
        return app_name, window_title
    except Exception:
        pass

    return app_name, window_title


# ── Log I/O ───────────────────────────────────────────────────────────────────

def _load_file_data(log_file: str) -> dict:
    """Load raw file data, handling both old array format and new object format."""
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                # Migrate old array format
                return {"paused": False, "pause_count": 0, "logs": data}
        except Exception:
            pass
    return {"paused": False, "pause_count": 0, "logs": []}

def load_logs(log_file: str = None) -> list:
    if log_file is None:
        log_file = get_log_file()
    return _load_file_data(log_file).get("logs", [])

def load_all_logs() -> list:
    all_logs = []
    if not os.path.exists(LOGS_DIR):
        return all_logs
    for fname in sorted(os.listdir(LOGS_DIR)):
        if fname.endswith(".json") and fname not in ["paused.json", "pause_status.json"]:
            fpath = os.path.join(LOGS_DIR, fname)
            all_logs.extend(_load_file_data(fpath).get("logs", []))
    return all_logs

def save_logs(logs: list, log_file: str = None):
    if log_file is None:
        log_file = get_log_file()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Preserve existing pause metadata
    existing = _load_file_data(log_file)

    ordered_logs = []
    for log in logs:
        ordered_log = {
            "date":             log.get("date"),
            "application":      log.get("application"),
            "window":           log.get("window"),
            "description":      log.get("description"),
            "start_time":       log.get("start_time"),
            "end_time":         log.get("end_time"),
            "duration_minutes": log.get("duration_minutes"),
            "smart_narration":  log.get("smart_narration", False),
            "summary":          log.get("summary"),
            "metrics":          log.get("metrics", {"keystrokes": 0, "mouse_clicks": 0, "mouse_distance_px": 0})
        }
        for k, v in log.items():
            if k not in ordered_log:
                ordered_log[k] = v
        ordered_logs.append(ordered_log)

    file_data = {
        "paused": existing.get("paused", False),
        "pause_count": existing.get("pause_count", 0),
        "logs": ordered_logs
    }

    with open(log_file, "w") as f:
        json.dump(file_data, f, indent=2)


def _build_entry(app, window, start: datetime, end: datetime, metrics: dict) -> dict:
    """Build a log entry containing the active window tracking duration and raw peripheral telemetry."""
    duration = (end - start).total_seconds() / 60.0
    return {
        "date":             human_date(start),
        "application":      app,
        "window":           window,
        "description":      None,
        "start_time":       start.isoformat(),
        "end_time":         end.isoformat(),
        "duration_minutes": round(duration, 2),
        "smart_narration":  False,
        "summary":          None,
        "metrics":          metrics  # Appended input telemetry directly into schema
    }


# ── Pause helpers ─────────────────────────────────────────────────────────────

def get_pause_data(dt: datetime = None) -> dict:
    log_file = get_log_file(dt)
    data = _load_file_data(log_file)
    return {
        "paused": data.get("paused", False),
        "pause_count": data.get("pause_count", 0),
        "date": dt.strftime("%d-%m-%Y") if dt else today_str()
    }

def is_paused() -> bool:
    return get_pause_data().get("paused", False)

def set_paused(paused: bool) -> dict:
    log_file = get_log_file()
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    data = _load_file_data(log_file)

    if paused and not data.get("paused", False):
        data["pause_count"] = data.get("pause_count", 0) + 1

    data["paused"] = paused

    with open(log_file, "w") as f:
        json.dump(data, f, indent=2)

    return {
        "paused": paused,
        "pause_count": data.get("pause_count", 0),
        "date": today_str()
    }


# ── Tracker loop ──────────────────────────────────────────────────────────────

def track_activity():
    print("Starting background activity tracker…")
    current_app, current_window = None, None
    start_time = None

    while True:
        try:
            if is_paused():
                now = datetime.now()
                if current_app != "System" or current_window != "Paused":
                    if current_app is not None:
                        duration = (now - start_time).total_seconds() / 60.0
                        activity_metrics = get_and_reset_metrics()
                        if current_app != "Unknown" and duration >= 0.05:
                            log_file = get_log_file(start_time)
                            logs = load_logs(log_file)
                            logs.append(_build_entry(current_app, current_window, start_time, now, activity_metrics))
                            save_logs(logs, log_file)
                            print(f"[{human_date(start_time)}] Logged: {current_app} – {current_window} ({round(duration,2)}m) | Inputs: {activity_metrics}")
                    else:
                        get_and_reset_metrics()
                        
                    current_app = "System"
                    current_window = "Paused"
                    start_time = now
                else:
                    # Keep clearing out peripheral metrics while paused so they don't leak into the next cycle
                    get_and_reset_metrics()
                
                time.sleep(2)
                continue

            app, window = get_active_window_title_and_app()
            
            if not app:
                app = "Unknown"

            if app != current_app or window != current_window:
                now = datetime.now()
                if current_app is not None:
                    duration = (now - start_time).total_seconds() / 60.0
                    activity_metrics = get_and_reset_metrics()
                    if current_app != "Unknown" and duration >= 0.05:
                        log_file = get_log_file(start_time)
                        logs = load_logs(log_file)
                        logs.append(_build_entry(current_app, current_window, start_time, now, activity_metrics))
                        save_logs(logs, log_file)
                        print(f"[{human_date(start_time)}] Logged: {current_app} – {current_window} ({round(duration,2)}m) | Inputs: {activity_metrics}")
                else:
                    get_and_reset_metrics()

                current_app = app
                current_window = window
                start_time = now

        except Exception as e:
            print(f"Tracking error: {e}")

        time.sleep(2)


# ── HTTP API ──────────────────────────────────────────────────────────────────

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
            dates = []
            if os.path.exists(LOGS_DIR):
                dates = sorted(
                    f.replace(".json", "")
                    for f in os.listdir(LOGS_DIR)
                    if f.endswith(".json")
                )
            dates = [d.replace("-", "/") for d in dates]
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(dates).encode())

        elif parsed.path.startswith("/api/status"):
            date_param = params.get("date", [None])[0]
            dt = None
            if date_param:
                try:
                    normalized = date_param.replace("/", "-")
                    dt = datetime.strptime(normalized, "%d-%m-%Y")
                except Exception:
                    pass
            
            pause_data = get_pause_data(dt)
            live_status = get_pause_data()
            
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "paused": live_status.get("paused", False),
                "pause_count": pause_data.get("pause_count", 0)
            }).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/api/pause":
            data = json.loads(post_data.decode("utf-8"))
            paused = data.get("paused", False)
            new_data = set_paused(paused)
            self._json_response({"success": True, "paused": paused, "pause_count": new_data.get("pause_count", 0)})

        elif parsed_path.path == "/api/update_logs":
            data = json.loads(post_data.decode("utf-8"))
            logs = data.get("logs", [])
            params = urllib.parse.parse_qs(parsed_path.query)
            date_param = params.get("date", [None])[0]
            normalized = date_param.replace("/", "-") if date_param else None
            log_file = os.path.join(LOGS_DIR, f"{normalized}.json") if normalized else get_log_file()
            save_logs(logs, log_file)
            self._json_response({"success": True})

        elif parsed_path.path == "/api/clear":
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
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(server_address, RequestHandler)
    print("Local API server running on port 5173…")
    httpd.serve_forever()


if __name__ == "__main__":
    tracker_thread = threading.Thread(target=track_activity, daemon=True)
    tracker_thread.start()
    run_server()