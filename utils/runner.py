import time
from playwright.sync_api import sync_playwright

from utils.line_api import send_line_message
from utils.history import load_state, save_state, append_access_logs
from utils.date_utils import get_jst_now
from utils.scraper import fetch_seat_statuses
from datetime import datetime

def run_availability_check(course_name, display_name, target_dates_str, search_conditions, line_method="broadcast"):
    """
    course_name: "kinan", "sanin", "sunrise"
    display_name: "WEST EXPRESS 銀河 紀南コース", "サンライズ出雲・瀬戸" など
    target_dates_str: 検索対象の日付文字列
    search_conditions: 検索する対象のリスト (depart, arrive, date, hour, minute, seat_configs/groups等を含む)
    """
    now = get_jst_now()
    fetch_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    fetch_time_iso = now.isoformat()
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    state = load_state()
    new_state = {}
    logs_list = []
    
    available_seats_lines = []
    has_available_seat = False

    base_url = (
        "https://e5489.jr-odekake.net/e5489/cspc/CBDayTimeArriveSelRsvMyDiaPC?"
        "inputDepartStName={depart}&inputArriveStName={arrive}&inputType=0&"
        "inputDate={date}&inputHour={hour}&inputMinute={minute}&"
        "inputUniqueDepartSt=1&inputUniqueArriveSt=1&inputSearchType=2&"
        "inputTransferDepartStName1={depart}&inputTransferArriveStName1={arrive}&"
        "inputTransferDepartStUnique1=1&inputTransferArriveStUnique1=1&"
        "inputTransferTrainType1=0001&inputSpecificTrainType1=2&"
        "inputSpecificBriefTrainKana1={param}&SequenceType=0"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for condition in search_conditions:
            date_obj = datetime.strptime(condition["date"], "%Y%m%d")
            date_formatted = date_obj.strftime(f"%m/%d({weekdays[date_obj.weekday()]})")
            
            depart_name = condition.get("depart_name", condition["depart"])
            arrive_name = condition.get("arrive_name", condition["arrive"])
            
            block_header = f"■{date_formatted} {depart_name}→{arrive_name}"
            block_seats = []

            # param ごとにグループ化してアクセスを減らす (無駄な処理の削減)
            param_groups = {}
            for seat_name, seat_info in condition["seat_configs"].items():
                param = seat_info["param"]
                if param not in param_groups:
                    param_groups[param] = []
                param_groups[param].append({
                    "seat_name": seat_name,
                    "data_id": seat_info["data_id"]
                })

            for train_kana_param, seats_in_param in param_groups.items():
                url = base_url.format(
                    depart=condition["depart"],
                    arrive=condition["arrive"],
                    date=condition["date"],
                    hour=condition["hour"],
                    minute=condition["minute"],
                    param=train_kana_param
                )

                # 対象URLに対する必要な data_id を一括で指定
                data_search_ids = [s["data_id"] for s in seats_in_param]
                statuses = fetch_seat_statuses(page, url, data_search_ids)

                time.sleep(1)

                for seat_info in seats_in_param:
                    seat_name = seat_info["seat_name"]
                    data_search_id = seat_info["data_id"]
                    seat_status = statuses.get(data_search_id, "情報なし")

                    # Logging each access
                    log_entry = {
                        "timestamp": fetch_time_iso,
                        "train": condition.get("name", display_name),
                        "depart": depart_name,
                        "arrive": arrive_name,
                        "target_date": condition["date"],
                        "direction": condition.get("direction", "unknown"),
                        "seat_type": seat_name,
                        "result": seat_status
                    }
                    logs_list.append(log_entry)

                    # Notification logic (last_state)
                    state_key = f"{course_name}_{condition['date']}_{condition.get('name', 'train')}_{seat_name}"
                    should_notify = False

                    if seat_status in ["〇", "△", "○"]:
                        prev_consecutive = state.get(state_key, {}).get("consecutive_count", 0)
                        if prev_consecutive >= 4:
                            consecutive_count = 1
                            should_notify = True
                            print(f"[{condition['date']} {condition.get('name', '')} {seat_name}] 空席継続(4回目)。通知します。")
                        elif prev_consecutive >= 1:
                            consecutive_count = prev_consecutive + 1
                            print(f"[{condition['date']} {condition.get('name', '')} {seat_name}] 空席継続({consecutive_count}回目)。通知スキップ。")
                        else:
                            consecutive_count = 1
                            should_notify = True
                            print(f"[{condition['date']} {condition.get('name', '')} {seat_name}] 新規空席検知。")
                            
                        new_state[state_key] = {
                            "status": seat_status,
                            "consecutive_count": consecutive_count
                        }
                    else:
                        if seat_status not in ["×", "残席なし", "座席なし"]:
                            print(f"[{condition['date']} {condition.get('name', '')} {seat_name}] ステータス: {seat_status}")

                    if should_notify:
                        block_seats.append(f"　{seat_name}：{seat_status}")
                        has_available_seat = True

            if len(block_seats) > 0:
                available_seats_lines.append(block_header)
                available_seats_lines.extend(block_seats)

        browser.close()

    # Merge state
    merged_state = {**state, **new_state}
    save_state(merged_state)
    
    # Append bulk logs
    append_access_logs(course_name, logs_list)

    if has_available_seat:
        msg_lines = [
            "【空席照会結果】",
            f"列車名：{display_name}",
            f"取得日時：{fetch_time_str}",
            f"検索対象：{target_dates_str}",
            ""
        ]
        msg_lines.extend(available_seats_lines)
        msg_lines.append("")
        msg_lines.append("https://fkks33.github.io/sakana/")
        
        final_message = "\n".join(msg_lines)
        print(final_message)
        send_line_message(final_message, method=line_method)
    else:
        print("通知対象の空席なし: 通知スキップ")
