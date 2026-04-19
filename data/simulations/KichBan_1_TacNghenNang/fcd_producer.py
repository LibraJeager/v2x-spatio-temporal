import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt
import json
import time

# Cấu hình kết nối
BROKER_ADDRESS = "192.168.140.128" # Hãy kiểm tra lại IP Linux nếu cần
PORT = 1883
TOPIC = "v2x/telemetry/raw"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sumo_fcd_producer")
client.connect(BROKER_ADDRESS, PORT, 60)

# 🚨 CỰC KỲ QUAN TRỌNG: Kích hoạt luồng chạy ngầm để giải phóng bộ đệm mạng
client.loop_start()

def stream_massive_fcd(xml_file):
    print(f"Bắt đầu stream dữ liệu siêu tốc từ {xml_file}...")
    
    # Kỹ thuật bóc tách Root Node để chống tràn RAM 100%
    context = iter(ET.iterparse(xml_file, events=('start', 'end')))
    _, root = next(context) # Bắt lấy thẻ gốc (Root)
    
    for event, elem in context:
        if event == 'end' and elem.tag == 'timestep':
            current_time = elem.attrib.get('time')
            
            for vehicle in elem.findall('vehicle'):
                payload = {
                    "timestep": current_time,
                    "vehicle_id": vehicle.attrib.get('id'),
                    "speed": round(float(vehicle.attrib.get('speed', 0.0)), 2),
                    "lane": vehicle.attrib.get('lane', ''),
                    "pos": round(float(vehicle.attrib.get('pos', 0.0)), 2)
                }
                client.publish(TOPIC, json.dumps(payload))
            
            # 1. Dọn dẹp thẻ hiện tại
            elem.clear()
            # 2. 🚨 Dọn dẹp thẻ gốc (Giải phóng RAM thực sự)
            root.clear()
            
            # 3. Kỹ thuật "Hãm phanh mạng": Nhấp nhả 0.005s cho mỗi timestep 
            # để máy Linux kịp nuốt dữ liệu, tránh làm nổ buffer MQTT
            time.sleep(0.005)

if __name__ == "__main__":
    try:
        stream_massive_fcd("fcd_data.xml")
    except KeyboardInterrupt:
        print("\nĐã ép dừng tiến trình an toàn (Ctrl + C)!")
    finally:
        client.loop_stop() # Đóng luồng mạng sạch sẽ
        print("Đường ống streaming đã đóng.")