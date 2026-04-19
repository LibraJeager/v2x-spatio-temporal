import xml.etree.ElementTree as ET
import paho.mqtt.client as mqtt
import json
import time

# Cấu hình kết nối tới Message Broker (Mosquitto trong Docker)
BROKER_ADDRESS = "192.168.140.128"
PORT = 1883
TOPIC = "v2x/telemetry/raw"

# Khởi tạo kết nối MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sumo_fcd_producer")
client.connect(BROKER_ADDRESS, PORT, 60)

def stream_massive_fcd(file_path):
    print(f"Đang mở file Big Data {file_path} để stream...")
    print("Bắt đầu phát dữ liệu lên mạng lưới V2X... (Nhấn Ctrl+C để dừng)")
    
    # iterparse là "phép thuật" của DE để đọc file khổng lồ mà không tốn RAM
    context = ET.iterparse(file_path, events=('start', 'end'))
    
    current_time = "0.0"

    try:
        for event, elem in context:
            # Bắt được mốc thời gian (timestep) mới
            if event == 'start' and elem.tag == 'timestep':
                current_time = elem.attrib.get('time', "0.0")
                
                # Cứ mỗi giây mô phỏng (timestep), ta cho script ngủ một chút
                # để tạo cảm giác dữ liệu đang chảy theo thời gian thực (real-time)
                # time.sleep(0.05) 
                
            # Bắt được dữ liệu của một chiếc xe trong timestep đó
            elif event == 'end' and elem.tag == 'vehicle':
                payload = {
    			"timestep": current_time,
    			"vehicle_id": elem.attrib.get('id'),
   			"speed": round(float(elem.attrib.get('speed', 0.0)), 2),
    			"lane": elem.attrib.get('lane', ''),  # Lấy ID làn đường
    			"pos": round(float(elem.attrib.get('pos', 0.0)), 2) # Lấy vị trí trên làn
		}
                
                # Bắn dữ liệu lên không gian mạng MQTT
                client.publish(TOPIC, json.dumps(payload))
                
                # Tùy chọn in ra màn hình (Nên tắt đi nếu muốn chạy tốc độ cao)
                # print(f"[PUBLISHED] T={current_time}s | {payload['vehicle_id']} | Speed: {payload['speed']}")
                
                # ĐIỂM CỐT LÕI CỦA BIG DATA: Xóa phần tử khỏi RAM ngay sau khi xử lý xong!
                elem.clear()
                
    except KeyboardInterrupt:
        print("\nĐã ngắt luồng dữ liệu.")
    finally:
        client.disconnect()

# Chạy hệ thống
if __name__ == "__main__":
    # Điền đúng tên file 5GB của bạn vào đây
    stream_massive_fcd("fcd_data_kb3.xml")