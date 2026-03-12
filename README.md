# Sloy - Автоматическая оцифровка чертежей

Fullstack приложение для автоматической конвертации фотографий чертежей в CAD формат (DXF).

## Возможности

- 📸 Загрузка фото чертежа через drag & drop
- 🔍 Автоматическое обнаружение контуров листа
- 📐 Коррекция перспективы (perspective transform)
- 🎨 Извлечение чертежа (адаптивная бинаризация)
- 📏 Детекция линий и окружностей (Hough Transform)
- 📄 Экспорт в DXF формат
- 🔄 Сравнение оригинала и обработанного изображения
- 💾 Скачивание готового DXF файла

## Технологии

### Backend
- **Python 3.12+**
- **FastAPI** - REST API
- **OpenCV** - компьютерное зрение
- **ezdxf** - генерация DXF файлов
- **NumPy, SciPy** - математические операции

### Frontend
- **React 18** + **TypeScript**
- **Vite** - сборка
- **Tailwind CSS** - стилизация
- **react-compare-image** - слайдер сравнения
- **axios** - HTTP клиент

## Установка и запуск

### Backend

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Активировать (Linux/Mac)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
uvicorn main:app --reload
```

Backend будет доступен на http://localhost:8000

API документация: http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Установить зависимости
npm install

# Запустить dev сервер
npm run dev
```

Frontend будет доступен на http://localhost:5173

## Использование

1. Откройте http://localhost:5173 в браузере
2. Загрузите фото чертежа (drag & drop или выбор файла)
3. Дождитесь обработки (обычно 2-5 секунд)
4. Просмотрите результат с помощью слайдера сравнения
5. Скачайте DXF файл

## Архитектура обработки

```
Фото чертежа
    ↓
[1] Детекция контура листа (findContours + approxPolyDP)
    ↓
[2] Коррекция перспективы (getPerspectiveTransform + warpPerspective)
    ↓
[3] Бинаризация (adaptiveThreshold + морфология)
    ↓
[4] Извлечение линий (HoughLinesP)
    ↓
[5] Извлечение окружностей (HoughCircles)
    ↓
[6] Генерация DXF (ezdxf)
    ↓
DXF файл
```

## API Endpoints

### `POST /api/upload`
Загрузка и обработка изображения

**Request:**
- `file`: multipart/form-data

**Response:**
```json
{
  "success": true,
  "id": "uuid",
  "original_url": "/api/files/...",
  "processed_url": "/api/files/...",
  "dxf_url": "/api/download/uuid",
  "metadata": {
    "lines_detected": 6,
    "circles_detected": 3
  }
}
```

### `GET /api/download/{id}`
Скачивание DXF файла

### `GET /api/files/{filename}`
Получение оригинального или обработанного изображения

## Тестирование

### Backend тесты

```bash
cd backend

# Тест обработки изображений
python test_processor.py

# Тест CAD конвертации
python test_cad.py

# Тест API (требуется запущенный сервер)
python test_api.py
```

### Frontend сборка

```bash
cd frontend
npm run build
```

## Алгоритмы

### Douglas-Peucker аппроксимация
Используется для точного определения углов листа:
```python
epsilon = 0.02 * perimeter
approx = cv2.approxPolyDP(contour, epsilon, True)
```

### Adaptive Thresholding
Бинаризация с учетом локального освещения:
```python
binary = cv2.adaptiveThreshold(
    gray, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    blockSize=11, C=2
)
```

### Hough Transform
Детекция геометрических примитивов:
- **HoughLinesP** - прямые линии
- **HoughCircles** - окружности

## Структура проекта

```
Sloy/
├── backend/
│   ├── main.py              # FastAPI приложение
│   ├── image_processor.py   # OpenCV обработка
│   ├── cad_converter.py     # DXF генерация
│   ├── requirements.txt     # Python зависимости
│   └── test_*.py           # Тесты
├── frontend/
│   ├── src/
│   │   ├── components/     # React компоненты
│   │   ├── services/       # API клиент
│   │   └── types/          # TypeScript типы
│   ├── package.json
│   └── vite.config.ts
├── PLAN.md                 # Детальный план реализации
└── README.md
```

## Roadmap

- [ ] Поддержка размерных линий
- [ ] Детекция текста (OCR)
- [ ] Калибровка по известным размерам
- [ ] Экспорт в другие форматы (SVG, PDF)
- [ ] Пакетная обработка
- [ ] История обработок

## Лицензия

MIT

## Авторы

Проект создан с использованием Claude Opus 4.6
