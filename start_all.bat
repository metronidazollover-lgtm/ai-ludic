@echo off
echo ==========================================
echo    AI-Trader One-Click Launcher
echo ==========================================

echo [1/3] Запуск Docker контейнеров...
docker-compose up -d

echo [2/3] Ожидание запуска API (10 секунд)...
timeout /t 10 /nobreak > nul

echo [3/3] Запуск Автономного Торгового Агента...
echo Скрипт агента откроется в новом окне для мониторинга.
start "AI-Trader Autonomous Agent" cmd /k "python agent_autonomous.py"

echo ==========================================
echo Система запущена! 
echo Дашборд: http://localhost:3000
echo Бэкенд API: http://localhost:8888
echo ==========================================
pause
