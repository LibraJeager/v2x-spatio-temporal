import paho.mqtt.client as mqtt
import json
import xgboost as xgb
import numpy as np
import xml.etree.ElementTree as ET
from collections import deque

BROKER_ADDRESS = "v2x-broker"
PORT = 1883
TOPIC = "v2x/telemetry/raw"

# --- 1. TẢI BẢN ĐỒ KHÔNG GIAN ---
print("[RSU] Đang nạp Bản đồ Không gian (osm.net.xml)...")
def build_topology(net_xml_path):
    tree = ET.parse(net_xml_path)
    incoming, outgoing = {}, {}
    for conn in tree.getroot().findall('connection'):
        from_edge, to_edge = conn.get('from'), conn.get('to')
        from_lane_idx, to_lane_idx = conn.get('fromLane'), conn.get('toLane')
        if not (from_edge and to_edge and from_lane_idx and to_lane_idx): continue
        from_lane, to_lane = f"{from_edge}_{from_lane_idx}", f"{to_edge}_{to_lane_idx}"
        outgoing.setdefault(from_lane, []).append(to_lane)
        incoming.setdefault(to_lane, []).append(from_lane)
    return incoming, outgoing

incoming_map, outgoing_map = build_topology('osm.net.xml')

# --- 2. TẢI MÔ HÌNH TRÍ TUỆ NHÂN TẠO ---
print("[RSU] Đang nạp Ký ức AI (veeps_spatio_temporal.json)...")
model = xgb.XGBRegressor()
model.load_model('veeps_spatio_temporal.json')

# --- 3. BỘ NHỚ THỜI GIAN (5 PHÚT = 300 GIÂY) ---
# Dùng cấu trúc 'deque' để lưu tối đa 300 giá trị fdr_mean gần nhất cho mỗi làn đường
MEMORY_WINDOW = 300
fdr_memory = {} 
current_timestep = "-1"
vehicle_states = {}

# Hằng số vật lý
V_MAX = 14.0
T_REACT = 1.5
EPSILON = 0.2
D_OPT = (V_MAX * T_REACT) + EPSILON

def predict_future_traffic(timestep):
    if not vehicle_states: return

    # 1. Nhóm xe theo làn và tính Tính năng Cơ bản (vehicle_count, v_mean, fdr_mean)
    lane_stats = {}
    for vid, data in vehicle_states.items():
        lane = data["lane"]
        lane_stats.setdefault(lane, []).append(data)

    current_fdr = {}
    features_batch = []
    lane_order = []

    for lane, cars in lane_stats.items():
        if len(cars) < 2: continue
        
        cars.sort(key=lambda x: x["pos"], reverse=True)
        fdr_list, total_speed = [], 0
        for i in range(len(cars) - 1):
            d_real = cars[i]["pos"] - cars[i+1]["pos"]
            if d_real > 0:
                fdr_list.append(d_real / D_OPT)
            total_speed += cars[i]["speed"]
            
        if fdr_list:
            v_mean = total_speed / len(cars)
            fdr_mean = sum(fdr_list) / len(fdr_list)
            current_fdr[lane] = fdr_mean
            
            # Cập nhật Bộ nhớ 5 phút
            if lane not in fdr_memory:
                fdr_memory[lane] = deque(maxlen=MEMORY_WINDOW)
            fdr_memory[lane].append(fdr_mean)
            
            # Tính Tính năng Thời gian (Temporal)
            fdr_med = np.median(fdr_memory[lane])
            fdr_std = np.std(fdr_memory[lane]) if len(fdr_memory[lane]) > 1 else 0.0
            
            # Tính Tính năng Không gian (Spatial)
            in_lanes = incoming_map.get(lane, [])
            out_lanes = outgoing_map.get(lane, [])
            
            fdr_in = np.mean([current_fdr.get(l, 1.0) for l in in_lanes]) if in_lanes else 1.0
            fdr_out = np.mean([current_fdr.get(l, 1.0) for l in out_lanes]) if out_lanes else 1.0
            
            # Đóng gói Features: ['vehicle_count', 'v_mean', 'fdr_mean', 'FDR_in', 'FDR_out', 'FDR_med', 'FDR_std']
            features_batch.append([len(cars), fdr_mean, fdr_in, fdr_out, fdr_med, fdr_std])
            lane_order.append(lane)

    # 2. Suy luận AI (AI Inference)
    if features_batch:
        X_infer = np.array(features_batch)
        predictions = model.predict(X_infer)
        
        # 3. Phát cảnh báo
        for i, lane in enumerate(lane_order):
            future_spi = predictions[i]
            # Nếu dự báo SPI < 0.4 (Tốc độ tương lai nhỏ hơn 40% tốc độ tối đa -> Kẹt xe nặng)
            if future_spi < 0.4:
                print(f"[🚨 CẢNH BÁO T={timestep}s] Làn {lane} - Nguy cơ kẹt xe nặng sau 15 phút! (SPI: {future_spi*100:.1f}%)")

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[RSU Node] Kết nối MQTT thành công. Hệ thống AI VEEPS đã kích hoạt!")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global current_timestep, vehicle_states
    payload = json.loads(msg.payload.decode("utf-8"))
    msg_time = payload["timestep"]
    
    if msg_time != current_timestep:
        if current_timestep != "-1":
            predict_future_traffic(current_timestep)
        current_timestep = msg_time
        vehicle_states = {} 
        
    vehicle_states[payload["vehicle_id"]] = payload

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="rsu_ai_node")
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_ADDRESS, PORT, 60)
client.loop_forever()
