from datetime import datetime
from utils.date_utils import get_jst_now
from utils.runner import run_availability_check

def main():
    today = get_jst_now().strftime("%Y%m%d")
    target_dates = [today]

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
        {"name": "サンライズ瀬戸 (東京→高松)", "depart_name": "東京", "arrive_name": "高松", "depart": "%93%8C%8B%9E", "arrive": "%8D%82%8F%BC%81i%8D%81%90%EC%8C%A7%81j", "groups": seto_groups},
        {"name": "サンライズ出雲 (東京→出雲市)", "depart_name": "東京", "arrive_name": "出雲市", "depart": "%93%8C%8B%9E", "arrive": "%8Fo%89_%8Es", "groups": izumo_groups},
        {"name": "サンライズ瀬戸 (高松→東京)", "depart_name": "高松", "arrive_name": "東京", "depart": "%8D%82%8F%BC%81i%8D%81%90%EC%8C%A7%81j", "arrive": "%93%8C%8B%9E", "groups": seto_groups},
        {"name": "サンライズ出雲 (出雲市→東京)", "depart_name": "出雲市", "arrive_name": "東京", "depart": "%8Fo%89_%8Es", "arrive": "%93%8C%8B%9E", "groups": izumo_groups}
    ]

    search_conditions = []
    dates_list = []

    for d_str in target_dates:
        dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))
        for route in routes:
            # Flatten the groups into a single seat_configs for the runner
            seat_configs = {}
            for group in route["groups"]:
                param = group["param"]
                for seat_name, data_id in group["seats"].items():
                    seat_configs[seat_name] = {"param": param, "data_id": data_id}

            search_conditions.append({
                "name": route["name"],
                "depart_name": route["depart_name"],
                "arrive_name": route["arrive_name"],
                "depart": route["depart"],
                "arrive": route["arrive"],
                "date": d_str,
                "hour": base_hour,
                "minute": base_minute,
                "seat_configs": seat_configs,
                "direction": "unknown"
            })

    target_dates_str = ", ".join(dates_list)

    run_availability_check(
        course_name="sunrise",
        display_name="サンライズ出雲・瀬戸",
        target_dates_str=target_dates_str,
        search_conditions=search_conditions,
        line_method="push"
    )

if __name__ == "__main__":
    main()
