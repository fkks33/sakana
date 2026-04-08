import time
import requests
import os
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ==========================================
# LINE Messaging API の設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

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

def check_e5489_availability_dates(target_dates):
    # ==========================================
    # 検索条件の定義（4つの列車ルート）
    # ==========================================
    base_hour = "18"
    base_minute = "00"

    # 座席とデータIDの定義
    base_seats = {
        "ノビノビ座席": "3010000",
        "シングルツイン(禁煙)": "4110042",
        "シングルツイン(喫煙)": "4120042",
        "シングルデラックス(禁煙)": "2110002",
        "シングルデラックス(喫煙)": "2120002"
    }
    solo_seats = {"ソロ": "4110040"}
    single_seats = {"シングル(禁煙)": "4110041", "シングル(喫煙)": "4120041"}
    suntwin_seats = {"サンライズツイン(禁煙)": "4110062", "サンライズツイン(喫煙)": "4120062"}

    # 出力順序の固定
    seat_order = [
        "ノビノビ座席",
        "ソロ",
        "シングル(禁煙)",
        "シングル(喫煙)",
        "シングルツイン(禁煙)",
        "シングルツイン(喫煙)",
        "サンライズツイン(禁煙)",
        "サンライズツイン(喫煙)",
        "シングルデラックス(禁煙)",
        "シングルデラックス(喫煙)"
    ]

    # 瀬戸・出雲のパラメータグループ
    seto_groups = [
        {"param": "%BB%BE%C4%20%20000", "seats": base_seats},
        {"param": "%BB%BE%C4%BF%20000", "seats": solo_seats},
        {"param": "%BB%BE%C4%BC%20000", "seats": single_seats},
        {"param": "%BB%BE%C4%BB%20000", "seats": suntwin_seats}
    ]

    izumo_groups = [
        {"param": "%BB%B2%BD%D3%20000", "seats": base_seats},
        {"param": "%BB%B2%BD%D3%BF000", "seats": solo_seats},
        {"param": "%BB%B2%BD%D3%BC000", "seats": single_seats},
        {"param": "%BB%B2%BD%D3%BB000", "seats": suntwin_seats}
    ]

    routes = [
        {"name": "サンライズ瀬戸 (東京→高松)", "depart": "%93%8C%8B%9E", "arrive": "%8D%82%8F%BC%81i%8D%81%90%EC%8C%A7%81j", "groups": seto_groups},
        {"name": "サンライズ出雲 (東京→出雲市)", "depart": "%93%8C%8B%9E", "arrive": "%8Fo%89_%8Es", "groups": izumo_groups},
        {"name": "サンライズ瀬戸 (高松→東京)", "depart": "%8D%82%8F%BC%81i%8D%81%90%EC%8C%A7%81j", "arrive": "%93%8C%8B%9E", "groups": seto_groups},
        {"name": "サンライズ出雲 (出雲市→東京)", "depart": "%8Fo%89_%8Es", "arrive": "%93%8C%8B%9E", "groups": izumo_groups}
    ]

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

    JST = timezone(timedelta(hours=9))
    start_time = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

    final_messages = [
        "【今夜の日の出情報】\n",
        f"取得開始日時: {start_time}"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for date in target_dates:
            # 複数日指定された場合を考慮し、日付の区切りを挿入
            if len(target_dates) > 1:
                final_messages.append(f"\n【対象日: {date}】")

            for route in routes:
                # この列車の各座席状況を格納（初期値は取得失敗や情報無とする）
                route_results = {seat: "情報無" for seat in seat_order}

                for group in route["groups"]:
                    train_kana_param = group["param"]
                    seats_to_check = group["seats"]

                    url = base_url.format(
                        depart=route["depart"],
                        arrive=route["arrive"],
                        date=date,
                        hour=base_hour,
                        minute=base_minute,
                        param=train_kana_param
                    )

                    retry_count = 0
                    max_retries = 5
                    page_loaded = False

                    while retry_count < max_retries:
                        try:
                            page.goto(url)
                            page.wait_for_load_state("domcontentloaded")

                            content = page.content()
                            if "混雑中" in content or "20100801" in content:
                                retry_count += 1
                                time.sleep(2)
                                continue

                            try:
                                page.wait_for_selector("td[data-search-id]", timeout=5000)
                            except Exception:
                                pass # 要素が出ない場合もスルー

                            page_loaded = True
                            break

                        except Exception:
                            retry_count += 1
                            time.sleep(2)

                    if not page_loaded:
                        # ロード失敗
                        for seat_name in seats_to_check.keys():
                            route_results[seat_name] = "エラー"
                        time.sleep(1)
                        continue

                    # 座席の空き状況をチェック
                    for seat_name, data_search_id in seats_to_check.items():
                        try:
                            selector = f"td[data-search-id='{data_search_id}'] img"
                            img_elements = page.query_selector_all(selector)

                            if img_elements:
                                for img in img_elements:
                                    alt_text = img.get_attribute("alt")
                                    if alt_text:
                                        route_results[seat_name] = alt_text
                                        break
                        except Exception:
                            route_results[seat_name] = "取得失敗"

                    time.sleep(1)

                # 1列車分の出力を成形
                route_msg = f"\n■ {route['name']}"
                printed_seats_count = 0 # 出力した座席数をカウント
                
                for seat in seat_order:
                    status = route_results[seat]
                    # "残席なし" の場合は出力せずスキップ
                    if status == "残席なし":
                        continue
                        
                    route_msg += f"\n{seat}:{status}"
                    printed_seats_count += 1
                
                # 1つも出力する座席がなかった（すべて「残席なし」だった）場合
                if printed_seats_count == 0:
                    route_msg += "\n　　≪　残　席　な　し　≫"
                
                final_messages.append(route_msg)

        browser.close()

    # ==========================================
    # 最終メッセージの出力とLINE通知
    # ==========================================
    final_output = "\n".join(final_messages)
    print(final_output)

    # 空き状況にかかわらず常にLINEへ通知
    send_line_message(final_output)

# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")
    target_dates = [today]
    check_e5489_availability_dates(target_dates)
