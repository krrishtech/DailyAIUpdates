"""
Step 0: prove the delivery pipe works.
No LLM, no search — just confirm the bot can message you on a schedule.
"""
import os
import sys
import requests

def send_telegram_message(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
    resp.raise_for_status()
    print("Message sent:", resp.json()["result"]["message_id"])

if __name__ == "__main__":
    try:
        send_telegram_message("Daily AI feed pipeline: Step 0 works. No AI used yet.")
    except Exception as e:
        print(f"Failed to send: {e}", file=sys.stderr)
        sys.exit(1)
