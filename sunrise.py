import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

from utils.line_api import send_line_message
from utils.date_utils import get_jst_now
from utils.scraper import fetch_seat_statuses

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

            short_term = data[0]

            weather = short_term['timeSeries'][0]['areas'][0]['weathers'][0]
            weather = weather.replace('\u3000', ' ').replace('\n', '')

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
                        temp_max = temps[0]
                    break

            if temp_min == temp_max or temp_min == "--":
                temp_str = f"{temp_max}℃"
            else:
                temp_str = f"{temp_min}℃ / {temp_max}℃"

            pop_areas = short_term['timeSeries'][1]['areas']
            pop_str = ""
            for area in pop_areas:
                if area['area']['name'] == target['temp_city']:
                    pops = area.get('pops', [])
                    if pops:
                        pop_str = f" ☔ {'/'.join(pops)}%"
                    break

            weather_lines.append(f"■ {target['display']}...{temp_str}{pop_str}\n{weather}")

        except Exception as e:
            weather_lines.append(f"■ {target['display']}...データ取得エラー\nエラー詳細: {e}")
            print(f"天気取得エラー({target['display']}): {e}")

    return "\n".join(weather_lines)

def check_e5489_availability_dates(target_dates):
    base_hour = "18"
    base_minute = "00"

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

    seat_order = [
        "ノビノビ座席", "ソロ", "シングル(禁煙)", "シングル(喫煙)",
        "シングルツイン(禁煙)", "シングルツイン(喫煙)", "サンライズツイン(禁煙)",
        "サンライズツイン(喫煙)", "シングルデラックス(禁煙)", "シングルデラックス(喫煙)"
    ]

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

    now = get_jst_now()
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

                    data_search_ids = list(seats_to_check.values())
                    statuses = fetch_seat_statuses(page, url, data_search_ids)

                    for seat_name, ds_id in seats_to_check.items():
                        route_results[seat_name] = statuses.get(ds_id, "取得失敗")

                    time.sleep(1)

                route_msg = f"\n■ {route['name']}"
                printed_seats_count = 0 
                
                for seat in seat_order:
                    status = route_results[seat]
                    if status in ["×", "残席なし", "座席なし"]:
                        continue
                        
                    route_msg += f"\n{seat}：{status}"
                    printed_seats_count += 1
                
                if printed_seats_count == 0:
                    route_msg += "\n　　≪　残　席　な　し　≫"
                
                final_messages.append(route_msg)

        browser.close()

    weather_info = get_weather_info()
    final_messages.append(weather_info)

    final_output = "\n".join(final_messages)
    print(final_output)

    send_line_message(final_output, method="push")

if __name__ == "__main__":
    today = get_jst_now().strftime("%Y%m%d")
    check_e5489_availability_dates([today])
