import requests
import os

TELEGRAM_TOKEN = "token_bot"

SERVER_URL = "https://fleet-monitor-service-963859706153.europe-west1.run.app" 
WEBHOOK_URL = f"{SERVER_URL}/webhook"

def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    if response.status_code == 200 and response.json().get("ok"):
        print("Webhook impostato con successo!")
        print(response.json())
    else:
        print("Errore nell'impostazione del webhook:")
        print(response.text)

if __name__ == "__main__":
    if not SERVER_URL or "URL Fututo" in SERVER_URL:
        print("ERRORE")
    else:
        set_webhook()
