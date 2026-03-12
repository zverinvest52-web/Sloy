# Sloy

Fullstack приложение на FastAPI + React.

## Структура проекта

```
Sloy/
├── backend/          # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/         # React + Vite frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Быстрый старт

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend запустится на http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend запустится на http://localhost:5173

## Технологии

- **Backend**: Python 3.x, FastAPI, Uvicorn
- **Frontend**: React 18, TypeScript, Vite
- **Стиль кода**: ESLint, TypeScript strict mode
