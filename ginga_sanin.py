import json
from datetime import datetime
from utils.date_utils import filter_target_dates
from utils.runner import run_availability_check

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
    kudari_dates_list = []
    nobori_dates_list = []

    for d_str in kyoto_to_izumo:
        search_conditions.append({
            "name": "京都→出雲市",
            "depart_name": "京都",
            "arrive_name": "出雲市",
            "depart": "%8B%9E%93s",
            "arrive": "%8Fo%89_%8Es",
            "date": d_str,
            "hour": "21",
            "minute": "00",
            "seat_configs": seat_configs,
            "direction": "kudari"
        })
        kudari_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    for d_str in izumo_to_kyoto:
        search_conditions.append({
            "name": "出雲市→京都",
            "depart_name": "出雲市",
            "arrive_name": "京都",
            "depart": "%8Fo%89_%8Es",
            "arrive": "%8B%9E%93s",
            "date": d_str,
            "hour": "09",
            "minute": "00",
            "seat_configs": seat_configs,
            "direction": "nobori"
        })
        nobori_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    target_dates_str = f"下り: {', '.join(kudari_dates_list)} | 上り: {', '.join(nobori_dates_list)}"

    run_availability_check(
        course_name="sanin",
        display_name="WEST EXPRESS 銀河（山陰コース）",
        target_dates_str=target_dates_str,
        search_conditions=search_conditions,
        line_method="broadcast"
    )

if __name__ == "__main__":
    main()
