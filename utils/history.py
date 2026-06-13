import os
import json
from datetime import datetime, timedelta, timezone

STATE_FILE = "last_state.json"
HISTORY_FILE = "docs/history.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"状態ファイルの読み込みエラー: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"状態ファイルの保存エラー: {e}")

def append_access_logs(course, log_entries_list):
    os.makedirs("docs", exist_ok=True)
    log_file = f"docs/log_{course}.json"
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            print(f"アクセスログの読み込みエラー: {e}")
            
    logs.extend(log_entries_list)
    
    # Keep logs for the last 30 days instead of a fixed count
    JST = timezone(timedelta(hours=9))
    thirty_days_ago = datetime.now(JST) - timedelta(days=30)
    
    filtered_logs = []
    for log in logs:
        try:
            # Parse the ISO timestamp
            log_time = datetime.fromisoformat(log["timestamp"])
            if log_time >= thirty_days_ago:
                filtered_logs.append(log)
        except Exception:
            # Keep if parsing fails to avoid data loss
            filtered_logs.append(log)
        
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(filtered_logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"アクセスログの保存エラー: {e}")
