from flask import Flask, request, jsonify, render_template
from collections import deque
from datetime import datetime
import threading, time, random
app = Flask(__name__, template_folder="templates")
MAX_HISTORY = 1000
data_store = {
    "air": deque(maxlen=MAX_HISTORY),   # entries: {ts, pm25, co2, temp}
    "water": deque(maxlen=MAX_HISTORY), # entries: {ts, ph, turbidity, temp}
    "noise": deque(maxlen=MAX_HISTORY)  # entries: {ts, db}
}
THRESHOLDS = {
    "pm25": 100,
    "co2": 1200,
    "ph_low": 6.5,
    "ph_high": 8.5,
    "turbidity": 50,
    "noise_db": 80
}
def add_reading(sensor_type, payload):
    payload = dict(payload)  # copy
    payload['ts'] = datetime.utcnow().isoformat() + "Z"
    data_store[sensor_type].append(payload)
@app.route("/")
def index():
    poster_path = "/mnt/data/miniproject poster.pdf"
    return render_template("index.html", poster_path=poster_path)
@app.route("/api/readings/<sensor_type>", methods=['POST'])
def post_reading(sensor_type):
    if sensor_type not in data_store:
        return jsonify({"error":"unknown sensor type"}), 400
    payload = request.get_json()
    if not payload:
        return jsonify({"error":"invalid json"}), 400
    add_reading(sensor_type, payload)
    return jsonify({"status":"ok"}), 201
@app.route("/api/latest")
def api_latest():
    result = {}
    for k, dq in data_store.items():
        result[k] = list(dq)[-1] if len(dq) else None
    return jsonify(result)
@app.route("/api/history/<sensor_type>")
def api_history(sensor_type):
    if sensor_type not in data_store:
        return jsonify({"error":"unknown sensor type"}), 400
    limit = int(request.args.get("limit", 100))
    return jsonify(list(data_store[sensor_type])[-limit:])
_sim_thread = None
_sim_lock = threading.Lock()
def sensor_simulator_loop(interval=2.0):
    while True:
        pm25 = max(0, random.gauss(60, 35))         
        co2 = max(300, random.gauss(800, 250))
        atemp = round(random.uniform(20, 32), 1)
        add_reading("air", {"pm25": round(pm25,1), "co2": int(co2), "temp": atemp})
        ph = round(random.gauss(7.4, 0.5), 2)
        turb = max(0, random.gauss(20, 15))
        wtemp = round(random.uniform(16, 30), 1)
        add_reading("water", {"ph": ph, "turbidity": int(turb), "temp": wtemp})
        db = max(30, random.gauss(60, 18))
        add_reading("noise", {"db": int(db)})
        time.sleep(interval)
@app.route("/start_simulator", methods=['GET'])
def start_simulator():
    global _sim_thread
    with _sim_lock:
        if _sim_thread and _sim_thread.is_alive():
            return "Simulator already running", 200
        _sim_thread = threading.Thread(target=sensor_simulator_loop, daemon=True)
        _sim_thread.start()
        return "Simulator started", 200
@app.route("/simulate_event/<event>", methods=['POST'])
def simulate_event(event):
    if event == "pm25_spike":
        for i in range(6):
            add_reading("air", {"pm25": 200 + i*10, "co2": 1500, "temp": 30})
        return "pm25 spike injected", 200
    if event == "water_pollution":
        for i in range(4):
            add_reading("water", {"ph": 5.4, "turbidity": 120, "temp": 28})
        return "water pollution injected", 200
    return "unknown event", 400
if __name__ == "__main__":
    threading.Thread(target=sensor_simulator_loop, daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=5000)
