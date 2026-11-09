# 🧠 Bài Học Từ Việc Cài PyTorch + PhoWhisper Trên Managed Server

> **Môi trường**: HPC Server (`ood-master`) — Không có quyền `sudo/root` — GPU Tesla P100 (SM 6.0) — Python 3.12 hệ thống

---

## 📋 Tóm tắt nhanh: Công thức đúng để cài PyTorch trên Managed Server có GPU cũ

```bash
# 1. Cài Miniconda (không cần root)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
source $HOME/miniconda/bin/activate

# 2. Tạo môi trường với Python 3.11
conda create -n p100_gpu python=3.11 -y
conda activate p100_gpu

# 3. Cài PyTorch ĐÚNG version cho GPU SM 6.0 — PHẢI dùng pip, KHÔNG dùng conda
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# 4. Cài các công cụ hệ thống (ffmpeg, etc.) qua conda-forge (không cần root)
conda install -c conda-forge ffmpeg -y

# 5. Ép NumPy xuống bản 1.x để tương thích PyTorch 2.1.2
pip install "numpy<2"

# 6. Cài các thư viện AI
pip install transformers==4.38.2 librosa soundfile
```

---

## 🚨 Danh Sách Lỗi Từng Gặp & Cách Giải Quyết

### Lỗi 1: `ModuleNotFoundError: No module named 'transformers'`
**Nguyên nhân**: Python hệ thống (system Python) không có thư viện này.  
**Sai lầm**: Cố chạy `pip install` vào Python hệ thống.  
**Bài học**: Trên managed server, **không bao giờ** cài thư viện vào Python hệ thống. Phải dùng virtual environment hoặc Conda.  
**Fix**: Tạo môi trường ảo với Conda trước, rồi mới cài.

---

### Lỗi 2: `externally-managed-environment` (PEP 668)
```
This environment is externally managed
To install Python packages system-wide, try apt install python3-xyz
```
**Nguyên nhân**: Debian/Ubuntu hiện đại bảo vệ Python hệ thống, không cho `pip install` lung tung.  
**Bài học**: Đây là tín hiệu bắt buộc phải dùng Conda hoặc venv. Đừng cố `--break-system-packages`.  
**Fix**: Cài Miniconda → tạo Conda environment.

---

### Lỗi 3: Không có `python3.11` và không có `sudo`
```
Command 'python3.11' not found
E: Unable to acquire the dpkg frontend lock — are you root?
```
**Nguyên nhân**: Server lock hoàn toàn, không có quyền Admin.  
**Bài học**: Không cần `sudo` nếu dùng **Miniconda**. Conda tự quản lý Python version riêng biệt trong `~/miniconda` mà không đụng vào hệ thống.  
**Fix**: Dùng Miniconda → `conda create -n env_name python=3.11`.

---

### Lỗi 4: Không có `docker`
```
Command 'docker' not found
snap install docker  # cần root
apt install docker.io  # cần root
```
**Nguyên nhân**: Server HPC thường cấm Docker vì lý do bảo mật.  
**Bài học**: Trên managed HPC server, đừng kỳ vọng có Docker. **Conda là thay thế tốt nhất**.  
**Fix**: Dùng Conda thay vì Docker.

---

### Lỗi 5: `ERROR: Could not find a version that satisfies the requirement torch==2.1.2`
**Nguyên nhân**: Conda mặc định tạo môi trường với Python mới nhất (3.14!). PyTorch 2.1.2 không có wheel cho Python 3.14.  
**Bài học**: **Luôn chỉ định version Python khi tạo Conda environment**. Đừng để mặc định.  
```bash
# SAI:
conda create -n myenv -y  # Sẽ dùng Python mới nhất (3.13, 3.14...)

# ĐÚNG:
conda create -n myenv python=3.11 -y  # Chỉ định rõ Python version
```

---

### Lỗi 6: `Tesla P100-PCIE-16GB with CUDA capability sm_60 is not compatible`
**Nguyên nhân**: GPU Tesla P100 có kiến trúc cũ (SM 6.0 / Pascal). Các bản PyTorch mới (2.2+, 2.11 qua Conda) không còn build kernel cho SM 6.0 nữa.  
**Bài học**: Phải kiểm tra compatibility của GPU trước khi cài PyTorch.

| GPU | Compute Capability | PyTorch tương thích |
|---|---|---|
| Tesla P100 | SM 6.0 | ≤ 2.1.x (cu118) |
| RTX 3090 | SM 8.6 | 2.x, 2.1, 2.2... |
| RTX 4090 | SM 8.9 | 2.x trở lên |
| A100 | SM 8.0 | 2.x trở lên |

**Fix**: Dùng `pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118`

---

### Lỗi 7: `ImportError: undefined symbol: iJIT_NotifyEvent`
```
ImportError: …/libtorch_cpu.so: undefined symbol: iJIT_NotifyEvent
```
**Nguyên nhân**: Build PyTorch qua `conda install pytorch -c pytorch -c nvidia` kéo bản PyTorch quá mới (2.11) với CUDA 13.0, bản này compiled với VTune của Intel nhưng server thiếu thư viện `libittnotify`.  
**Bài học**: Khi `conda install pytorch` mà bị lỗi `iJIT_NotifyEvent`, **đừng cố vá**, hãy uninstall và chuyển sang dùng `pip` với URL của PyTorch:
```bash
conda remove pytorch torchvision torchaudio -y
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

---

### Lỗi 8: `[transformers] Disabling PyTorch because PyTorch >= 2.5 is required`
**Nguyên nhân**: `pip install transformers` mặc định tải bản mới nhất (5.x). Bản 5.x đòi PyTorch ≥ 2.5, nhưng mình bị kẹt ở PyTorch 2.1.2.  
**Bài học**: Khi bị kẹt ở một version PyTorch cụ thể, phải cài `transformers` đúng version tương thích:
```bash
pip install transformers==4.38.2  # Compatible với PyTorch 2.1.x
```

---

### Lỗi 9: `ValueError: ffmpeg was not found but is required`
**Nguyên nhân**: `transformers` dùng `ffmpeg` để đọc audio file, nhưng trên server không có (và không thể `apt install ffmpeg` vì thiếu quyền root).  
**Bài học**: `ffmpeg` là **system-level tool**, pip không cài được. Dùng Conda:
```bash
conda install -c conda-forge ffmpeg -y
```
Đây chính là ưu điểm lớn của Conda: cài được cả **non-Python tools** mà không cần root.

---

### Lỗi 10: `NumPy 2.x` không tương thích
```
A module compiled using NumPy 1.x cannot be run in NumPy 2.4.6
UserWarning: Failed to initialize NumPy: _ARRAY_API not found
```
**Nguyên nhân**: PyTorch 2.1.2 được build với NumPy 1.x. Khi cài thêm `librosa`, `soundfile` qua pip, nó tự động kéo NumPy 2.x về, gây xung đột.  
**Bài học**: Khi dùng PyTorch 2.1.x, phải ép NumPy ở bản 1.x:
```bash
pip install "numpy<2"
```

---

## 🏁 Kiểm Tra Cuối Cùng — Môi Trường Sạch

Sau khi cài xong, chạy script này để verify mọi thứ đều ổn:

```python
import torch, numpy as np
from transformers import pipeline

print(f"PyTorch: {torch.__version__}")
print(f"NumPy: {np.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU Capability: {torch.cuda.get_device_capability(0)}")

# Kết quả mong đợi:
# PyTorch: 2.1.2+cu118
# NumPy: 1.x.x  <-- phải là 1.x
# CUDA available: True
# GPU: Tesla P100-PCIE-16GB
# GPU Capability: (6, 0)
```

---

## 💡 Nguyên Tắc Vàng Cho Managed Server

| Tình huống | Nên làm |
|---|---|
| Cần Python version cụ thể | `conda create -n env python=3.11` |
| Cài thư viện Python | `pip install` trong Conda env |
| Cài công cụ hệ thống (ffmpeg, git-lfs...) | `conda install -c conda-forge ten_cong_cu` |
| GPU cũ (P100, V100, K80) | PyTorch ≤ 2.1.2 + `cu118` |
| Version conflict | Chỉ định rõ version: `pip install X==1.2.3` |
| `conda install` bị lỗi runtime | Thử lại với `pip install` từ PyTorch index URL |

