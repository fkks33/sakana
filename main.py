import time
import requests
import os
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ==========================================
# LINE Messaging API の設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

FIXED_RESERVATION_URL = "https://www.jr-odekake.net/railroad/westexginga/reservation/#route-sanin"

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

def check_e5489_availability_dates(seat_types, search_conditions):
    # ==========================================
    # UTC → JST変換
    # ==========================================
    JST = timezone(timedelta(hours=9))
    start_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

    result_messages = [
        "[e5489 空席照会結果]",
        f"取得開始日時: {start_time}"
    ]

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
            section_messages = []

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

                                if alt_text not in ["残席なし", "座席なし"]:
                                    has_available_seat = True

                                msg = (
                                    f"■ {condition['name']} ({condition['date']})\n"
                                    f"【{seat_name}】: {alt_text}"
                                )
                                section_messages.append(msg)
                            break
                        else:
                            msg = (
                                f"■ {condition['name']} ({condition['date']})\n"
                                f"【{seat_name}】: 情報なし"
                            )
                            section_messages.append(msg)
                            break

                    except Exception:
                        msg = (
                            f"■ {condition['name']} ({condition['date']})\n"
                            f"【{seat_name}】: 取得エラー"
                        )
                        section_messages.append(msg)
                        break

                time.sleep(1)

            result_messages.extend(section_messages)

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
    seat_configs = {
        "クシェット": {"param": "%B7%B2%DD%B8%BC000", "data_id": "3010000"},
        "リクライニング": {"param": "%B7%B2%DD%20%20000", "data_id": "3010000"}
    }

    search_conditions = [
        {
            "name": "京都→出雲市",
            "depart": "%8B%9E%93s",
            "arrive": "%8Fo%89_%8Es",
            "date": "20260403",
            "hour": "21",
            "minute": "00"
        },
        {
            "name": "出雲市→京都",
            "depart": "%8Fo%89_%8Es",
            "arrive": "%8B%9E%93s",
            "date": "20260404",
            "hour": "09",
            "minute": "00"
        },
        {
            "name": "京都→出雲市",
            "depart": "%8B%9E%93s",
            "arrive": "%8Fo%89_%8Es",
            "date": "20260417",
            "hour": "21",
            "minute": "00"
        },
        {
            "name": "出雲市→京都",
            "depart": "%8Fo%89_%8Es",
            "arrive": "%8B%9E%93s",
            "date": "20260418",
            "hour": "09",
            "minute": "00"
        }
    ]

    check_e5489_availability_dates(seat_configs, search_conditions)
