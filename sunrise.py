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
    # e5489は指定時刻「以降」の列車を検索するため、全て夕方(18:00)を指定して夜行を拾う
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

    # 4つの検索ルート
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
        "【今夜の日の出予報】",
        f"取得開始日時: {start_time}"
    ]

    has_any_available_seat = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for date in target_dates:
            available_list = []
            unavailable_dict = {route["name"]: [] for route in routes}

            for route in routes:
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
                                pass # 要素が出ない場合（満席や運行なし等）もスルー

                            page_loaded = True
                            break

                        except Exception:
                            retry_count += 1
                            time.sleep(2)

                    if not page_loaded:
                        # ページロード失敗時はすべてエラー扱い
                        for seat_name in seats_to_check.keys():
                            unavailable_dict[route["name"]].append(f"{seat_name}(エラー)")
                        time.sleep(1)
                        continue

                    # 座席の空き状況をチェック
                    for seat_name, data_search_id in seats_to_check.items():
                        try:
                            selector = f"td[data-search-id='{data_search_id}'] img"
                            img_elements = page.query_selector_all(selector)

                            if img_elements:
                                found = False
                                for img in img_elements:
                                    alt_text = img.get_attribute("alt")
                                    if alt_text not in ["残席なし", "座席なし"]:
                                        has_any_available_seat = True
                                        # 空席ありの場合は優先リストに追加し、該当URLも付与
                                        available_list.append(f"・{route['name']} - 【{seat_name}】: {alt_text}\n  URL: {url}")
                                        found = True
                                        break
                                
                                if not found:
                                    # 残席なし等の場合
                                    unavailable_dict[route["name"]].append(seat_name)
                            else:
                                unavailable_dict[route["name"]].append(f"{seat_name}(情報無)")
                        except Exception:
                            unavailable_dict[route["name"]].append(f"{seat_name}(取得失敗)")

                    time.sleep(1) # サーバ負荷軽減のインターバル

            # ------------------------------------------
            # 1日分のメッセージを成形
            # ------------------------------------------
            date_msg = f"\n====================\n■ {date} の空席状況\n===================="
            
            # 【空きがある座席】（優先表示）
            if available_list:
                date_msg += "\n\n【空席あり】\n" + "\n\n".join(available_list)
            else:
                date_msg += "\n\n【空席あり】\n・該当なし"

            # 【空きがない座席】（下にまとめて表示）
            date_msg += "\n\n【満席 / 情報なし一覧】"
            for r_name, u_seats in unavailable_dict.items():
                if u_seats:
                    # 見やすくするためにカンマ区切りで結合
                    seats_str = ", ".join(u_seats)
                    date_msg += f"\n・{r_name}:\n  {seats_str}"
                
            final_messages.append(date_msg)

        browser.close()

    # ==========================================
    # 最終メッセージの出力とLINE通知
    # ==========================================
    final_output = "\n".join(final_messages)
    print(final_output)

    # 空席が1つでもあればLINEへ通知（毎回の満席通知を避ける仕様）
    if has_any_available_seat:
        send_line_message(final_output)
    else:
        print("\n全日程で空席なし: LINE通知をスキップしました")

# ==========================================
# メイン
# ==========================================
if __name__ == "__main__":
    # 今日の日付を日本時間(JST)で検索対象とする
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")
    target_dates = [today]

    check_e5489_availability_dates(target_dates)
