import os
import requests

def send_line_message(message, method="broadcast", to=None):
    """
    Sends a LINE message.
    :param message: The text message to send.
    :param method: "broadcast" or "push".
    :param to: LINE_USER_ID, required if method is "push".
    """
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    
    if method == "broadcast":
        url = "https://api.line.me/v2/bot/message/broadcast"
        payload = {
            "messages": [{"type": "text", "text": message}]
        }
    elif method == "push":
        url = "https://api.line.me/v2/bot/message/push"
        if not to:
            to = os.environ.get("LINE_USER_ID")
        payload = {
            "to": to,
            "messages": [{"type": "text", "text": message}]
        }
    else:
        print(f"Unknown LINE message method: {method}")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"LINE通知送信 ({method}): 成功")
    except requests.exceptions.RequestException as e:
        print(f"LINE通知送信エラー: {e}")
        if e.response is not None:
            print(f"詳細: {e.response.text}")
