import os
import json
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, render_template
from google.cloud import bigquery

app = Flask(__name__)

bq_client = bigquery.Client()

project_id = bq_client.project
dataset_id = "fleet_data"
table_id = "positions"
table_ref = f"{project_id}.{dataset_id}.{table_id}"

user_states = {}

def handle_start(chat_id):
    """Gestisce il comando /start e chiede l'username."""
    user_states[chat_id] = "AWAITING_USERNAME"
    return "Ciao! Benvenuto nel sistema di monitoraggio. Per favore, inserisci il tuo username (es. veicolo_01):"

def handle_username(chat_id, username):
    """Gestisce l'inserimento dell'username e chiede la posizione."""
    user_states[chat_id] = {"username": username}
    return f"Grazie, {username}! Ora condividi la tua 'Posizione in tempo reale' usando l'opzione Allega > Posizione."

def handle_location(chat_id, location_data):
    """Gestisce la ricezione della posizione e la salva su BigQuery."""
    if chat_id not in user_states or "username" not in user_states.get(chat_id, {}):
        return "Errore: non ho ancora un username per te. Usa /start per iniziare."

    username = user_states[chat_id]["username"]
    latitude = location_data['latitude']
    longitude = location_data['longitude']

    row_to_insert = {
        "username": username,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    errors = bq_client.insert_rows_json(table_ref, [row_to_insert])
    if not errors:
        print(f"Dato inserito per {username}: ({latitude}, {longitude})")
        return None
    else:
        print(f"Errore durante l'inserimento in BigQuery: {errors}")
        return "Si è verificato un errore nel salvataggio della tua posizione."

@app.route('/webhook', methods=['POST'])
def webhook():
    """Riceve tutti gli aggiornamenti da Telegram."""
    data = request.get_json()
    
    message = data.get('message') or data.get('edited_message')
    if not message:
        return jsonify(status="ok")

    chat_id = message['chat']['id']
    text = message.get('text')
    location = message.get('location')
    
    response_text = ""
    if text and text == "/start":
        response_text = handle_start(chat_id)
    elif location:
        response_text = handle_location(chat_id, location)
    elif chat_id in user_states and user_states[chat_id] == "AWAITING_USERNAME":
        response_text = handle_username(chat_id, text)
    
    if response_text:
        send_telegram_message(chat_id, response_text)

    return jsonify(status="ok")


def send_telegram_message(chat_id, text):
    """Funzione helper per inviare messaggi all'utente."""

    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        print("ERRORE: La variabile d'ambiente TELEGRAM_TOKEN non è impostata.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore nell'invio del messaggio a Telegram: {e}")

@app.route('/')
def dashboard():
    """Mostra la dashboard con la mappa e le statistiche, gestendo i filtri."""

    selected_user = request.args.get('username', 'all')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    where_conditions = []
    if selected_user != 'all':
        where_conditions.append(f"username = '{selected_user}'")
    if start_date_str:
        where_conditions.append(f"DATE(timestamp) >= '{start_date_str}'")
    if end_date_str:
        where_conditions.append(f"DATE(timestamp) <= '{end_date_str}'")
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    query_stats = f"""
        SELECT COUNT(DISTINCT username) as total_vehicles, MIN(timestamp) as start_date
        FROM `{table_ref}` {where_clause}
    """
    stats_job = bq_client.query(query_stats)
    stats_result = next(stats_job.result(), None)
    if not stats_result or stats_result.total_vehicles is None:
        stats_result = {'total_vehicles': 0, 'start_date': None}

    query_rilevazioni = f"""
        SELECT username, DATE(timestamp, 'Europe/Rome') as giorno,
               MIN(timestamp) as ora_inizio, MAX(timestamp) as ora_fine,
               COUNT(*) as punti_raccolti
        FROM `{table_ref}` {where_clause}
        GROUP BY username, giorno ORDER BY username, giorno DESC
    """
    rilevazioni_job = bq_client.query(query_rilevazioni)
    rilevazioni = list(rilevazioni_job.result())

    query_trajectories = f"""
        SELECT username, latitude, longitude FROM `{table_ref}`
        {where_clause} ORDER BY timestamp
    """
    trajectories_job = bq_client.query(query_trajectories)
    trajectories_data = {}
    for row in trajectories_job.result():
        if row.username not in trajectories_data:
            trajectories_data[row.username] = []
        trajectories_data[row.username].append([row.latitude, row.longitude])

    query_all_users = f"SELECT DISTINCT username FROM `{table_ref}` ORDER BY username"
    all_users_job = bq_client.query(query_all_users)
    all_known_users = [row.username for row in all_users_job.result()]

    return render_template(
        'dashboard.html',
        stats=stats_result,
        rilevazioni=rilevazioni,
        trajectories=json.dumps(trajectories_data),
        all_users=all_known_users,
        selected_user=selected_user,
        start_date=start_date_str, 
        end_date=end_date_str      
    )




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
