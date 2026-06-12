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

def update_history(course_name, results_list):
    os.makedirs("docs", exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            print(f"履歴ファイルのロードエラー: {e}")
            
    JST = timezone(timedelta(hours=9))
    now_iso = datetime.now(JST).isoformat()
    
    history.append({
        "timestamp": now_iso,
        "course": course_name,
        "results": results_list
    })
    
    # 過去30日以内のデータのみ保持する
    thirty_days_ago = datetime.now(JST) - timedelta(days=30)
    filtered_history = []
    for run in history:
        try:
            run_time = datetime.fromisoformat(run["timestamp"])
            if run_time >= thirty_days_ago:
                filtered_history.append(run)
        except Exception:
            filtered_history.append(run)
            
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered_history, f, ensure_ascii=False, indent=2)
        print(f"履歴データの更新({course_name}): 成功")
    except Exception as e:
        print(f"履歴データの保存エラー: {e}")

def append_access_log(course, log_entry):
    os.makedirs("docs", exist_ok=True)
    log_file = f"docs/log_{course}.json"
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            print(f"アクセスログの読み込みエラー: {e}")
            
    logs.append(log_entry)
    
    # Keep only the last 1000 records to prevent infinite growth
    if len(logs) > 1000:
        logs = logs[-1000:]
        
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"アクセスログの保存エラー: {e}")
