import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

def log_tracker_activity(activity_data):
    """
    Saves tracker data to a file named after the current date (DD-MM-YYYY.json).
    Generates a new file automatically when a new day starts.
    """
    # Ensure the logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Get today's date to use as the file name
    date_str = datetime.now().strftime("%d-%m-%Y")
    file_path = os.path.join(LOGS_DIR, f"{date_str}.json")

    existing_logs = []
    
    # If a log file for today already exists, load the existing data
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                existing_logs = json.load(f)
        except json.JSONDecodeError:
            # Fallback just in case the file exists but is empty or corrupted
            existing_logs = []
            
    # Append the new activity data
    existing_logs.append(activity_data)
    
    # Write the updated logs back to today's file
    with open(file_path, "w") as f:
        json.dump(existing_logs, f, indent=2)
        
    print(f"Logged activity to {file_path}")

# --- Example Usage ---
# if __name__ == "__main__":
    # Simulate the tracker starting and generating some data
    # new_log_entry = {
    #     "start_time": datetime.now().isoformat(),
    #     "task_name": "Working on Python Script",
    #     "status": "started"
    # }
    
    # # Call the function whenever you need to save
    # log_tracker_activity(new_log_entry)