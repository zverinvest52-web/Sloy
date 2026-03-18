# План миграции на гибридную ML+CV+CAD архитектуру

## Обзор

Текущая система использует чистый CV подход (OpenCV + Hough Transform). Цель миграции — внедрить гибридную архитектуру с ML моделями для повышения точности и расширения функциональности.

### Текущая архитектура
```
Фото → Детекция контура → Коррекция перспективы → Бинаризация →
Hough Transform (линии/окружности) → DXF
```

### Целевая архитектура
```
Фото → ML Document Detection → Perspective Correction →
ML Segmentation → Hybrid Feature Extraction (ML + CV) →
CAD Intelligence Layer → Optimized DXF
```

## Ключевые улучшения

1. **ML Document Detection** - замена findContours на нейросеть для надежной детекции листа
2. **ML Segmentation** - семантическая сегментация элементов чертежа
3. **Hybrid Feature Extraction** - комбинация ML предсказаний и CV верификации
4. **CAD Intelligence** - постобработка с учетом CAD правил (snap to grid, merge близких точек)
5. **Vectorization Quality** - улучшенная точность линий, дуг, окружностей

## Фазы миграции

### Фаза 1: ML Document Detection (2-3 недели)
- Интеграция предобученной модели детекции документов
- Fallback на текущий CV подход
- A/B тестирование

### Фаза 2: ML Line/Shape Extraction (3-4 недели)
- Обучение/интеграция модели сегментации линий
- Гибридный подход: ML + Hough верификация
- Метрики качества

### Фаза 3: CAD Intelligence Layer (2-3 недели)
- Snap to grid, merge vertices
- Топологическая оптимизация
- Валидация DXF

### Фаза 4: Production Optimization (1-2 недели)
- Профилирование производительности
- Кэширование моделей
- Мониторинг

---

## Модуль 1: ML Document Detection

### 1.1 Выбор модели

**Рекомендация: DocTR (Document Text Recognition)**
- Предобучена на документах
- Легковесная (ResNet50 backbone)
- Хорошо работает с перспективными искажениями
- Apache 2.0 лицензия

**Альтернативы:**
- U²-Net (salient object detection) - для сложных фонов
- Custom YOLO - если нужна максимальная скорость

### 1.2 Архитектура модуля

```python
# backend/ml_models/document_detector.py

from typing import Optional, Tuple
import numpy as np
import cv2
from doctr.models import detection_predictor

class MLDocumentDetector:
    """ML-based document detection with CV fallback"""

    def __init__(self, use_ml: bool = True, confidence_threshold: float = 0.7):
        self.use_ml = use_ml
        self.confidence_threshold = confidence_threshold
        self.model = None

        if use_ml:
            self._load_model()

    def _load_model(self):
        """Lazy load DocTR model"""
        self.model = detection_predictor(
            arch='db_resnet50',
            pretrained=True
        )

    def detect(self, image: np.ndarray) -> Tuple[np.ndarray, float, str]:
        """
        Detect document corners

        Returns:
            corners: (4, 2) array of corner coordinates
            confidence: detection confidence [0-1]
            method: 'ml' or 'cv_fallback'
        """
        if self.use_ml and self.model:
            corners, confidence = self._ml_detect(image)

            if confidence >= self.confidence_threshold:
                return corners, confidence, 'ml'

        # Fallback to current CV approach
        corners = self._cv_fallback(image)
        return corners, 1.0, 'cv_fallback'

    def _ml_detect(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """ML detection using DocTR"""
        # DocTR expects RGB
        if len(image.shape) == 2:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        result = self.model([image_rgb])

        # Extract largest bounding box
        boxes = result[0]['boxes']
        if len(boxes) == 0:
            return None, 0.0

        # Get box with highest confidence
        confidences = result[0]['confidences']
        best_idx = np.argmax(confidences)
        box = boxes[best_idx]
        confidence = confidences[best_idx]

        # Convert to corner format
        corners = self._box_to_corners(box, image.shape)
        return corners, float(confidence)

    def _cv_fallback(self, image: np.ndarray) -> np.ndarray:
        """Current OpenCV approach"""
        # Existing logic from image_processor.py
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            if len(approx) == 4:
                return approx.reshape(4, 2)

        # Default to image corners
        h, w = image.shape[:2]
        return np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
```

### 1.3 Интеграция в image_processor.py

```python
# backend/image_processor.py (обновление)

from ml_models.document_detector import MLDocumentDetector

class ImageProcessor:
    def __init__(self):
        self.doc_detector = MLDocumentDetector(use_ml=True)

    def detect_document(self, image: np.ndarray) -> dict:
        """Detect document with ML + metadata"""
        corners, confidence, method = self.doc_detector.detect(image)

        return {
            'corners': corners,
            'confidence': confidence,
            'method': method,
            'fallback_used': method == 'cv_fallback'
        }
```

### 1.4 Зависимости

```txt
# requirements.txt (добавить)
python-doctr==0.7.0
torch==2.1.0  # или tensorflow==2.15.0
torchvision==0.16.0
```

### 1.5 Тестирование

```python
# backend/tests/test_ml_document_detection.py

import pytest
import cv2
import numpy as np
from ml_models.document_detector import MLDocumentDetector

def test_ml_detection_high_confidence():
    detector = MLDocumentDetector(use_ml=True, confidence_threshold=0.7)
    image = cv2.imread('test_data/clear_document.jpg')

    corners, confidence, method = detector.detect(image)

    assert method == 'ml'
    assert confidence >= 0.7
    assert corners.shape == (4, 2)

def test_fallback_on_low_confidence():
    detector = MLDocumentDetector(use_ml=True, confidence_threshold=0.9)
    image = cv2.imread('test_data/blurry_document.jpg')

    corners, confidence, method = detector.detect(image)

    # Should fallback if ML confidence < 0.9
    assert method in ['ml', 'cv_fallback']
    assert corners.shape == (4, 2)
```

---

## Модуль 2: ML Line & Shape Extraction

### 2.1 Выбор подхода

**Рекомендация: Hybrid ML Segmentation + Hough Refinement**

Используем легковесную сегментационную модель для первичной детекции, затем уточняем с помощью Hough Transform.

**Модели для рассмотрения:**
1. **LCNN (Line Convolutional Neural Network)** - специализирована на линиях
2. **HED (Holistically-Nested Edge Detection)** - edge detection с глубоким обучением
3. **Custom U-Net** - обучить на датасете чертежей

### 2.2 Архитектура модуля

```python
# backend/ml_models/line_extractor.py

import torch
import torch.nn as nn
import numpy as np
import cv2
from typing import List, Tuple, Dict

class HybridLineExtractor:
    """Hybrid ML + CV line extraction"""

    def __init__(self, use_ml: bool = True, model_path: Optional[str] = None):
        self.use_ml = use_ml
        self.model = None

        if use_ml:
            self._load_model(model_path)

    def _load_model(self, model_path: Optional[str]):
        """Load pretrained line detection model"""
        if model_path:
            self.model = torch.load(model_path)
        else:
            # Use HED pretrained on BSDS500
            self.model = self._load_hed_model()

        self.model.eval()

    def extract_lines(self, image: np.ndarray) -> Dict:
        """
        Extract lines using hybrid approach

        Returns:
            {
                'lines': List of line segments [(x1,y1,x2,y2), ...],
                'confidence': List of confidence scores,
                'method': 'ml' | 'hybrid' | 'cv_only'
            }
        """
        if self.use_ml and self.model:
            # ML edge detection
            edge_map = self._ml_edge_detection(image)

            # Refine with Hough
            lines = self._hough_refinement(edge_map, image)

            return {
                'lines': lines,
                'method': 'hybrid',
                'edge_map': edge_map
            }
        else:
            # Pure CV fallback
            lines = self._cv_line_detection(image)
            return {
                'lines': lines,
                'method': 'cv_only'
            }

    def _ml_edge_detection(self, image: np.ndarray) -> np.ndarray:
        """ML-based edge detection"""
        # Preprocess
        img_tensor = self._preprocess_image(image)

        with torch.no_grad():
            edge_map = self.model(img_tensor)

        # Post-process to binary edge map
        edge_map = edge_map.squeeze().cpu().numpy()
        edge_map = (edge_map * 255).astype(np.uint8)

        return edge_map

    def _hough_refinement(self, edge_map: np.ndarray, original: np.ndarray) -> List[Tuple]:
        """Refine ML edges with Hough Transform"""
        # Apply morphological operations to clean edges
        kernel = np.ones((3, 3), np.uint8)
        edge_map = cv2.morphologyEx(edge_map, cv2.MORPH_CLOSE, kernel)

        # Hough Line Transform with adaptive parameters
        lines = cv2.HoughLinesP(
            edge_map,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=30,
            maxLineGap=10
        )

        if lines is None:
            return []

        # Merge collinear lines
        merged_lines = self._merge_collinear_lines(lines)

        return merged_lines

    def _merge_collinear_lines(self, lines: np.ndarray,
                                angle_threshold: float = 5.0,
                                distance_threshold: float = 10.0) -> List[Tuple]:
        """Merge lines that are nearly collinear"""
        if len(lines) == 0:
            return []

        merged = []
        used = set()

        for i, line1 in enumerate(lines):
            if i in used:
                continue

            x1, y1, x2, y2 = line1[0]
            angle1 = np.arctan2(y2 - y1, x2 - x1)

            # Find similar lines
            group = [line1[0]]

            for j, line2 in enumerate(lines[i+1:], start=i+1):
                if j in used:
                    continue

                x3, y3, x4, y4 = line2[0]
                angle2 = np.arctan2(y4 - y3, x4 - x3)

                # Check angle similarity
                angle_diff = abs(angle1 - angle2) * 180 / np.pi
                if angle_diff > angle_threshold and angle_diff < (180 - angle_threshold):
                    continue

                # Check distance
                dist = self._point_to_line_distance((x3, y3), (x1, y1, x2, y2))
                if dist < distance_threshold:
                    group.append(line2[0])
                    used.add(j)

            # Merge group into single line
            merged_line = self._fit_line_to_points(group)
            merged.append(merged_line)
            used.add(i)

        return merged

    def _cv_line_detection(self, image: np.ndarray) -> List[Tuple]:
        """Current CV approach (fallback)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=50,
            maxLineGap=10
        )

        return lines.reshape(-1, 4).tolist() if lines is not None else []
```

### 2.3 Circle Detection Enhancement

```python
# backend/ml_models/circle_extractor.py

class HybridCircleExtractor:
    """Hybrid circle detection with ML preprocessing"""

    def extract_circles(self, image: np.ndarray, edge_map: Optional[np.ndarray] = None) -> List[Dict]:
        """
        Extract circles using ML edge map + Hough Circles

        Returns:
            List of {center: (x,y), radius: r, confidence: float}
        """
        if edge_map is None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edge_map = cv2.Canny(gray, 50, 150)

        # Apply Hough Circle Transform
        circles = cv2.HoughCircles(
            edge_map,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=200
        )

        if circles is None:
            return []

        # Convert to structured format
        result = []
        for circle in circles[0]:
            x, y, r = circle
            result.append({
                'center': (int(x), int(y)),
                'radius': int(r),
                'confidence': 1.0  # Can be enhanced with ML confidence
            })

        return result
```

### 2.4 Интеграция в image_processor.py

```python
# backend/image_processor.py (обновление)

from ml_models.line_extractor import HybridLineExtractor
from ml_models.circle_extractor import HybridCircleExtractor

class ImageProcessor:
    def __init__(self):
        self.doc_detector = MLDocumentDetector(use_ml=True)
        self.line_extractor = HybridLineExtractor(use_ml=True)
        self.circle_extractor = HybridCircleExtractor()

    def extract_features(self, image: np.ndarray) -> dict:
        """Extract lines and circles with hybrid approach"""
        # Extract lines
        line_result = self.line_extractor.extract_lines(image)
        lines = line_result['lines']

        # Extract circles using ML edge map if available
        edge_map = line_result.get('edge_map')
        circles = self.circle_extractor.extract_circles(image, edge_map)

        return {
            'lines': lines,
            'circles': circles,
            'method': line_result['method'],
            'metadata': {
                'lines_count': len(lines),
                'circles_count': len(circles)
            }
        }
```

### 2.5 Зависимости

```txt
# requirements.txt (добавить)
torch==2.1.0
torchvision==0.16.0
scikit-image==0.22.0
```

---

## Модуль 3: CAD Intelligence Layer

### 3.1 Цель модуля

Постобработка извлеченных примитивов с учетом CAD правил:
- Snap to grid (привязка к сетке)
- Merge близких вершин
- Обнаружение параллельных/перпендикулярных линий
- Топологическая оптимизация
- Валидация геометрии

### 3.2 Архитектура

```python
# backend/cad_intelligence/optimizer.py

from typing import List, Tuple, Dict
import numpy as np
from dataclasses import dataclass

@dataclass
class CADLine:
    start: Tuple[float, float]
    end: Tuple[float, float]
    layer: str = "0"
    confidence: float = 1.0

@dataclass
class CADCircle:
    center: Tuple[float, float]
    radius: float
    layer: str = "0"
    confidence: float = 1.0

class CADOptimizer:
    """Intelligent CAD optimization and cleanup"""

    def __init__(self,
                 grid_size: float = 1.0,
                 snap_threshold: float = 2.0,
                 merge_threshold: float = 3.0,
                 angle_snap_degrees: float = 5.0):
        self.grid_size = grid_size
        self.snap_threshold = snap_threshold
        self.merge_threshold = merge_threshold
        self.angle_snap = np.radians(angle_snap_degrees)

    def optimize(self, lines: List[CADLine], circles: List[CADCircle]) -> Dict:
        """
        Apply CAD intelligence optimizations

        Returns:
            {
                'lines': optimized lines,
                'circles': optimized circles,
                'stats': optimization statistics
            }
        """
        stats = {
            'original_lines': len(lines),
            'original_circles': len(circles),
            'vertices_merged': 0,
            'lines_merged': 0,
            'angles_snapped': 0
        }

        # Step 1: Snap to grid
        lines = self._snap_to_grid(lines)
        circles = self._snap_circles_to_grid(circles)

        # Step 2: Merge close vertices
        lines, merged_count = self._merge_vertices(lines)
        stats['vertices_merged'] = merged_count

        # Step 3: Snap angles (0°, 45°, 90°, etc.)
        lines, snapped_count = self._snap_angles(lines)
        stats['angles_snapped'] = snapped_count

        # Step 4: Merge collinear lines
        lines, merged_lines = self._merge_collinear(lines)
        stats['lines_merged'] = merged_lines

        # Step 5: Detect and enforce constraints
        lines = self._enforce_constraints(lines)

        stats['final_lines'] = len(lines)
        stats['final_circles'] = len(circles)

        return {
            'lines': lines,
            'circles': circles,
            'stats': stats
        }

    def _snap_to_grid(self, lines: List[CADLine]) -> List[CADLine]:
        """Snap line endpoints to grid"""
        snapped = []
        for line in lines:
            start = self._snap_point(line.start)
            end = self._snap_point(line.end)
            snapped.append(CADLine(start, end, line.layer, line.confidence))
        return snapped

    def _snap_point(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Snap point to nearest grid intersection"""
        x, y = point
        snapped_x = round(x / self.grid_size) * self.grid_size
        snapped_y = round(y / self.grid_size) * self.grid_size
        return (snapped_x, snapped_y)

    def _merge_vertices(self, lines: List[CADLine]) -> Tuple[List[CADLine], int]:
        """Merge vertices that are very close"""
        # Build vertex graph
        vertices = {}
        for line in lines:
            for point in [line.start, line.end]:
                key = self._vertex_key(point)
                if key not in vertices:
                    vertices[key] = []
                vertices[key].append(point)

        # Find merge candidates
        merge_map = {}
        merged_count = 0

        for key, points in vertices.items():
            if len(points) > 1:
                # Merge to centroid
                centroid = np.mean(points, axis=0)
                centroid = tuple(centroid)
                for point in points:
                    merge_map[point] = centroid
                merged_count += len(points) - 1

        # Apply merges
        merged_lines = []
        for line in lines:
            start = merge_map.get(line.start, line.start)
            end = merge_map.get(line.end, line.end)

            # Skip degenerate lines
            if start != end:
                merged_lines.append(CADLine(start, end, line.layer, line.confidence))

        return merged_lines, merged_count

    def _snap_angles(self, lines: List[CADLine]) -> Tuple[List[CADLine], int]:
        """Snap lines to common angles (0°, 45°, 90°, etc.)"""
        common_angles = [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi]
        snapped_count = 0
        snapped_lines = []

        for line in lines:
            x1, y1 = line.start
            x2, y2 = line.end

            angle = np.arctan2(y2 - y1, x2 - x1)

            # Find nearest common angle
            nearest_angle = min(common_angles, key=lambda a: abs(angle - a))

            if abs(angle - nearest_angle) < self.angle_snap:
                # Snap to nearest angle
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                new_x2 = x1 + length * np.cos(nearest_angle)
                new_y2 = y1 + length * np.sin(nearest_angle)

                snapped_lines.append(CADLine(
                    line.start,
                    (new_x2, new_y2),
                    line.layer,
                    line.confidence
                ))
                snapped_count += 1
            else:
                snapped_lines.append(line)

        return snapped_lines, snapped_count

    def _merge_collinear(self, lines: List[CADLine]) -> Tuple[List[CADLine], int]:
        """Merge collinear line segments"""
        # Implementation similar to line_extractor._merge_collinear_lines
        # but working with CADLine objects
        merged_count = 0
        # ... (detailed implementation)
        return lines, merged_count

    def _enforce_constraints(self, lines: List[CADLine]) -> List[CADLine]:
        """Enforce geometric constraints (parallel, perpendicular)"""
        # Detect parallel line groups
        # Detect perpendicular intersections
        # Adjust to enforce exact constraints
        return lines
```

### 3.3 Интеграция в cad_converter.py

```python
# backend/cad_converter.py (обновление)

from cad_intelligence.optimizer import CADOptimizer, CADLine, CADCircle

class CADConverter:
    def __init__(self):
        self.optimizer = CADOptimizer(
            grid_size=1.0,
            snap_threshold=2.0,
            merge_threshold=3.0
        )

    def convert_to_dxf(self, lines: List, circles: List, output_path: str) -> dict:
        """Convert with CAD intelligence"""
        # Convert to CAD objects
        cad_lines = [CADLine((l[0], l[1]), (l[2], l[3])) for l in lines]
        cad_circles = [CADCircle((c['center']), c['radius']) for c in circles]

        # Optimize
        result = self.optimizer.optimize(cad_lines, cad_circles)

        # Generate DXF
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()

        for line in result['lines']:
            msp.add_line(line.start, line.end)

        for circle in result['circles']:
            msp.add_circle(circle.center, circle.radius)

        doc.saveas(output_path)

        return {
            'success': True,
            'stats': result['stats']
        }
```

---

## Модуль 4: Production Optimization

### 4.1 Model Loading & Caching

```python
# backend/ml_models/model_manager.py

import torch
from functools import lru_cache
from pathlib import Path
import logging

class ModelManager:
    """Centralized model loading and caching"""

    _instance = None
    _models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @lru_cache(maxsize=3)
    def load_model(self, model_name: str, model_path: Optional[str] = None):
        """Load model with caching"""
        if model_name in self._models:
            return self._models[model_name]

        logging.info(f"Loading model: {model_name}")

        if model_name == "document_detector":
            from doctr.models import detection_predictor
            model = detection_predictor(arch='db_resnet50', pretrained=True)
        elif model_name == "line_extractor":
            model = torch.load(model_path) if model_path else self._load_hed()
        else:
            raise ValueError(f"Unknown model: {model_name}")

        # Move to GPU if available
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        model.eval()

        self._models[model_name] = model
        logging.info(f"Model {model_name} loaded on {device}")

        return model

    def preload_models(self):
        """Preload all models at startup"""
        self.load_model("document_detector")
        self.load_model("line_extractor")
```

### 4.2 Async Processing Pipeline

```python
# backend/main.py (обновление)

from fastapi import FastAPI, BackgroundTasks
from ml_models.model_manager import ModelManager
import asyncio

app = FastAPI()

# Preload models at startup
@app.on_event("startup")
async def startup_event():
    model_manager = ModelManager()
    await asyncio.to_thread(model_manager.preload_models)

@app.post("/api/upload")
async def upload_image(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    """Async image processing"""
    # Save file
    file_id = str(uuid.uuid4())
    image_path = f"uploads/{file_id}.jpg"

    # Process in background
    background_tasks.add_task(process_image_async, file_id, image_path)

    return {
        "id": file_id,
        "status": "processing"
    }

@app.get("/api/status/{file_id}")
async def get_status(file_id: str):
    """Check processing status"""
    # Check Redis/DB for status
    status = await get_processing_status(file_id)
    return status
```

### 4.3 Performance Monitoring

```python
# backend/monitoring/metrics.py

import time
from functools import wraps
from prometheus_client import Counter, Histogram
import logging

# Metrics
processing_time = Histogram(
    'image_processing_seconds',
    'Time spent processing images',
    ['stage']
)

processing_errors = Counter(
    'processing_errors_total',
    'Total processing errors',
    ['error_type']
)

def monitor_performance(stage: str):
    """Decorator for performance monitoring"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                processing_time.labels(stage=stage).observe(duration)
                logging.info(f"{stage} completed in {duration:.2f}s")
                return result
            except Exception as e:
                processing_errors.labels(error_type=type(e).__name__).inc()
                raise
        return wrapper
    return decorator

# Usage
@monitor_performance("document_detection")
def detect_document(image):
    # ...
    pass
```

### 4.4 Зависимости для Production

```txt
# requirements.txt (добавить)

# Async & Performance
redis==5.0.0
celery==5.3.4
prometheus-client==0.19.0

# Monitoring
sentry-sdk==1.39.0

# GPU acceleration (optional)
onnxruntime-gpu==1.16.0  # для ONNX inference
```

---

## План рефакторинга существующего кода

### Этап 1: Подготовка (1 неделя)

**1.1 Создать структуру модулей**
```
backend/
├── ml_models/
│   ├── __init__.py
│   ├── model_manager.py
│   ├── document_detector.py
│   ├── line_extractor.py
│   └── circle_extractor.py
├── cad_intelligence/
│   ├── __init__.py
│   └── optimizer.py
├── monitoring/
│   ├── __init__.py
│   └── metrics.py
└── tests/
    ├── test_ml_detection.py
    ├── test_line_extraction.py
    └── test_cad_optimization.py
```

**1.2 Рефакторинг image_processor.py**
- Выделить методы в отдельные классы
- Добавить интерфейсы для ML/CV переключения
- Добавить логирование и метрики

**1.3 Рефакторинг cad_converter.py**
- Интегрировать CADOptimizer
- Добавить валидацию DXF
- Улучшить обработку ошибок

### Этап 2: Интеграция ML (2-3 недели)

**2.1 Document Detection**
- Интегрировать MLDocumentDetector
- Добавить A/B тестирование (ML vs CV)
- Собрать метрики точности

**2.2 Line Extraction**
- Интегрировать HybridLineExtractor
- Настроить параметры Hough Transform
- Оптимизировать merge алгоритмы

**2.3 Testing**
- Создать тестовый датасет (50+ изображений)
- Сравнить качество ML vs CV
- Измерить производительность

### Этап 3: CAD Intelligence (2 недели)

**3.1 Optimizer Integration**
- Интегрировать CADOptimizer в pipeline
- Настроить параметры snap/merge
- Валидация выходных DXF

**3.2 Quality Metrics**
- Метрики точности векторизации
- Сравнение с ground truth
- User feedback loop

### Этап 4: Production Ready (1-2 недели)

**4.1 Performance**
- Профилирование bottlenecks
- Оптимизация inference
- Кэширование моделей

**4.2 Monitoring**
- Prometheus metrics
- Sentry error tracking
- Logging infrastructure

**4.3 Deployment**
- Docker optimization (multi-stage build)
- GPU support (optional)
- Health checks

---

## Анализ производительности

### Текущая производительность (CV only)

| Этап | Время | % от общего |
|------|-------|-------------|
| Document detection | 50-100ms | 5% |
| Perspective correction | 100-150ms | 10% |
| Binarization | 200-300ms | 20% |
| Hough Lines | 500-800ms | 50% |
| Hough Circles | 100-200ms | 10% |
| DXF generation | 50-100ms | 5% |
| **Total** | **1-1.7s** | **100%** |

### Ожидаемая производительность (Hybrid ML+CV)

| Этап | Время | Изменение |
|------|-------|-----------|
| ML Document detection | 100-200ms | +100ms |
| Perspective correction | 100-150ms | без изменений |
| ML Edge detection | 300-500ms | +200ms |
| Hough refinement | 200-300ms | -400ms |
| Circle detection | 100-200ms | без изменений |
| CAD optimization | 100-200ms | +150ms |
| DXF generation | 50-100ms | без изменений |
| **Total** | **1-1.8s** | **+0-0.1s** |

**Вывод:** Небольшое увеличение времени обработки (+5-10%), но значительное улучшение качества.

### Оптимизации для компенсации

1. **ONNX Runtime** - конвертация PyTorch → ONNX (ускорение 2-3x)
2. **Batch processing** - обработка нескольких изображений параллельно
3. **GPU inference** - ускорение ML этапов в 5-10x
4. **Model quantization** - уменьшение размера моделей (INT8)

---

## Риски и митигация

### Риск 1: Увеличение времени обработки
**Вероятность:** Средняя
**Влияние:** Среднее
**Митигация:**
- ONNX оптимизация
- GPU inference для production
- Async processing с очередями

### Риск 2: Снижение точности на некоторых типах чертежей
**Вероятность:** Средняя
**Влияние:** Высокое
**Митигация:**
- A/B тестирование перед полным переходом
- Fallback на CV при низкой confidence
- Сбор feedback от пользователей

### Риск 3: Увеличение размера Docker образа
**Вероятность:** Высокая
**Влияние:** Низкое
**Митигация:**
- Multi-stage Docker build
- Использование slim base images
- Опциональная GPU поддержка

### Риск 4: Сложность deployment на бесплатных хостингах
**Вероятность:** Высокая
**Влияние:** Среднее
**Митигация:**
- CPU-only версия для Render free tier
- Легковесные модели (MobileNet backbone)
- Опциональное отключение ML (env var)

---

## Timeline и Milestones

### Milestone 1: ML Document Detection (Неделя 1-2)
- [ ] Интеграция DocTR
- [ ] A/B тестирование
- [ ] Метрики точности
- [ ] Deployment на staging

### Milestone 2: Hybrid Line Extraction (Неделя 3-5)
- [ ] Интеграция HED/LCNN
- [ ] Hough refinement
- [ ] Line merging optimization
- [ ] Performance benchmarks

### Milestone 3: CAD Intelligence (Неделя 6-7)
- [ ] CADOptimizer implementation
- [ ] Snap to grid
- [ ] Angle snapping
- [ ] DXF validation

### Milestone 4: Production Ready (Неделя 8-9)
- [ ] ONNX conversion
- [ ] Monitoring setup
- [ ] Docker optimization
- [ ] Production deployment

---

## Стратегия тестирования

### Unit Tests
```python
# backend/tests/test_ml_detection.py
def test_document_detection_accuracy():
    detector = MLDocumentDetector()
    test_images = load_test_dataset()

    correct = 0
    for image, ground_truth in test_images:
        corners, conf, method = detector.detect(image)
        if is_correct(corners, ground_truth):
            correct += 1

    accuracy = correct / len(test_images)
    assert accuracy > 0.90  # 90% accuracy threshold
```

### Integration Tests
```python
def test_full_pipeline():
    processor = ImageProcessor()
    image = cv2.imread('test_data/sample.jpg')

    result = processor.process(image)

    assert result['success']
    assert len(result['lines']) > 0
    assert result['dxf_path'].exists()
```

### Performance Tests
```python
def test_processing_time():
    processor = ImageProcessor()
    image = cv2.imread('test_data/sample.jpg')

    start = time.time()
    result = processor.process(image)
    duration = time.time() - start

    assert duration < 2.0  # Max 2 seconds
```

---

## Стратегия deployment

### Staging Environment
1. Deploy на отдельный Render service
2. Env var: `ML_ENABLED=true`
3. Тестирование с реальными пользователями (beta)
4. Сбор метрик производительности

### Production Rollout
1. **Phase 1 (10% traffic):** Canary deployment
2. **Phase 2 (50% traffic):** Monitor metrics
3. **Phase 3 (100% traffic):** Full rollout
4. **Rollback plan:** Feature flag для отключения ML

### Docker Configuration
```dockerfile
# Dockerfile (multi-stage)
FROM python:3.12-slim as base

# Stage 1: Build dependencies
FROM base as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime
FROM base
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
ENV ML_ENABLED=true
ENV TORCH_HOME=/app/.cache/torch

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Заключение

Миграция на гибридную ML+CV архитектуру обеспечит:

✅ **Улучшение точности** - особенно для сложных условий съемки
✅ **Масштабируемость** - легко добавлять новые типы примитивов
✅ **Гибкость** - fallback на CV при необходимости
✅ **Production-ready** - мониторинг, метрики, оптимизация

**Рекомендуемый подход:** Поэтапная миграция с A/B тестированием и возможностью rollback.

**Общее время реализации:** 8-9 недель
**Команда:** 1-2 разработчика
**Риски:** Средние, управляемые
