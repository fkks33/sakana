import json
from datetime import datetime
from utils.date_utils import filter_target_dates
from utils.runner import run_availability_check

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
            "depart_name": "京都",
            "arrive_name": "新宮",
            "depart": "%8B%9E%93s",
            "arrive": "%90V%8B%7B",
            "date": d_str,
            "hour": "21",
            "minute": "00",
            "seat_configs": seat_configs_kudari,
            "direction": "kudari"
        })
        kudari_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    for d_str in shingu_to_kyoto:
        search_conditions.append({
            "name": "新宮→京都",
            "depart_name": "新宮",
            "arrive_name": "京都",
            "depart": "%90V%8B%7B",
            "arrive": "%8B%9E%93s",
            "date": d_str,
            "hour": "09",
            "minute": "00",
            "seat_configs": seat_configs_nobori,
            "direction": "nobori"
        })
        nobori_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    target_dates_str = f"下り: {', '.join(kudari_dates_list)} | 上り: {', '.join(nobori_dates_list)}"

    run_availability_check(
        course_name="kinan",
        display_name="WEST EXPRESS 銀河（紀南コース）",
        target_dates_str=target_dates_str,
        search_conditions=search_conditions,
        line_method="broadcast"
    )

if __name__ == "__main__":
    main()
