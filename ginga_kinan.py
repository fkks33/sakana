import time
import requests
import os
import json
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ==========================================
# LINE Messaging API の設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

FIXED_RESERVATION_URL = "https://www.jr-odekake.net/railroad/westexginga/reservation/#route-kinan"
STATE_FILE = "last_state.json"
HISTORY_FILE = "docs/history.json"

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "messages": [{"type": "text", "text": message}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("LINE通知送信: 成功")
    except requests.exceptions.RequestException as e:
        print(f"LINE通知送信エラー: {e}")

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
        print("履歴データの更新: 成功")
    except Exception as e:
        print(f"履歴データの保存エラー: {e}")

def check_e5489_availability_dates(search_conditions, target_dates_str):
    # ==========================================
    # UTC → JST変換 と 日時のフォーマット設定
    # ==========================================
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    
    start_time = now.strftime(f"%Y-%m-%d %H:%M:%S")

    state = load_state()
    new_state = {}
    results_list = [] # 履歴保存用の結果リスト

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
            weekday_str_c = weekdays[date_obj.weekday()]
            date_formatted_c = date_obj.strftime(f"%m/%d({weekday_str_c})")
            
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

                retry_count = 0
                max_retries = 5
                seat_status = "取得タイムアウト"

                while retry_count < max_retries:
                    try:
                        page.goto(url)
                        page.wait_for_load_state("domcontentloaded")

                        content = page.content()
                        if "混雑中" in content or "20100801" in content:
                            retry_count += 1
                            time.sleep(2)
                            continue

                        selector = f"td[data-search-id='{data_search_id}'] img"
                        page.wait_for_selector(selector, timeout=5000)

                        img_elements = page.query_selector_all(selector)

                        if img_elements:
                            for img in img_elements:
                                alt_text = img.get_attribute("alt")

                                if alt_text == "空席あり":
                                    alt_text = "○"
                                elif alt_text == "空席残りわずか":
                                    alt_text = "△"
                                elif alt_text == "残席なし":
                                    alt_text = "×"

                                seat_status = alt_text
                            break
                        else:
                            seat_status = "情報なし"
                            break

                    except Exception:
                        seat_status = "取得エラー"
                        break

                time.sleep(1)

                # 履歴用レコードの追加
                results_list.append({
                    "date": condition["date"],
                    "direction": "kudari" if condition["name"] == "京都→新宮" else "nobori",
                    "seat": seat_name,
                    "status": seat_status
                })

                # 重複通知の制御ロジック
                state_key = f"{condition['date']}_{condition['name']}_{seat_name}"
                
                if seat_status in ["○", "△"]:
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
                    if seat_status != "×" and seat_status != "残席なし":
                        print(f"[{condition['date']} {condition['name']} {seat_name}] ステータス: {seat_status}")

                if should_notify_seat:
                    block_lines.append(f"{seat_name}：{seat_status}\n{url}")
                    printed_seats_count += 1
                    has_available_seat_to_notify = True

            if printed_seats_count > 0:
                body_lines.append("\n".join(block_lines))

        browser.close()

    save_state(new_state)
    update_history("kinan", results_list) # 履歴の追記

    # ==========================================
    # 最終メッセージ生成
    # ==========================================
    if has_available_seat_to_notify:
        final_message = "\n".join(header_lines) + "\n" + "\n".join(body_lines)
        print(final_message)
        send_line_message(final_message)
    else:
        print("\n" + "\n".join(header_lines))
        print("通知対象の新規空席なし: 通知スキップ")

# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    seat_configs_kudari = {
        "クシェット": {"param": "%B7%C5%B8%BC%D4000", "data_id": "3010000"}, # ｷﾅｸｼﾔ000
        "ファーストシート": {"param": "%B7%C5%CC%B1%D4000", "data_id": "1010000"}, # ｷﾅﾌｱﾔ000
        "プレミアルーム1": {"param": "%B7%C5%CC1%D4000", "data_id": "11100C1"}, # ｷﾅﾌ1ﾔ000
        "プレミアルーム2": {"param": "%B7%C5%CC2%D4000", "data_id": "11100D1"}  # ｷﾅﾌ2ﾔ000
    }

    seat_configs_nobori = {
        "クシェット": {"param": "%B7%C5%B8%BC%CB000", "data_id": "3010000"}, # ｷﾅｸｼﾋ000
        "ファーストシート": {"param": "%B7%C5%CC%B1%CB000", "data_id": "1010000"}, # ｷﾅﾌｱﾋ000
        "プレミアルーム1": {"param": "%B7%C5%CC1%CB000", "data_id": "11100C1"}, # ｷﾅﾌ1ﾋ000
        "プレミアルーム2": {"param": "%B7%C5%CC2%CB000", "data_id": "11100E1"}  # ｷﾅﾌ2ﾋ000
    }

    import calendar
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()

    # 1か月先の計算
    next_month_year = today.year
    next_month = today.month + 1
    if next_month > 12:
        next_month_year += 1
        next_month = 1
    
    max_day = calendar.monthrange(next_month_year, next_month)[1]
    next_month_day = min(today.day, max_day)
    one_month_later = today.replace(year=next_month_year, month=next_month, day=next_month_day)

    kyoto_to_shingu = [
        "20260703", "20260706", "20260710", "20260713", "20260717", "20260720", "20260724", "20260727", "20260731",
        "20260803", "20260807", "20260817", "20260821", "20260824", "20260828", "20260831",
        "20260904", "20260907", "20260911", "20260914", "20260918", "20260921", "20260925", "20260928"
    ]
    shingu_to_kyoto = [
        "20260705", "20260708", "20260712", "20260715", "20260719", "20260722", "20260726", "20260729",
        "20260802", "20260805", "20260809", "20260819", "20260823", "20260826", "20260830",
        "20260902", "20260906", "20260909", "20260913", "20260916", "20260920", "20260923", "20260927", "20260930"
    ]

    search_conditions = []
    kudari_dates_list = []
    nobori_dates_list = []

    for d_str in kyoto_to_shingu:
        d_date = datetime.strptime(d_str, "%Y%m%d").date()
        if today <= d_date <= one_month_later:
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
        d_date = datetime.strptime(d_str, "%Y%m%d").date()
        if today <= d_date <= one_month_later:
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

    # 対象日時文字列の作成
    target_dates_str = f"下り: {', '.join(kudari_dates_list)} | 上り: {', '.join(nobori_dates_list)}"

    check_e5489_availability_dates(search_conditions, target_dates_str)
