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
    user_states[chat_id] = "AWAITING_USERNAME"
    return "Inserire Username:"

def handle_username(chat_id, username):
    user_states[chat_id] = {"username": username}
    return "Condividere posizione in tempo reale:"

def handle_location(chat_id, location_data):
    if chat_id not in user_states or "username" not in user_states.get(chat_id, {}):
        return "Errore. Usare /start per iniziare."

    username = user_states[chat_id]["username"]
    row_to_insert = {
        "username": username,
        "latitude": location_data['latitude'],
        "longitude": location_data['longitude'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    errors = bq_client.insert_rows_json(table_ref, [row_to_insert])
    if not errors:
        return None
    else:
        print(f"Errore durante l'inserimento in BigQuery: {errors}")
        return "Errore nel salvataggio della posizione."

@app.route('/webhook', methods=['POST'])
def webhook():
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
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        print("ERRORE: La variabile d'ambiente TELEGRAM_TOKEN non è impostata.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route('/')
def dashboard():
    selected_user = request.args.get('username', 'all')
    

    where_clause = ""
    if selected_user != 'all':
        
        where_clause = f"WHERE username = '{selected_user}'"

    
    query_stats = f"SELECT COUNT(DISTINCT username) as total_vehicles, MIN(timestamp) as start_date FROM `{table_ref}` {where_clause}"
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

    
    query_trajectories = f"SELECT username, latitude, longitude FROM `{table_ref}` {where_clause} ORDER BY timestamp"
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
        selected_user=selected_user
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

