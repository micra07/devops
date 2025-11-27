#!/usr/bin/env python3
"""
Webhook сервер для автоматического развертывания catty-reminders-app
Использует FastAPI вместо BaseHTTPRequestHandler
"""
# morning test8
from fastapi import FastAPI, Request, Response
import subprocess
import os
import json
from datetime import datetime

# Конфигурация
WEBHOOK_PORT = 8080
APP_PORT = 8181
APP_DIR = "/home/vboxuser/catty-app"
REPO_URL = "https://github.com/micra07/devops.git"

app = FastAPI(title="Catty App Webhook Server")

@app.post("/")
async def webhook(request: Request):
    """Обработка webhook событий от GitHub"""
    
    # Получаем данные webhook
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    
    # Логируем событие
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repo_name = payload.get('repository', {}).get('full_name', 'unknown')
    branch = payload.get('ref', '').replace('refs/heads/', '')
    commits = payload.get('commits', [])
    
    print(f"\n🔔 Получено webhook событие:")
    print(f"   Время: {timestamp}")
    print(f"   Тип события: {event_type}")
    print(f"   Репозиторий: {repo_name}")
    print(f"   📝 Push в ветку: {branch}")
    print(f"   📊 Коммитов: {len(commits)}")
    
    # Обрабатываем только push события
    if event_type == "push":
        await _handle_push_event(branch)
    
    return Response(status_code=200)

@app.get("/")
async def health():
    """Страница статуса"""
    return {
        "status": "ok", 
        "service": "Catty App Webhook Server",
        "timestamp": datetime.now().isoformat(),
        "webhook_port": WEBHOOK_PORT,
        "app_port": APP_PORT,
        "app_url": f"http://app.{os.environ.get('ID', 'your-id')}.{os.environ.get('PROXY', 'course.prafdin.ru')}"
    }

async def _handle_push_event(branch: str):
    """Обработка push события - автоматическое развертывание"""
    print(f"   🚀 ЗАПУСКАЕМ АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ:")
    
    try:
        # 1. Останавливаем приложение
        print(f"      - Останавливаем приложение...")
        result = subprocess.run(
            ["sudo", "systemctl", "stop", "catty-app.service"],
            capture_output=True,
            text=True
        )
        
        # 2. Обновляем код
        print(f"      - Обновляем код из репозитория...")
        if not os.path.exists(APP_DIR):
            os.makedirs(APP_DIR, exist_ok=True)
        
        os.chdir(APP_DIR)
        
        # Проверяем это git репозиторий
        if os.path.exists(os.path.join(APP_DIR, ".git")):
            # Делаем pull если это git репозиторий
            subprocess.run(["git", "fetch"], capture_output=True)
            subprocess.run(["git", "checkout", branch], capture_output=True)
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"      ✅ Код обновлен (git pull)")
            else:
                print(f"      ❌ Ошибка при pull: {result.stderr}")
                return
        else:
            # Клонируем если это не git репозиторий
            result = subprocess.run(
                ["git", "clone", REPO_URL, APP_DIR],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"      ✅ Репозиторий склонирован")
                os.chdir(APP_DIR)
                subprocess.run(["git", "checkout", branch], capture_output=True)
            else:
                print(f"      ❌ Ошибка при clone: {result.stderr}")
                return

        # 3. Устанавливаем зависимости в виртуальном окружении
        print(f"      - Устанавливаем зависимости...")
        venv_path = os.path.join(APP_DIR, "venv")
        if not os.path.exists(venv_path):
            result = subprocess.run(
                ["python3", "-m", "venv", "venv"],
                capture_output=True,
                text=True
            )
            print(f"      ✅ Виртуальное окружение создано")

        # Устанавливаем зависимости через venv pip
        pip_path = os.path.join(APP_DIR, "venv/bin/pip")
        result = subprocess.run(
            [pip_path, "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"      ✅ Зависимости установлены")
        else:
            print(f"      ⚠️  Проблемы с зависимостями: {result.stderr}")

        # 4. Запускаем приложение через systemd
        print(f"      - Запускаем приложение через systemd...")
        result = subprocess.run(
            ["sudo", "systemctl", "start", "catty-app.service"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"      ✅ Systemd сервис запущен")
            
            # Даем время на запуск
            import time
            time.sleep(3)
            
            # Проверяем статус
            status_result = subprocess.run(
                ["sudo", "systemctl", "is-active", "catty-app.service"],
                capture_output=True,
                text=True
            )
            if status_result.stdout.strip() == "active":
                print(f"      ✅ Приложение активно на порту {APP_PORT}")
                print(f"      🎉 АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ УСПЕШНО!")
                print(f"      🌐 Приложение доступно по: http://app.{os.environ.get('ID', 'ushakov')}.{os.environ.get('PROXY', 'course.prafdin.ru')}")
            else:
                print(f"      ❌ Приложение не запустилось")
        else:
            print(f"      ❌ Ошибка запуска: {result.stderr}")

    except Exception as e:
        print(f"      ❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print(f"🚀 Запуск Catty App Webhook Server")
    print(f"📡 Webhook порт: {WEBHOOK_PORT}")
    print(f"🌐 App порт: {APP_PORT}")
    print(f"📁 Директория приложения: {APP_DIR}")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n👀 Ожидание webhook событий от GitHub...")
    print(f"💡 Для остановки: Ctrl+C\n")
    
    uvicorn.run(app, host="0.0.0.0", port=WEBHOOK_PORT)
