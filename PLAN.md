# План реализации проекта Sloy

## Обзор проекта

Sloy — система автоматической оцифровки чертежей с бумаги в CAD-формат (DXF).

**Основной флоу:**
1. Пользователь загружает фото чертежа
2. Backend обрабатывает изображение (OpenCV)
3. Система находит контуры, корректирует перспективу
4. Генерируется черно-белый чертеж
5. Координаты конвертируются в DXF (ezdxf)
6. Frontend показывает сравнение до/после
7. Пользователь скачивает DXF файл

## Архитектура

```
Frontend (React)          Backend (FastAPI)           Processing
    │                          │                          │
    ├─ Upload Image ──────────>│                          │
    │                          ├─ Validate ──────────────>│
    │                          │                          ├─ OpenCV Pipeline
    │                          │                          │  ├─ Contour Detection
    │                          │                          │  ├─ Perspective Transform
    │                          │                          │  └─ Binarization
    │                          │<─────────────────────────┤
    │                          ├─ CAD Conversion ────────>│
    │                          │                          ├─ ezdxf Generation
    │                          │<─────────────────────────┤
    │<─ Return Results ────────┤
    ├─ Display Comparison
    └─ Download DXF
```

## Backend: Этап 1 - OpenCV Processing Pipeline

### 1.1 Установка зависимостей
```python
# requirements.txt
opencv-python==4.9.0.80
opencv-contrib-python==4.9.0.80
numpy==1.26.4
pillow==10.2.0
ezdxf==1.3.0
```

### 1.2 Модуль обработки изображений (`backend/image_processor.py`)

**Функции:**
- `detect_paper_contour(image)` - поиск контура листа
- `apply_perspective_transform(image, contour)` - коррекция перспективы
- `extract_drawing(image)` - извлечение чертежа (бинаризация)
- `approximate_contours(contours, epsilon)` - аппроксимация PolyDP

**Алгоритм:**
1. Конвертация в grayscale
2. Gaussian blur для шумоподавления
3. Adaptive threshold или Canny edge detection
4. findContours с RETR_EXTERNAL
5. Аппроксимация контура (approxPolyDP с epsilon=0.02*perimeter)
6. Проверка на 4 угла (четырехугольник)
7. Perspective transform (getPerspectiveTransform + warpPerspective)
8. Бинаризация (THRESH_BINARY + THRESH_OTSU)
9. Морфологические операции (closing для заполнения разрывов)

### 1.3 API endpoints (`backend/main.py`)

```python
POST /api/upload          # Загрузка изображения
POST /api/process         # Обработка изображения
GET  /api/result/{id}     # Получение результата
GET  /api/download/{id}   # Скачивание DXF
```

## Backend: Этап 2 - CAD Conversion

### 2.1 Модуль конвертации (`backend/cad_converter.py`)

**Функции:**
- `extract_lines(binary_image)` - извлечение линий (HoughLinesP)
- `extract_circles(binary_image)` - извлечение окружностей (HoughCircles)
- `coordinates_to_dxf(lines, circles, output_path)` - генерация DXF

**Алгоритм:**
1. Скелетонизация изображения (morphologyEx с MORPH_SKELETON)
2. Hough Line Transform для прямых линий
3. Hough Circle Transform для окружностей
4. Фильтрация дубликатов (близкие линии объединяются)
5. Масштабирование координат (пиксели → мм)
6. Создание DXF документа (ezdxf.new('R2010'))
7. Добавление примитивов (LINE, CIRCLE, ARC)

### 2.2 Масштабирование

```python
# Определение масштаба по известному размеру листа
# A4: 210x297mm
scale_factor = real_width_mm / image_width_px
```

## Frontend: Этап 3 - UI Implementation

### 3.1 Компоненты

**Структура:**
```
src/
├── components/
│   ├── ImageUploader.tsx      # Drag & drop upload
│   ├── ComparisonSlider.tsx   # Before/after slider
│   ├── ProcessingStatus.tsx   # Progress indicator
│   └── DownloadButton.tsx     # DXF download
├── services/
│   └── api.ts                 # API client
└── types/
    └── index.ts               # TypeScript types
```

### 3.2 Comparison Slider

**Библиотека:** `react-compare-image` или custom implementation

**Функционал:**
- Вертикальный разделитель
- Drag для сравнения
- Zoom для детального просмотра
- Overlay с координатами

### 3.3 API Integration

```typescript
interface ProcessResult {
  id: string;
  original_url: string;
  processed_url: string;
  dxf_url: string;
  status: 'processing' | 'completed' | 'failed';
  metadata: {
    contours_found: number;
    lines_detected: number;
    circles_detected: number;
  };
}
```

## Этап 4: Продвинутые алгоритмы

### 4.1 Polygon Douglas-Peucker Approximation

```python
def approximate_with_polydp(contour, epsilon_factor=0.02):
    """
    Аппроксимация контура алгоритмом Дугласа-Пекера
    epsilon_factor: чем меньше, тем точнее (0.01-0.05)
    """
    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_factor * perimeter
    approx = cv2.approxPolyDP(contour, epsilon, True)
    return approx
```

### 4.2 Adaptive Thresholding

```python
def adaptive_threshold(image):
    """
    Адаптивная бинаризация для неравномерного освещения
    """
    return cv2.adaptiveThreshold(
        image, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2
    )
```

### 4.3 Sub-pixel Accuracy

```python
def refine_corners(image, corners):
    """
    Уточнение координат углов с субпиксельной точностью
    """
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners_refined = cv2.cornerSubPix(
        image, corners, (5, 5), (-1, -1), criteria
    )
    return corners_refined
```

## Этап 5: Пошаговая реализация

### Неделя 1: Backend Core
- [ ] Настройка FastAPI проекта
- [ ] Установка OpenCV и зависимостей
- [ ] Реализация базового image_processor.py
- [ ] Тестирование на sample изображениях

### Неделя 2: CV Pipeline
- [ ] Детекция контуров листа
- [ ] Perspective transform
- [ ] Бинаризация и очистка
- [ ] Unit тесты для каждого этапа

### Неделя 3: CAD Conversion
- [ ] Интеграция ezdxf
- [ ] Извлечение линий (Hough)
- [ ] Извлечение окружностей
- [ ] Генерация DXF файлов

### Неделя 4: API & Storage
- [ ] REST API endpoints
- [ ] File upload handling
- [ ] Temporary storage (Redis/filesystem)
- [ ] Error handling

### Неделя 5: Frontend Base
- [ ] React компоненты
- [ ] Image uploader
- [ ] API integration
- [ ] Routing

### Неделя 6: Comparison Slider
- [ ] Реализация slider компонента
- [ ] Zoom functionality
- [ ] Responsive design
- [ ] Mobile support

### Неделя 7: Polish & Testing
- [ ] E2E тестирование
- [ ] Performance optimization
- [ ] Error handling UI
- [ ] Documentation

## Технические детали

### OpenCV Pipeline Parameters

```python
# Оптимальные параметры (требуют тюнинга)
GAUSSIAN_KERNEL = (5, 5)
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 150
POLY_EPSILON = 0.02
MIN_CONTOUR_AREA = 1000
HOUGH_THRESHOLD = 50
HOUGH_MIN_LINE_LENGTH = 50
HOUGH_MAX_LINE_GAP = 10
```

### DXF Layer Structure

```python
# Слои в DXF файле
LAYER_LINES = "LINES"
LAYER_CIRCLES = "CIRCLES"
LAYER_DIMENSIONS = "DIMENSIONS"
LAYER_BORDER = "BORDER"
```

### API Response Format

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "original": "/uploads/original.jpg",
    "processed": "/uploads/processed.png",
    "dxf": "/downloads/drawing.dxf",
    "metadata": {
      "dimensions": {"width": 210, "height": 297},
      "elements": {"lines": 45, "circles": 3},
      "processing_time": 2.3
    }
  }
}
```

## Риски и митигация

1. **Плохое качество фото** → Добавить валидацию и рекомендации
2. **Сложные чертежи** → Начать с простых геометрических фигур
3. **Производительность** → Асинхронная обработка (Celery/RQ)
4. **Точность** → Калибровка по эталонным размерам

## Следующие шаги

1. Создать sample dataset (10-20 фото чертежей)
2. Реализовать MVP backend (только прямые линии)
3. Протестировать точность на тестовых данных
4. Итеративно улучшать алгоритмы
5. Добавить frontend после стабилизации backend
