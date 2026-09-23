# SmartSchedule AI

FastAPI-приложение для подготовки и генерации учебного расписания. Frontend
раздаётся тем же приложением, поэтому локально API и интерфейс доступны на
одном адресе.

## Требования

- Python 3.11+
- PostgreSQL для production (локально можно использовать существующую
  совместимую базу, указанную в `DATABASE_URL`)

## Локальный запуск

Из корня проекта:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/smartschedule"
$env:APP_ENV = "development"
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Откройте <http://127.0.0.1:8000/>. Не открывайте HTML двойным щелчком:
`file://` не является заменой запущенному API.

## Миграции

Перед запуском production:

```powershell
python -m alembic upgrade head
```

Миграции рассчитаны на базу, в которой уже присутствует исходная схема
проекта. Для новой базы сначала примените базовую схему, используемую вашей
инфраструктурой, затем выполните `alembic upgrade head`. Не запускайте
`Base.metadata.create_all()` в production вместо миграций.

## Production и Render

Для production обязательно задайте:

- `DATABASE_URL`;
- `APP_SECRET_KEY` — случайную длинную строку;
- `ADMIN_USERNAME`;
- `ADMIN_PASSWORD` — не используйте `admin123`.

Команда запуска:

```text
alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

В репозитории есть [render.yaml](./render.yaml) с web-сервисом и PostgreSQL.

## Проверки

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q backend\app
node --check frontend\js\page.js
node --check frontend\js\script.js
```

## Генерация расписания

Генерация выполняется в отдельном процессе через `GenerationJob`, поэтому
долгий CP-SAT поиск не блокирует обработку HTTP-запросов. Сначала используйте
`/schedules/diagnostics/{academic_period_id}`: endpoint проверяет входные
данные, доступные слоты, конфликты ресурсов и совместимость аудиторий.
После проверки запускайте `POST /schedules/generate`.
