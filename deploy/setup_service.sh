#!/bin/bash
# Script hỗ trợ triển khai FollowUpAgent thành Background Service

echo "[*] Đang copy cấu hình service vào /etc/systemd/system/..."
sudo cp followup-agent.service /etc/systemd/system/

echo "[*] Đang nạp lại systemd daemon..."
sudo systemctl daemon-reload

echo "[*] Bật tính năng khởi động cùng hệ thống..."
sudo systemctl enable followup-agent.service

echo "[*] Đang khởi động service..."
sudo systemctl restart followup-agent.service

echo "[*] Trạng thái hiện tại của service:"
sudo systemctl status followup-agent.service --no-pager
