import time
import requests
import os
from playwright.sync_api import sync_playwright

# ==========================================
# LINE Messaging API の設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

def send_line_message(message):
    """LINEにブロードキャスト送信する関数"""
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
        print("LINEへブロードキャスト通知を送信しました。")
    except requests.exceptions.RequestException as e:
        print(f"LINE通知エラー: {e}")

def check_e5489_availability_dates(seat_types, target_dates):
    """e5489の空席状況を照会するメイン関数 (同期版)"""
    result_messages = ["[e5489 空席照会結果]"]

    with sync_playwright() as p:
        # headless=False にするとブラウザが立ち上がる様子が見えます
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for target_date in target_dates:
            print(f"\n=== 照会開始: {target_date} ===")
            result_messages.append(f"\n■ {target_date}")
            
            for seat_name, seat_info in seat_types.items():
                train_kana_param = seat_info["param"]
                data_search_id = seat_info["data_id"]
                
                base_url = (
                    "https://e5489.jr-odekake.net/e5489/cspc/CBDayTimeArriveSelRsvMyDiaPC?"
                    "inputDepartStName=%8B%9E%93s&inputArriveStName=%90%B6%8ER&inputType=0&"
                    "inputDate={date}&inputHour=21&inputMinute=00&inputUniqueDepartSt=1&"
                    "inputUniqueArriveSt=1&inputSearchType=2&inputTransferDepartStName1=%8B%9E%93s&"
                    "inputTransferArriveStName1=%90%B6%8ER&inputTransferDepartStUnique1=1&"
                    "inputTransferArriveStUnique1=1&inputTransferTrainType1=0001&"
                    "inputSpecificTrainType1=2&inputSpecificBriefTrainKana1={param}&SequenceType=0"
                )
                
                url = base_url.format(date=target_date, param=train_kana_param)
                print(f"  【{seat_name}】 確認中...")

                retry_count = 0
                max_retries = 5
                
                while retry_count < max_retries:
                    try:
                        page.goto(url)
                        page.wait_for_load_state("domcontentloaded")

                        content = page.content()
                        if "混雑中" in content or "20100801" in content:
                            retry_count += 1
                            print(f"    [混雑中] 再試行 {retry_count}/{max_retries}...")
                            time.sleep(2) # 2秒待機
                            continue 

                        # セレクターの出現を待機
                        selector = f"td[data-search-id='{data_search_id}'] img"
                        page.wait_for_selector(selector, timeout=5000)
                        
                        img_elements = page.query_selector_all(selector)
                        
                        if img_elements:
                            for img in img_elements:
                                alt_text = img.get_attribute("alt")
                                status_msg = f"【{seat_name}】: {alt_text}"
                                if alt_text != "残席なし":
                                    status_msg += f"\n予約URL: {url}"
                                
                                print(f"    {status_msg}")
                                result_messages.append(status_msg)
                            break
                        else:
                            msg = f"【{seat_name}】: 列車が見つかりませんでした。"
                            result_messages.append(msg)
                            break
                            
                    except Exception as e:
                        print(f"    エラー発生: {e}")
                        break

                time.sleep(1) # 次の座席への待機

        browser.close()
    
    # 最後にまとめて送信
    final_message = "\n".join(result_messages)
    send_line_message(final_message)

# ==========================================
# メイン実行部分
# ==========================================
if __name__ == "__main__":
    seat_configs = {
        "クシェット": {"param": "%B7%B2%DD%B8%BC000", "data_id": "3010000"},
        "リクライニング": {"param": "%B7%B2%DD%20%20000", "data_id": "3010000"}
    }
    dates_to_check = ["20260403", "20260406", "20260417"]

    # 非同期なしの直接呼び出し
    check_e5489_availability_dates(seat_configs, dates_to_check)
