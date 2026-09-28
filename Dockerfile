# Base image CUDA 11.8 hỗ trợ dải GPU rộng nhất (từ Tesla P100 sm_60 đến L4/A100/H100)
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Cài đặt Python 3.11, trình biên dịch C++ và thư viện audio
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

COPY requirements.txt .

# 1. Cài đặt PyTorch CUDA 11.8 (hỗ trợ sm_60 cho P100 và các GPU mới hơn)
# 2. Biên dịch llama-cpp-python với tất cả kiến trúc phổ biến:
#    60 (P100), 70 (V100), 75 (T4/RTX 20xx), 80 (A100), 86 (RTX 30xx), 89 (L4/RTX 40xx)
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir torch==2.1.2+cu118 torchaudio==2.1.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118 && \
    CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=60;70;75;80;86;89" FORCE_CMAKE=1 pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
