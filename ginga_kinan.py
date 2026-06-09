import time
import requests
import os
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ==========================================
# LINE Messaging API の設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

FIXED_RESERVATION_URL = "https://www.jr-odekake.net/railroad/westexginga/reservation/#route-kinan"

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

def check_e5489_availability_dates(search_conditions):
    # ==========================================
    # UTC → JST変換 と 日時のフォーマット設定
    # ==========================================
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    
    # 曜日の取得
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[now.weekday()]
    start_time = now.strftime(f"%Y-%m-%d({weekday_str}) %H:%M:%S")

    result_messages = [
        "[WEST EXPRESS 銀河 紀南空席通知]",
        f"{start_time}時点"
    ]

    has_available_seat = False

    # 紀南コース用のベースURL (末尾に inputReturnUrl パラメータを付加)
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
            # ルートと日付ごとにブロックを作成
            block_lines = [f"■ {condition['name']} ({condition['date']})"]
            printed_seats_count = 0  # 出力した座席数をカウント

            # 検索条件ごとに紐付けられた seat_configs を使用する
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
                seat_status = "取得タイムアウト" # デフォルトのステータス

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

                                # 空席があるかどうかの判定 (元のまま)
                                if alt_text not in ["残席なし", "座席なし"]:
                                    has_available_seat = True
                                
                                # テキストを記号に変換
                                if alt_text == "空席あり":
                                    alt_text = "〇"
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

                # 1つの座席の取得結果をブロックに追加（×・残席なしの場合は表示をスキップ）
                if seat_status == "×" or seat_status == "残席なし":
                    continue
                
                block_lines.append(f"{seat_name}: {seat_status}")
                printed_seats_count += 1

            # 1つも表示されなかった場合の処理
            if printed_seats_count == 0:
                block_lines.append("　　≪　残　席　な　し　≫")

            # ルート・日付ブロックを最終結果のリストに追加（改行で結合）
            result_messages.append("\n".join(block_lines))

        browser.close()

    # ==========================================
    # 最終メッセージ生成
    # ==========================================
    final_message = "\n\n".join(result_messages)

    # 空席がある場合のみURLを最後に追加
    if has_available_seat:
        final_message += f"\n\n予約ページ:\n{FIXED_RESERVATION_URL}"

    print(final_message)

    if has_available_seat:
        send_line_message(final_message)
    else:
        print("空席なし: 通知スキップ")

# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    # 紀南コース：下り用の座席コード（夜行：末尾「ﾔ」）
    seat_configs_kudari = {
        "クシェット": {"param": "%B7%C5%B8%BC%D4000", "data_id": "3010000"}, # ｷﾅｸｼﾔ000
        "ファーストシート": {"param": "%B7%C5%CC%B1%D4000", "data_id": "1010000"}, # ｷﾅﾌｱﾔ000
        "プレミアルーム1": {"param": "%B7%C5%CC1%D4000", "data_id": "11100C1"}, # ｷﾅﾌ1ﾔ000
        "プレミアルーム2": {"param": "%B7%C5%CC2%D4000", "data_id": "11100D1"}  # ｷﾅﾌ2ﾔ000
    }

    # 紀南コース：上り用の座席コード（昼行：末尾「ﾋ」）
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

    # 運行日の定義
    # 下り（京都→新宮）: 7月、8月、9月の指定日
    kyoto_to_shingu = [
        "20260703", "20260706", "20260710", "20260713", "20260717", "20260720", "20260724", "20260727", "20260731",
        "20260803", "20260807", "20260817", "20260821", "20260824", "20260828", "20260831",
        "20260904", "20260907", "20260911", "20260914", "20260918", "20260921", "20260925", "20260928"
    ]
    # 上り（新宮→京都）: 7月、8月、9月の指定日
    shingu_to_kyoto = [
        "20260705", "20260708", "20260712", "20260715", "20260719", "20260722", "20260726", "20260729",
        "20260802", "20260805", "20260809", "20260819", "20260823", "20260826", "20260830",
        "20260902", "20260906", "20260909", "20260913", "20260916", "20260920", "20260923", "20260927", "20260930"
    ]

    search_conditions = []

    # 下り（京都→新宮）
    for d_str in kyoto_to_shingu:
        d_date = datetime.strptime(d_str, "%Y%m%d").date()
        if today <= d_date <= one_month_later:
            search_conditions.append({
                "name": "京都→新宮",
                "depart": "%8B%9E%93s", # 京都 (SJIS)
                "arrive": "%90V%8B%7B", # 新宮 (SJIS)
                "date": d_str,
                "hour": "21",
                "minute": "00",
                "seat_configs": seat_configs_kudari
            })

    # 上り（新宮→京都）
    for d_str in shingu_to_kyoto:
        d_date = datetime.strptime(d_str, "%Y%m%d").date()
        if today <= d_date <= one_month_later:
            search_conditions.append({
                "name": "新宮→京都",
                "depart": "%90V%8B%7B", # 新宮 (SJIS)
                "arrive": "%8B%9E%93s", # 京都 (SJIS)
                "date": d_str,
                "hour": "09",
                "minute": "00",
                "seat_configs": seat_configs_nobori
            })

    check_e5489_availability_dates(search_conditions)
