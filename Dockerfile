# Sử dụng base image có sẵn CUDA 12.1.1 (phù hợp với GPU L4) và cuDNN để hỗ trợ tính toán bằng GPU NVIDIA
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Cấu hình tránh tương tác dòng lệnh khi cài đặt thư viện hệ thống
ENV DEBIAN_FRONTEND=noninteractive

# Cài đặt Python 3.11, trình biên dịch C++ (để build llama-cpp) và các gói hỗ trợ audio (ffmpeg, libsndfile1)
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập python3.11 làm mặc định
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

COPY requirements.txt .

# Nâng cấp pip và cài đặt thư viện
# Quan trọng: Cờ CMAKE_ARGS="-DGGML_CUDA=on" ép llama-cpp-python biên dịch mã nguồn hỗ trợ nhân CUDA
RUN python -m pip install --upgrade pip && \
    CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Mở port cho FastAPI
EXPOSE 8000

# Chạy server (trỏ đúng đường dẫn app.main)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
