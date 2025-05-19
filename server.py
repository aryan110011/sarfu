from flask import Flask, request, jsonify
import requests
import threading
import time
import os
import random

app = Flask(__name__)

conversations = {}  # { convo_name: { data... } }

GRAPH_URL = "https://graph.facebook.com/v15.0"

def send_message(convo_name):
    data = conversations[convo_name]
    tokens = data['tokens']
    convo_ids = data['convo_ids']
    messages = data['messages']
    delay = data['delay']
    hatter_name = data['hatter_name']

    while data['active']:
        for convo_id in convo_ids:
            for msg in messages:
                token = random.choice(tokens)
                payload = {
                    'access_token': token,
                    'message': f"{hatter_name} {msg}"
                }
                response = requests.post(f"{GRAPH_URL}/t_{convo_id}/", data=payload)
                status = "✅ Sent" if response.ok else "❌ Failed"
                print(f"[{status}] {msg} -> {convo_id}")
                time.sleep(delay)

@app.route('/start_convo', methods=['POST'])
def start_convo():
    content = request.json
    convo_name = content['convo_name']

    tokens = content['tokens']  # list of access tokens
    convo_ids = content['convo_ids']  # list of convo ids
    messages = content['messages']  # list of messages
    delay = int(content['delay'])
    hatter_name = content['hatter_name']

    conversations[convo_name] = {
        'tokens': tokens,
        'convo_ids': convo_ids,
        'messages': messages,
        'delay': delay,
        'hatter_name': hatter_name,
        'active': True
    }

    threading.Thread(target=send_message, args=(convo_name,), daemon=True).start()
    return jsonify({"status": "started", "convo_name": convo_name})

@app.route('/resume_convo', methods=['POST'])
def resume_convo():
    convo_name = request.json['convo_name']
    if convo_name in conversations and not conversations[convo_name]['active']:
        conversations[convo_name]['active'] = True
        threading.Thread(target=send_message, args=(convo_name,), daemon=True).start()
        return jsonify({"status": "resumed"})
    return jsonify({"error": "Conversation not found or already active"})

@app.route('/stop_convo', methods=['POST'])
def stop_convo():
    convo_name = request.json['convo_name']
    if convo_name in conversations:
        conversations[convo_name]['active'] = False
        return jsonify({"status": "stopped"})
    return jsonify({"error": "Conversation not found"})

@app.route('/view_convos', methods=['GET'])
def view_convos():
    return jsonify({
        name: {
            'active': conv['active'],
            'convo_ids': conv['convo_ids']
        } for name, conv in conversations.items()
    })

@app.route('/validate_tokens', methods=['POST'])
def validate_tokens():
    content = request.json
    login_type = content['type']
    items = content['items']  # token or cookie list

    valid = []
    invalid = []

    for item in items:
        try:
            if login_type == "token":
                res = requests.get(f"https://graph.facebook.com/me?access_token={item}").json()
            else:
                headers = {"Cookie": item}
                res = requests.get("https://m.facebook.com/profile.php", headers=headers).text
                if "mbasic_logout_button" in res or "logout.php" in res:
                    res = {"name": "FB User"}
                else:
                    res = {}

            if 'name' in res:
                valid.append({"name": res['name'], "token": item})
            else:
                invalid.append(item)
        except:
            invalid.append(item)

    return jsonify({
        "valid_ids": valid,
        "invalid_count": len(invalid)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
