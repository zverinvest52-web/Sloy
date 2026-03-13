# Sloy Backend

FastAPI backend для проекта Sloy.

## Установка

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

### Быстро (из корня проекта)

На Windows можно запустить одной командой (backend + frontend):

```bat
start.bat
```

### Только backend

```bash
uvicorn main:app --reload
```

API будет доступен на http://localhost:8000
