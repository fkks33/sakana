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

# ==========================================
# 気象庁API 天気情報取得
# ==========================================
def get_weather_info():
    targets = [
        {"display": "東京", "code": "130000", "temp_city": "東京"},
        {"display": "高松", "code": "370000", "temp_city": "高松"},
        {"display": "出雲", "code": "320000", "temp_city": "松江"} 
    ]
    
    weather_lines = ["\n～本日の天気～"]
    
    for target in targets:
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{target['code']}.json"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # [0]番目の要素（短期予報）を取得
            short_term = data[0]

            # 1. 天気の抽出
            weather = short_term['timeSeries'][0]['areas'][0]['weathers'][0]
            weather = weather.replace('\u3000', ' ').replace('\n', '')

            # 2. 気温の抽出 (最低気温・最高気温)
            temp_areas = short_term['timeSeries'][2]['areas']
            temp_min = "--"
            temp_max = "--"
            
            for area in temp_areas:
                if area['area']['name'] == target['temp_city']:
                    temps = area.get('temps', [])
                    if len(temps) >= 2:
                        temp_min = temps[0]
                        temp_max = temps[1]
                    elif len(temps) == 1:
                        # 取得時間が遅く、最高気温のみの発表になっている場合のフォールバック
                        temp_max = temps[0]
                    break

            # 指定されたフォーマットで追加
            weather_lines.append(f"■ {target['display']}...{temp_min}℃ / {temp_max}℃\n{weather}")

        except Exception as e:
            weather_lines.append(f"■ {target['display']}...データ取得エラー\nエラー詳細: {e}")
            print(f"天気取得エラー({target['display']}): {e}")

    return "\n".join(weather_lines)

# ==========================================
# e5489 空席状況チェック処理
# ==========================================
def check_e5489_availability_dates(target_dates):
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
    now = datetime.now(JST)
    
    # 曜日の取得と日時フォーマット
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_str = weekdays[now.weekday()]
    start_time = now.strftime(f"%Y-%m-%d({weekday_str}) %H:%M:%S")

    final_messages = [
        "【今夜の日の出情報】\n",
        f"{start_time}時点"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for date in target_dates:
            if len(target_dates) > 1:
                final_messages.append(f"\n【対象日: {date}】")

            for route in routes:
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
                                pass

                            page_loaded = True
                            break

                        except Exception:
                            retry_count += 1
                            time.sleep(2)

                    if not page_loaded:
                        for seat_name in seats_to_check.keys():
                            route_results[seat_name] = "エラー"
                        time.sleep(1)
                        continue

                    for seat_name, data_search_id in seats_to_check.items():
                        try:
                            selector = f"td[data-search-id='{data_search_id}'] img"
                            img_elements = page.query_selector_all(selector)

                            if img_elements:
                                for img in img_elements:
                                    alt_text = img.get_attribute("alt")
                                    if alt_text:
                                        # 【追加】テキストを記号に変換
                                        if alt_text == "空席あり":
                                            alt_text = "〇"
                                        elif alt_text == "空席残りわずか":
                                            alt_text = "△"
                                        elif alt_text == "残席なし":
                                            alt_text = "×"

                                        route_results[seat_name] = alt_text
                                        break
                        except Exception:
                            route_results[seat_name] = "取得失敗"

                    time.sleep(1)

                route_msg = f"\n■ {route['name']}"
                printed_seats_count = 0 
                
                for seat in seat_order:
                    status = route_results[seat]
                    
                    # 【修正】「×」と念のため元の「残席なし」をスキップするように条件を変更
                    if status == "×" or status == "残席なし":
                        continue
                        
                    route_msg += f"\n{seat}：{status}"
                    printed_seats_count += 1
                
                if printed_seats_count == 0:
                    route_msg += "\n　　≪　残　席　な　し　≫"
                
                final_messages.append(route_msg)

        browser.close()

    # ==========================================
    # 天気情報の取得と追加
    # ==========================================
    weather_info = get_weather_info()
    final_messages.append(weather_info)

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
