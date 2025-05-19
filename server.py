from flask import Flask, request, jsonify, Response
import threading
import time

app = Flask(__name__)

# Memory storage
conversations = {}
message_logs = {}
stopped_convos = {}

def send_messages(convo_name, convo_data):
    accounts = convo_data["accounts"]
    group_ids = convo_data["group_ids"]
    messages = convo_data["messages"]
    hatter_name = convo_data["hatter_name"]
    delay = convo_data["delay"]

    message_logs[convo_name] = []
    try:
        while convo_name in conversations:
            for acc in accounts:
                for gid in group_ids:
                    for msg in messages:
                        full_msg = f"[{hatter_name}] {msg}"
                        log = f"[{acc['name']} → Group {gid}]: {full_msg}"
                        print(log)
                        message_logs[convo_name].append(log)
                        time.sleep(delay)
    except Exception as e:
        print(f"[ERROR] {e}")

@app.route('/start_convo', methods=['POST'])
def start_convo():
    data = request.json
    convo_name = data.get("convo_name")

    if convo_name in conversations:
        return jsonify({"error": "Conversation already running."}), 400

    thread = threading.Thread(target=send_messages, args=(convo_name, data), daemon=True)
    thread.start()
    conversations[convo_name] = thread

    return jsonify({"message": f"Conversation '{convo_name}' started."})

@app.route('/view_convos', methods=['GET'])
def view_convos():
    return jsonify({"conversations": list(conversations.keys())})

@app.route('/stream_convo/<convo_name>', methods=['GET'])
def stream_convo(convo_name):
    def generate():
        prev_len = 0
        while convo_name in conversations:
            logs = message_logs.get(convo_name, [])
            new_logs = logs[prev_len:]
            for line in new_logs:
                yield line + "\n"
            prev_len = len(logs)
            time.sleep(1)
    return Response(generate(), mimetype='text/plain')

@app.route('/resume_convos', methods=['GET'])
def resume_convos():
    resumables = [name for name in message_logs.keys() if name not in conversations]
    return jsonify({"resumable": resumables})

@app.route('/stream_resume/<convo_name>', methods=['GET'])
def stream_resume(convo_name):
    logs = message_logs.get(convo_name, [])
    return Response("\n".join(logs), mimetype='text/plain')

@app.route('/stop_convo', methods=['POST'])
def stop_convo():
    convo_name = request.json.get("convo_name")
    if convo_name in conversations:
        del conversations[convo_name]
        stopped_convos[convo_name] = True
        return jsonify({"message": f"Conversation '{convo_name}' stopped."})
    else:
        return jsonify({"error": "Conversation not found."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
