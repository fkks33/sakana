import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

from utils.line_api import send_line_message
from utils.history import load_state, save_state, update_history
from utils.date_utils import filter_target_dates, get_jst_now
from utils.scraper import fetch_seat_statuses

FIXED_RESERVATION_URL = "https://www.jr-odekake.net/railroad/westexginga/reservation/#route-sanin"

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    config = load_config()
    kyoto_to_izumo = filter_target_dates(config.get("sanin", {}).get("kyoto_to_izumo", []))
    izumo_to_kyoto = filter_target_dates(config.get("sanin", {}).get("izumo_to_kyoto", []))

    seat_configs = {
        "クシェット": {"param": "%B7%B2%DD%B8%BC000", "data_id": "3010000"},
        "ファーストシート": {"param": "%B7%B2%DD%CC%B1000", "data_id": "1010000"},
        "プレミアルーム1": {"param": "%B7%B2%DD%CC1000", "data_id": "11100C1"},
        "プレミアルーム2": {"param": "%B7%B2%DD%CC2000", "data_id": "11100D1"}
    }

    search_conditions = []
    for d_str in kyoto_to_izumo:
        search_conditions.append({
            "name": "京都→出雲市",
            "depart": "%8B%9E%93s",
            "arrive": "%8Fo%89_%8Es",
            "date": d_str,
            "hour": "21",
            "minute": "00"
        })

    for d_str in izumo_to_kyoto:
        search_conditions.append({
            "name": "出雲市→京都",
            "depart": "%8Fo%89_%8Es",
            "arrive": "%8B%9E%93s",
            "date": d_str,
            "hour": "09",
            "minute": "00"
        })

    now = get_jst_now()
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[now.weekday()]
    start_time = now.strftime(f"%Y-%m-%d({weekday_str}) %H:%M:%S")

    result_messages = [
        "[WEST EXPRESS 銀河 空席通知]",
        f"{start_time}時点"
    ]

    has_available_seat = False
    results_list = []
    
    # 状態管理（kinanを参考にsaninにも適用）
    state = load_state()
    new_state = {}

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
            block_lines = [f"■ {condition['name']} ({condition['date']})"]
            printed_seats_count = 0

            for seat_name, seat_info in seat_configs.items():
                train_kana_param = seat_info["param"]
                data_search_id = seat_info["data_id"]

                url = base_url.format(
                    depart=condition["depart"],
                    arrive=condition["arrive"],
                    date=condition["date"],
                    hour=condition["hour"],
                    minute=condition["minute"],
                    param=train_kana_param
                )

                statuses = fetch_seat_statuses(page, url, [data_search_id])
                seat_status = statuses.get(data_search_id, "情報なし")

                time.sleep(1)

                results_list.append({
                    "date": condition["date"],
                    "direction": "kudari" if condition["name"] == "京都→出雲市" else "nobori",
                    "seat": seat_name,
                    "status": seat_status
                })

                # saninでの重複通知抑止ロジック
                state_key = f"sanin_{condition['date']}_{condition['name']}_{seat_name}"
                should_notify_seat = False
                
                if seat_status in ["〇", "△"]:
                    prev_consecutive = state.get(state_key, {}).get("consecutive_count", 0)
                    if prev_consecutive >= 4:
                        consecutive_count = 1
                        should_notify_seat = True
                    elif prev_consecutive >= 1:
                        consecutive_count = prev_consecutive + 1
                        should_notify_seat = False
                    else:
                        consecutive_count = 1
                        should_notify_seat = True
                        
                    new_state[state_key] = {
                        "status": seat_status,
                        "consecutive_count": consecutive_count
                    }
                else:
                    if seat_status not in ["×", "残席なし", "座席なし"]:
                        should_notify_seat = True

                if seat_status not in ["×", "残席なし", "座席なし"]:
                    has_available_seat = True
                
                if should_notify_seat and seat_status not in ["×", "残席なし", "座席なし"]:
                    block_lines.append(f"{seat_name}: {seat_status}")
                    printed_seats_count += 1

            if printed_seats_count == 0:
                block_lines.append("　　≪　新　規　の　空　席　な　し　≫")
            
            # If all seats were 'no new empty seats', we might skip appending the whole block if desired.
            # But let's keep it to show we checked.
            result_messages.append("\n".join(block_lines))

        browser.close()

    # saninのstateも共有ファイルに保存（上書きしないようにマージ）
    merged_state = {**state, **new_state}
    save_state(merged_state)
    
    update_history("sanin", results_list)

    final_message = "\n\n".join(result_messages)

    if has_available_seat:
        final_message += f"\n\n予約ページ:\n{FIXED_RESERVATION_URL}"

    print(final_message)

    # 通知対象があれば送る
    if has_available_seat and any("〇" in msg or "△" in msg for msg in result_messages):
        send_line_message(final_message, method="broadcast")
    else:
        print("新規通知対象の空席なし: 通知スキップ")

if __name__ == "__main__":
    main()
