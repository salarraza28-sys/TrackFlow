import json
import os
import math

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "tracker", "activity_logs.json"))

with open(LOG_FILE, "r") as f:
    logs = json.load(f)

for entry in logs:
    app = (entry.get("application") or "Unknown App").lower()
    windowTitle = (entry.get("window") or "").lower()
    duration = entry.get("duration_minutes") or 0
    
    if duration < 1:
        durationText = f"{round(duration * 60)} sec"
    elif duration < 60:
        durationText = f"{round(duration)} min"
    else:
        h = math.floor(duration / 60)
        m = round(duration % 60)
        durationText = f"{h} hr {m} min" if m > 0 else f"{h} hr"

    desc = ""
    if "code" in app or "antigravity" in app or "vscode" in windowTitle or "studio" in windowTitle:
        import re
        project = re.sub(r'( - )?(visual studio code|antigravity)', '', windowTitle, flags=re.IGNORECASE).strip()
        if not project or project == "unknown window": project = "project files"
        desc = f"Worked on {project} in {entry.get('application', app)} for {durationText}. Reviewed code logic and actively tested software state transitions. Visited files related to development and optimization."
    elif "chrome" in app or "browser" in app or "firefox" in app:
        import re
        site = re.sub(r'( - )?(google chrome|mozilla firefox)', '', windowTitle, flags=re.IGNORECASE).strip()
        if "youtube" in windowTitle or "video" in windowTitle:
            desc = f"Watched video content ({site}) for {durationText}."
        elif "docs" in windowTitle or "sheet" in windowTitle or "notion" in windowTitle:
            desc = f"Read and edited documentation ({site}) for {durationText}. Organized thoughts and structured written content."
        else:
            desc = f"Browsed the web for {durationText}. Interacted with pages related to {site}."
    elif "terminal" in app or "alacritty" in app or "konsole" in app:
        desc = f"Executed terminal commands and managed system tasks via {entry.get('application', app)} for {durationText}. Checked configurations and monitored background scripts."
    elif "nautilus" in app or "explorer" in app or "files" in app:
        desc = f"Organized local files and navigated directories using {entry.get('application', app)} for {durationText}. Managed active folders and data structures."
    else:
        desc = f"Maintained focus on \"{entry.get('window', windowTitle)}\" via {entry.get('application', app)} for {durationText}. Interacted with active application interfaces and processed current tasks."
        
    entry["description"] = desc
    entry["smart_narration"] = True
    
    # Remove unused keys
    for k in ["summary", "commentary", "ai_generated_text"]:
        if k in entry:
            del entry[k]

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
    for k, v in log.items():
        if k not in ordered_log:
            ordered_log[k] = v
    ordered_logs.append(ordered_log)

with open(LOG_FILE, "w") as f:
    json.dump(ordered_logs, f, indent=2)

print("Done populating descriptions!")
