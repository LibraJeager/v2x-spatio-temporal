import xml.etree.ElementTree as ET
import csv
from collections import defaultdict

# --- HẰNG SỐ VẬT LÝ V2X ---
V_MAX = 14.0       
T_REACT = 1.5      
EPSILON = 0.2      
D_OPT = (V_MAX * T_REACT) + EPSILON  

def process_single_xml_to_csv(xml_input, csv_output):
    print(f"\n🚀 Bắt đầu vắt kiệt {xml_input} -> {csv_output}...")

    # Mở file CSV để ghi luồng (Streaming Write)
    with open(csv_output, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['timestep', 'lane_id', 'vehicle_count', 'v_mean', 'fdr_mean'])

        # Đọc luồng XML (Streaming Read) - Chống tràn RAM 100%
        context = iter(ET.iterparse(xml_input, events=('start', 'end')))
        _, root = next(context)

        processed_steps = 0

        for event, elem in context:
            if event == 'end' and elem.tag == 'timestep':
                t_val = float(elem.attrib.get('time'))
                t_int = int(t_val)

                lane_data = defaultdict(list)

                # Bốc dữ liệu xe trong 1 giây
                for vehicle in elem.findall('vehicle'):
                    lane = vehicle.attrib.get('lane')
                    if lane.startswith(':'): 
                        continue # Bỏ qua xe đang kẹt giữa ngã tư ảo
                        
                    speed = float(vehicle.attrib.get('speed', 0.0))
                    pos = float(vehicle.attrib.get('pos', 0.0))
                    lane_data[lane].append({'speed': speed, 'pos': pos})

                # Tính toán FDR cho từng làn
                for lane, cars in lane_data.items():
                    count = len(cars)
                    if count < 2: continue # Cần ít nhất 2 xe nối đuôi nhau

                    cars.sort(key=lambda x: x['pos'], reverse=True)
                    total_speed = 0
                    fdr_list = []

                    for i in range(count - 1):
                        d_real = cars[i]['pos'] - cars[i+1]['pos']
                        if d_real > 0:
                            fdr_list.append(d_real / D_OPT)
                        total_speed += cars[i]['speed']

                    total_speed += cars[-1]['speed']

                    if fdr_list:
                        v_mean = total_speed / count
                        fdr_mean = sum(fdr_list) / len(fdr_list)
                        
                        # Ghi thẳng xuống ổ cứng
                        writer.writerow([t_int, lane, count, round(v_mean, 3), round(fdr_mean, 3)])

                # 🚨 XÓA TRÍ NHỚ (Giữ RAM luôn ở mức 20MB)
                elem.clear()
                root.clear()

                processed_steps += 1
                if processed_steps % 1000 == 0:
                    print(f"⏳ Đã xử lý {processed_steps} giây của {xml_input}...")

    print(f"✅ HOÀN TẤT! Đã xuất thành công: {csv_output}")

if __name__ == "__main__":
    # --- DANH SÁCH 4 FILE CỦA BẠN ---
    # Thay đổi tên file XML ở cột bên trái cho đúng với tên file bạn đã lưu
    scenarios = [
        ("fcd_data.xml", "dataset_kb1.csv"),
        ("fcd_data_kb2.xml", "dataset_kb2.csv"),
        ("fcd_data_kb3.xml", "dataset_kb3.csv"),
        ("fcd_data_kb4.xml", "dataset_kb4.csv")
    ]

    for xml_in, csv_out in scenarios:
        try:
            process_single_xml_to_csv(xml_in, csv_out)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file {xml_in}. Vui lòng kiểm tra lại tên file!")
            
    print("\n🎉 Toàn bộ quá trình trích xuất đã xong. Sẵn sàng nạp vào AI!")