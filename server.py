from flask import Flask, request, jsonify
import threading
import time
import requests

app = Flask(__name__)

conversations = {}

# Improved Token/Cookie Validator
def validate_ids(login_type, id_list):
    valid = []
    invalid = []
    for item in id_list:
        if login_type == "token":
            try:
                check = requests.get(f"https://graph.facebook.com/me?access_token={item}")
                data = check.json()
                if 'error' in data:
                    invalid.append(item)
                else:
                    valid.append({"name": data.get('name', 'FB User'), "token": item})
            except Exception as e:
                print(f"Error validating token: {e}")
                invalid.append(item)
        else:
            try:
                headers = {"Cookie": item}
                res = requests.get("https://m.facebook.com/profile.php", headers=headers).text
                if "mbasic_logout_button" in res or "logout.php" in res:
                    valid.append({"name": "FB User", "token": item})
                else:
                    invalid.append(item)
            except Exception as e:
                print(f"Error validating cookie: {e}")
                invalid.append(item)
    return valid, invalid

def send_messages(convo_name):
    convo = conversations[convo_name]
    while convo['active']:
        for message in convo['messages']:
            for token_info in convo['ids']:
                token = token_info['token']
                headers = {'Content-Type': 'application/json'}
                payload = {
                    'access_token': token,
                    'message': convo['hatter'] + ' ' + message
                }
                try:
                    response = requests.post(
                        f"https://graph.facebook.com/v15.0/t_{convo['convo_id']}/",
                        json=payload,
                        headers=headers
                    )
                    print(f"[+] Sent: {message} | By: {token_info['name']} | Status: {response.status_code}")
                except Exception as e:
                    print(f"[x] Error sending: {message} | By: {token_info['name']} | Error: {e}")
                time.sleep(convo['delay'])
        print("[+] All messages sent. Restarting loop...")

@app.route('/start_convo', methods=['POST'])
def start_convo():
    data = request.json
    convo_name = data['convo_name']
    login_type = data['login_type']
    id_list = data['ids']
    convo_id = data['convo_id']
    hatter = data['hatter']
    messages = data['messages']
    delay = int(data['delay'])

    valid, invalid = validate_ids(login_type, id_list)
    if not valid:
        return jsonify({"status": "error", "message": "No valid IDs found.", "invalid_count": len(invalid)})

    conversations[convo_name] = {
        'convo_id': convo_id,
        'hatter': hatter,
        'messages': messages,
        'delay': delay,
        'ids': valid,
        'active': True
    }

    thread = threading.Thread(target=send_messages, args=(convo_name,))
    thread.start()

    return jsonify({"status": "started", "valid": valid, "invalid_count": len(invalid)})

@app.route('/stop_convo', methods=['POST'])
def stop_convo():
    data = request.json
    convo_name = data['convo_name']
    if convo_name in conversations:
        conversations[convo_name]['active'] = False
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_found"})

@app.route('/resume_convo', methods=['POST'])
def resume_convo():
    data = request.json
    convo_name = data['convo_name']
    if convo_name in conversations:
        conversations[convo_name]['active'] = True
        thread = threading.Thread(target=send_messages, args=(convo_name,))
        thread.start()
        return jsonify({"status": "resumed"})
    return jsonify({"status": "not_found"})

@app.route('/view_convos', methods=['GET'])
def view_convos():
    result = {name: {k: v for k, v in convo.items() if k != 'ids'} for name, convo in conversations.items()}
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
