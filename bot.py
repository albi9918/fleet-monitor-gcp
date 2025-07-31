# bot.py
import requests
import os

# Carica le variabili d'ambiente (lo useremo dopo per il deploy)
# from dotenv import load_dotenv
# load_dotenv()

# Per ora, mettiamo il token qui. In produzione, useremo le variabili d'ambiente.
TELEGRAM_TOKEN = "8380003470:AAEbg_USCYqtMDto4O5I9XPhQS7vv41Nbpw"


# L'URL del nostro server che verrà deployato su Cloud Run
SERVER_URL = "https://fleet-monitor-service-963859706153.europe-west1.run.app" 
WEBHOOK_URL = f"{SERVER_URL}/webhook"

def set_webhook():
    """
    Imposta il webhook di Telegram per puntare al nostro server Flask.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    if response.status_code == 200 and response.json().get("ok"):
        print("Webhook impostato con successo!")
        print(response.json())
    else:
        print("Errore nell'impostazione del webhook:")
        print(response.text)

if __name__ == "__main__":
    if not SERVER_URL or "L_URL_CHE_OTTERRAI" in SERVER_URL:
        print("ERRORE: Devi prima deployare il server su Cloud Run e impostare la variabile SERVER_URL.")
    else:
        set_webhook()