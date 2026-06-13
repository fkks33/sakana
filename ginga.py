import json
import sys
from datetime import datetime
from utils.date_utils import filter_target_dates
from utils.runner import run_availability_check

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_course(config, course_key):
    if course_key == "kinan":
        kudari_dates = filter_target_dates(config.get("kinan", {}).get("kyoto_to_shingu", []))
        nobori_dates = filter_target_dates(config.get("kinan", {}).get("shingu_to_kyoto", []))
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
        course_name = "kinan"
        display_name = "WEST EXPRESS 銀河（紀南コース）"
        kudari_name = "紀南コース(下り)"
        nobori_name = "紀南コース(上り)"
        arrive_name_kudari = "新宮"
        arrive_param_kudari = "%90V%8B%7B"
        depart_name_nobori = "新宮"
        depart_param_nobori = "%90V%8B%7B"

    elif course_key == "sanin":
        kudari_dates = filter_target_dates(config.get("sanin", {}).get("kyoto_to_izumo", []))
        nobori_dates = filter_target_dates(config.get("sanin", {}).get("izumo_to_kyoto", []))
        seat_configs_kudari = {
            "クシェット": {"param": "%B7%B2%DD%B8%BC000", "data_id": "3010000"},
            "ファーストシート": {"param": "%B7%B2%DD%CC%B1000", "data_id": "1010000"},
            "プレミアルーム1": {"param": "%B7%B2%DD%CC1000", "data_id": "11100C1"},
            "プレミアルーム2": {"param": "%B7%B2%DD%CC2000", "data_id": "11100D1"}
        }
        seat_configs_nobori = seat_configs_kudari
        course_name = "sanin"
        display_name = "WEST EXPRESS 銀河（山陰コース）"
        kudari_name = "山陰コース(下り)"
        nobori_name = "山陰コース(上り)"
        arrive_name_kudari = "出雲市"
        arrive_param_kudari = "%8Fo%89_%8Es"
        depart_name_nobori = "出雲市"
        depart_param_nobori = "%8Fo%89_%8Es"
    else:
        return

    search_conditions = []
    kudari_dates_list = []
    nobori_dates_list = []

    for d_str in kudari_dates:
        search_conditions.append({
            "name": kudari_name,
            "depart_name": "京都",
            "arrive_name": arrive_name_kudari,
            "depart": "%8B%9E%93s",
            "arrive": arrive_param_kudari,
            "date": d_str,
            "hour": "21",
            "minute": "00",
            "seat_configs": seat_configs_kudari,
            "direction": "kudari"
        })
        kudari_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    for d_str in nobori_dates:
        search_conditions.append({
            "name": nobori_name,
            "depart_name": depart_name_nobori,
            "arrive_name": "京都",
            "depart": depart_param_nobori,
            "arrive": "%8B%9E%93s",
            "date": d_str,
            "hour": "09",
            "minute": "00",
            "seat_configs": seat_configs_nobori,
            "direction": "nobori"
        })
        nobori_dates_list.append(datetime.strptime(d_str, "%Y%m%d").strftime("%m/%d"))

    if not search_conditions:
        return

    target_dates_str = f"下り: {', '.join(kudari_dates_list)} | 上り: {', '.join(nobori_dates_list)}"

    run_availability_check(
        course_name=course_name,
        display_name=display_name,
        target_dates_str=target_dates_str,
        search_conditions=search_conditions,
        line_method="broadcast"
    )

def main():
    config = load_config()
    
    if len(sys.argv) > 1:
        course = sys.argv[1]
        if course in ["kinan", "sanin"]:
            run_course(config, course)
        else:
            print(f"Unknown course: {course}")
    else:
        run_course(config, "kinan")
        run_course(config, "sanin")

if __name__ == "__main__":
    main()
