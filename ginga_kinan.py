import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

from utils.line_api import send_line_message
from utils.history import load_state, save_state, update_history
from utils.date_utils import filter_target_dates, get_jst_now
from utils.scraper import fetch_seat_statuses

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    config = load_config()
    kyoto_to_shingu = filter_target_dates(config.get("kinan", {}).get("kyoto_to_shingu", []))
    shingu_to_kyoto = filter_target_dates(config.get("kinan", {}).get("shingu_to_kyoto", []))

    seat_configs_kudari = {
        "クシェット": {"param": "%B7%C5%B8%BC%D4000", "data_id": "3010000"},
        "ファーストシート": {"param": "%B7%C5%CC%B1%D4000", "data_id": "1010000"},
        "プレミアルーム1": {"param": "%B7%C5%CC1%D4000", "data_id": "11100C1"},
        "プレミアルーム2": {"param": "%B7%C5%CC2%D4000", "data_id": "11100D1"}
    }

    seat_configs_nobori = {
        "クシェット": {"param": "%B7%C5%B8%BC%CB000", "data_id": "3010000"},
        "ファーストシート": {"param": "%B7%C5%CC%B1%CB000", "data_id": "1010000"},
        "プレミアルーム1": {"param": "%B7%C5%CC1%CB000", "data_id": "11100C1"},
        "プレミアルーム2": {"param": "%B7%C5%CC2%CB000", "data_id": "11100E1"}
    }

    search_conditions = []
    kudari_dates_list = []
    nobori_dates_list = []

    for d_str in kyoto_to_shingu:
        search_conditions.append({
            "name": "京都→新宮",
            "depart": "%8B%9E%93s",
            "arrive": "%90V%8B%7B",
            "date": d_str,
            "hour": "21",
            "minute": "00",
            "seat_configs": seat_configs_kudari
        })
        kudari_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    for d_str in shingu_to_kyoto:
        search_conditions.append({
            "name": "新宮→京都",
            "depart": "%90V%8B%7B",
            "arrive": "%8B%9E%93s",
            "date": d_str,
            "hour": "09",
            "minute": "00",
            "seat_configs": seat_configs_nobori
        })
        nobori_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    target_dates_str = f"下り: {', '.join(kudari_dates_list)} | 上り: {', '.join(nobori_dates_list)}"

    start_time = get_jst_now().strftime("%Y-%m-%d %H:%M:%S")
    state = load_state()
    new_state = {}
    results_list = []

    weekdays = ["月", "火", "水", "木", "金", "土", "日"]

    header_lines = [
        "【WEST EXPRESS銀河 空席照会結果】",
        f"取得日時：{start_time}",
        "対象コース：紀南コース",
        f"対象日時：{target_dates_str}",
        "対象席種：クシェット、ファーストシート、プレミアルーム1、プレミアルーム2"
    ]

    body_lines = []
    has_available_seat_to_notify = False

    base_url = (
        "https://e5489.jr-odekake.net/e5489/cspc/CBDayTimeArriveSelRsvMyDiaPC?"
        "inputDepartStName={depart}&inputArriveStName={arrive}&inputType=0&"
        "inputDate={date}&inputHour={hour}&inputMinute={minute}&"
        "inputUniqueDepartSt=1&inputUniqueArriveSt=1&inputSearchType=2&"
        "inputTransferDepartStName1={depart}&inputTransferArriveStName1={arrive}&"
        "inputTransferDepartStUnique1=1&inputTransferArriveStUnique1=1&"
        "inputTransferTrainType1=0001&inputSpecificTrainType1=2&"
        "inputSpecificBriefTrainKana1={param}&SequenceType=0"
        "&inputReturnUrl=railroad/westexginga/reservation/reservation-kinan-nonmember/ordinarycar/&"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for condition in search_conditions:
            date_obj = datetime.strptime(condition["date"], "%Y%m%d")
            date_formatted_c = date_obj.strftime(f"%m/%d({weekdays[date_obj.weekday()]})")
            
            block_lines = [f"\n■{date_formatted_c} {condition['name']}"]
            printed_seats_count = 0

            seat_types = condition["seat_configs"]

            for seat_name, seat_info in seat_types.items():
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
                    "direction": "kudari" if condition["name"] == "京都→新宮" else "nobori",
                    "seat": seat_name,
                    "status": seat_status
                })

                state_key = f"{condition['date']}_{condition['name']}_{seat_name}"
                
                if seat_status in ["〇", "△"]:
                    prev_consecutive = state.get(state_key, {}).get("consecutive_count", 0)
                    if prev_consecutive >= 4:
                        consecutive_count = 1
                        should_notify_seat = True
                        print(f"[{condition['date']} {condition['name']} {seat_name}] 空席継続(4回目)。通知します。")
                    elif prev_consecutive >= 1:
                        consecutive_count = prev_consecutive + 1
                        should_notify_seat = False
                        print(f"[{condition['date']} {condition['name']} {seat_name}] 空席継続(連続{consecutive_count}回目)。通知をスキップします。")
                    else:
                        consecutive_count = 1
                        should_notify_seat = True
                        print(f"[{condition['date']} {condition['name']} {seat_name}] 新規空席検知。通知します。")
                        
                    new_state[state_key] = {
                        "status": seat_status,
                        "consecutive_count": consecutive_count
                    }
                else:
                    should_notify_seat = False
                    if seat_status not in ["×", "残席なし", "座席なし"]:
                        print(f"[{condition['date']} {condition['name']} {seat_name}] ステータス: {seat_status}")

                if should_notify_seat:
                    block_lines.append(f"{seat_name}：{seat_status}\n{url}")
                    printed_seats_count += 1
                    has_available_seat_to_notify = True

            if printed_seats_count > 0:
                body_lines.append("\n".join(block_lines))

        browser.close()

    save_state(new_state)
    update_history("kinan", results_list)

    if has_available_seat_to_notify:
        final_message = "\n".join(header_lines) + "\n" + "\n".join(body_lines)
        print(final_message)
        send_line_message(final_message, method="broadcast")
    else:
        print("\n" + "\n".join(header_lines))
        print("通知対象の新規空席なし: 通知スキップ")

if __name__ == "__main__":
    main()
