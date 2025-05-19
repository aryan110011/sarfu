from flask import Flask, request, jsonify, stream_with_context, Response
from threading import Thread
import time
import random

app = Flask(__name__)

# In-memory store
conversations = {}
resumable_convos = {}

# Dummy name fetcher from token or cookie
def get_name_from_token(token):
    if "invalid" in token.lower():
        return None
    return f"User_{random.randint(1000, 9999)}"

def get_name_from_cookie(cookie):
    if "invalid" in cookie.lower():
        return None
    return f"CookieUser_{random.randint(1000, 9999)}"

@app.route("/validate_id", methods=["POST"])
def validate_id():
    data = request.json
    id_type = data.get("type")
    value = data.get("value")

    if id_type == "token":
        name = get_name_from_token(value)
    elif id_type == "cookie":
        name = get_name_from_cookie(value)
    else:
        return jsonify({"valid": False})

    if name:
        return jsonify({"valid": True, "name": name})
    else:
        return jsonify({"valid": False})

def send_messages(convo_name, accounts, group_ids, hatter_name, messages, delay):
    while convo_name in conversations:
        for acc in accounts:
            acc_type = acc['type']
            acc_val = acc['value']
            sender = get_name_from_token(acc_val) if acc_type == 'token' else get_name_from_cookie(acc_val)

            for group in group_ids:
                msg = random.choice(messages)
                line = f"{hatter_name} [{sender}] to Group {group}: {msg}"
                conversations[convo_name].append(line)

        time.sleep(delay)

@app.route("/start_convo", methods=["POST"])
def start_convo():
    data = request.json
    convo_name = data['convo_name']
    if convo_name in conversations:
        return "❌ Conversation name already running"

    conversations[convo_name] = []
    thread = Thread(target=send_messages, args=(
        convo_name,
        data['accounts'],
        data['group_ids'],
        data['hatter_name'],
        data['messages'],
        data['delay']
    ))
    thread.start()
    return f"✅ Conversation '{convo_name}' started."

@app.route("/view_convos", methods=["GET"])
def view_convos():
    return jsonify({"conversations": list(conversations.keys())})

@app.route("/stream_convo/<convo>", methods=["GET"])
def stream_convo(convo):
    def event_stream():
        last = 0
        while convo in conversations:
            msgs = conversations[convo]
            if last < len(msgs):
                yield msgs[last] + '\n'
                last += 1
            time.sleep(1)
    return Response(stream_with_context(event_stream()), mimetype='text/plain')

@app.route("/resume_convos", methods=["GET"])
def resume_convos():
    return jsonify({"resumable": list(resumable_convos.keys())})

@app.route("/stream_resume/<convo>", methods=["GET"])
def stream_resume(convo):
    def event_stream():
        msgs = resumable_convos.get(convo, [])
        for msg in msgs:
            yield msg + '\n'
            time.sleep(0.5)
    return Response(stream_with_context(event_stream()), mimetype='text/plain')

@app.route("/stop_convo", methods=["POST"])
def stop_convo():
    data = request.json
    convo_name = data['convo_name']
    if convo_name in conversations:
        resumable_convos[convo_name] = conversations[convo_name]
        del conversations[convo_name]
        return f"✅ Conversation '{convo_name}' stopped."
    return "❌ Conversation not found."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
