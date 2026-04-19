# Sử dụng Python 3.9 làm nền móng
FROM python:3.9-slim

# Đặt thư mục làm việc mặc định trong container
WORKDIR /app

# CÀI ĐẶT 1 LẦN DUY NHẤT LÚC BUILD HÌNH ẢNH
RUN pip install --no-cache-dir paho-mqtt xgboost scikit-learn pandas tqdm

# Lệnh mặc định khi container chạy (Đã bỏ phần pip install đi)
CMD ["python", "-u", "edge_processor.py"]
