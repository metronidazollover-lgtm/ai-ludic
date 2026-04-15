@echo off
echo [INFO] Starting AI-Trader Development Cluster...
cd service/server
start "Sniper Backend" python main.py
cd ../../web-ui
start "Sniper Web UI" npm run dev
echo [SUCCESS] Both services are starting in separate windows.
