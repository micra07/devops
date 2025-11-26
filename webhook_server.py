#!/usr/bin/env python3
"""
Webhook сервер для автоматического развертывания catty-reminders-app
"""
#6try
import tempfile
import subprocess
import os
import json
import hashlib
import hmac
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

# Конфигурация
PORT = 8080
APP_PORT = 8181
APP_DIR = "/home/ubuntu/catty-app"  # Папка где будет развернуто приложение

class WebhookHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        """Обработка POST запросов от GitHub"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode('utf-8'))
            self._process_webhook(payload)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')

        except json.JSONDecodeError:
            print("Ошибка парсинга JSON")
            self.send_response(400)
            self.end_headers()

    def do_GET(self):
        """Простая страница статуса"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Catty App Webhook Server</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }}
                .container {{ background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #4d90cd; text-align: center; }}
                .info {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .success {{ background-color: #d4edda; color: #155724; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1> Catty App Webhook Server</h1>
                <div class="info">
                    <p><strong>Статус:</strong> Сервер активен и ожидает webhook события</p>
                    <p><strong>Время запуска:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p><strong>Webhook порт:</strong> {PORT}</p>
                    <p><strong>Приложение порт:</strong> {APP_PORT}</p>
                </div>
                <div class="status success">
                    <p><strong>Приложение доступно по адресу:</strong> http://app.{os.environ.get('ID', 'your-id')}.{os.environ.get('PROXY', 'course.prafdin.ru')}</p>
                </div>
                <p>Этот сервер автоматически развертывает приложение Catty Reminders при каждом push в репозиторий.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def _process_webhook(self, payload):
        """Обработка webhook события"""
        event_type = self.headers.get('X-GitHub-Event', 'unknown')
        repo_name = payload.get('repository', {}).get('full_name', 'unknown')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\nПолучено webhook событие:")
        print(f"   Время: {timestamp}")
        print(f"   Тип события: {event_type}")
        print(f"   Репозиторий: {repo_name}")

        if event_type == 'push':
            self._handle_push_event(payload)
        else:
            print(f"  Событие '{event_type}' - только логирование")

    def _handle_push_event(self, payload):
        """Обработка push события - автоматическое развертывание"""
        branch = payload.get('ref', '').replace('refs/heads/', '')
        clone_url = payload.get('repository', {}).get('clone_url', '')
        commits = payload.get('commits', [])

        print(f"   Push в ветку: {branch}")
        print(f"   Коммитов: {len(commits)}")

        # АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ
        print(f"   ЗАПУСКАЕМ АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ:")

        try:
            # 1. Останавливаем текущее приложение
            print(f"      - Останавливаем текущее приложение...")
            subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)

            # 2. Обновляем код
            print(f"  - Обновляем код из репозитория...")
            if os.path.exists(APP_DIR):
                # Если папка уже существует, делаем pull
                result = subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=APP_DIR,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"   Ошибка при pull: {result.stderr}")
                    return
                print(f"   Код обновлен (git pull)")
            else:
                # Если папки нет, делаем clone
                result = subprocess.run(
                    ["git", "clone", clone_url, APP_DIR],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"     Ошибка при clone: {result.stderr}")
                    return
                print(f"      Репозиторий склонирован")

            # 3. Переходим в нужную ветку
            result = subprocess.run(
                ["git", "checkout", branch],
                cwd=APP_DIR,
                capture_output=True,
                text=True
            )
            print(f"     Переключено на ветку: {branch}")

            # 4. Устанавливаем зависимости в виртуальном окружении
            print(f"      - Устанавливаем зависимости в виртуальном окружении...")
            
            # Создаем venv если не существует
            venv_path = os.path.join(APP_DIR, "venv")
            if not os.path.exists(venv_path):
                result = subprocess.run(
                    ["python3", "-m", "venv", "venv"],
                    cwd=APP_DIR,
                    capture_output=True,
                    text=True
                )
                print(f"     Виртуальное окружение создано")

            # Устанавливаем зависимости через venv pip
            pip_path = os.path.join(APP_DIR, "venv/bin/pip")
            result = subprocess.run(
                [pip_path, "install", "-r", "requirements.txt"],
                cwd=APP_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"     Зависимости установлены")
            else:
                print(f"    Возможные проблемы с зависимостями: {result.stderr}")

            # 5. Запускаем приложение в фоне через venv
            print(f"   - Запускаем приложение...")
            uvicorn_path = os.path.join(APP_DIR, "venv/bin/uvicorn")
            process = subprocess.Popen(
                [uvicorn_path, "app.main:app", "--host", "0.0.0.0", "--port", str(APP_PORT)],
                cwd=APP_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Даем время на запуск
            import time
            time.sleep(3)
            
            # Проверяем что процесс запущен
            if process.poll() is None:
                print(f"    Приложение запущено на порту {APP_PORT}")
                
                # Сохраняем PID для возможности управления
                with open("/tmp/catty-app.pid", "w") as f:
                    f.write(str(process.pid))
            else:
                stdout, stderr = process.communicate()
                print(f"    Ошибка запуска приложения: {stderr.decode()}")
                return

            print(f"    АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ УСПЕШНО ЗАВЕРШЕНО!")
            print(f"  Приложение доступно по: http://app.{os.environ.get('ID', 'your-id')}.{os.environ.get('PROXY', 'course.prafdin.ru')}")

        except Exception as e:
            print(f"  КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")

def main():
    """Запуск webhook сервера"""
    print(f" Запуск Catty App Webhook Server")
    print(f" Webhook порт: {PORT}")
    print(f" App порт: {APP_PORT}")
    print(f" Директория приложения: {APP_DIR}")
    print(f" Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n Ожидание webhook событий от GitHub...")
    print(f" Для остановки: Ctrl+C\n")

    # Создаем директорию для приложения если её нет
    os.makedirs(APP_DIR, exist_ok=True)

    try:
        server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n Сервер остановлен")

if __name__ == '__main__':
    main()
