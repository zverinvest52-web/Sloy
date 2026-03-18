"""FastAPI application for Sloy - Drawing digitization service."""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging
import uuid
import cv2
import numpy as np
from pathlib import Path
import shutil
import os

try:
    from image_processor import ImageProcessor, ProcessingResult
    from cad_converter import CADConverter, CADElements, Line, Circle, Rectangle
    from config import Config
    from services.integration import apply_cad_constraints_to_elements, get_processing_stats
except ModuleNotFoundError:
    from backend.image_processor import ImageProcessor, ProcessingResult
    from backend.cad_converter import CADConverter, CADElements, Line, Circle, Rectangle
    from backend.config import Config
    from backend.services.integration import apply_cad_constraints_to_elements, get_processing_stats

app = FastAPI(title="Sloy API", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log active configuration on startup
logger.info(f"Sloy API starting - {Config.log_config()}")

_cors_allow_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_origins=_cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
DXF_DIR = Path("dxf")

for directory in [UPLOAD_DIR, PROCESSED_DIR, DXF_DIR]:
    directory.mkdir(exist_ok=True)


class ProcessResponse(BaseModel):
    success: bool
    id: str
    original_url: Optional[str] = None
    processed_url: Optional[str] = None
    vector_preview_url: Optional[str] = None
    warped_original_url: Optional[str] = None
    dxf_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class LineModel(BaseModel):
    x1: float = Field(ge=-1e6, le=1e6)
    y1: float = Field(ge=-1e6, le=1e6)
    x2: float = Field(ge=-1e6, le=1e6)
    y2: float = Field(ge=-1e6, le=1e6)


class CircleModel(BaseModel):
    x: float = Field(ge=-1e6, le=1e6)
    y: float = Field(ge=-1e6, le=1e6)
    radius: float = Field(gt=0, le=1e6)


class RectangleModel(BaseModel):
    x: float = Field(ge=-1e6, le=1e6)
    y: float = Field(ge=-1e6, le=1e6)
    width: float = Field(gt=0, le=1e6)
    height: float = Field(gt=0, le=1e6)


class ExportRequest(BaseModel):
    lines: list[LineModel] = Field(default=[], max_length=10000)
    circles: list[CircleModel] = Field(default=[], max_length=10000)
    rectangles: list[RectangleModel] = Field(default=[], max_length=10000)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Sloy API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "POST /api/upload",
            "process": "POST /api/process/{id}",
            "download": "GET /api/download/{id}"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/upload", response_model=ProcessResponse)
async def upload_image(file: UploadFile = File(...)):
    try:
        if not (file.content_type or "").startswith("image/"):
            raise HTTPException(400, "File must be an image")

        file_id = str(uuid.uuid4())
        suffix = Path(file.filename).suffix if file.filename else ".png"
        original_path = UPLOAD_DIR / f"{file_id}_original{suffix}"
        with original_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        processor = ImageProcessor()
        result = processor.process_image(str(original_path))

        if not result.success:
            return ProcessResponse(success=False, id=file_id, error=result.error)

        processed_path = PROCESSED_DIR / f"{file_id}_processed.png"
        cv2.imwrite(str(processed_path), result.processed_image)

        warped_path = PROCESSED_DIR / f"{file_id}_warped.png"
        if result.warped_original_image is not None:
            cv2.imwrite(str(warped_path), result.warped_original_image)
        else:
            warped_path = original_path

        converter = CADConverter(scale_factor=0.1)
        dxf_path = DXF_DIR / f"{file_id}.dxf"

        # Extract elements
        elements = converter.extract_elements(result.processed_image)

        # Apply CAD constraints if enabled
        elements = apply_cad_constraints_to_elements(elements, Config)

        # Convert to DXF
        success = converter.to_dxf(elements, str(dxf_path))

        if not success or elements is None:
            return ProcessResponse(success=False, id=file_id, error="Failed to generate DXF")

        vector_preview_path = PROCESSED_DIR / f"{file_id}_vector_preview.png"
        preview_h, preview_w = result.processed_image.shape[:2]
        preview = np.full((preview_h, preview_w), 255, dtype=np.uint8)

        sf = float(converter.scale_factor)
        if sf <= 0:
            sf = 1.0

        def to_px(x: float, y: float) -> tuple[int, int]:
            return (int(round(x / sf)), int(round(y / sf)))

        for pl in elements.polylines:
            pts = pl.points
            for i in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                cv2.line(preview, to_px(x1, y1), to_px(x2, y2), (0,), 2, lineType=cv2.LINE_AA)
            if pl.closed and len(pts) >= 2:
                (x1, y1), (x2, y2) = pts[-1], pts[0]
                cv2.line(preview, to_px(x1, y1), to_px(x2, y2), (0,), 2, lineType=cv2.LINE_AA)

        for line in elements.lines:
            cv2.line(preview, to_px(line.x1, line.y1), to_px(line.x2, line.y2), (0,), 2, lineType=cv2.LINE_AA)

        for circle in elements.circles:
            center = to_px(circle.x, circle.y)
            radius = int(round(circle.radius / sf))
            if radius > 0:
                cv2.circle(preview, center, radius, (0,), 2, lineType=cv2.LINE_AA)

        cv2.imwrite(str(vector_preview_path), preview)

        # Get processing statistics
        stats = get_processing_stats(elements)
        stats['cad_solver_enabled'] = Config.USE_CAD_SOLVER

        return ProcessResponse(
            success=True,
            id=file_id,
            original_url=f"/api/files/{warped_path.name}",
            warped_original_url=f"/api/files/{warped_path.name}",
            processed_url=f"/api/files/{processed_path.name}",
            vector_preview_url=f"/api/files/{vector_preview_path.name}",
            dxf_url=f"/api/download/{file_id}",
            metadata=stats
        )

    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)

    file_path = PROCESSED_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)

    raise HTTPException(404, "File not found")


@app.get("/api/download/{file_id}")
async def download_dxf(file_id: str):
    dxf_path = DXF_DIR / f"{file_id}.dxf"

    if not dxf_path.exists():
        raise HTTPException(404, "DXF file not found")

    return FileResponse(dxf_path, media_type="application/dxf", filename=f"drawing_{file_id}.dxf")


@app.post("/api/export")
async def export_shapes(request: ExportRequest) -> FileResponse:
    file_id = str(uuid.uuid4())
    dxf_path = DXF_DIR / f"{file_id}.dxf"

    try:
        lines = [Line(x1=l.x1, y1=l.y1, x2=l.x2, y2=l.y2) for l in request.lines]
        circles = [Circle(x=c.x, y=c.y, radius=c.radius) for c in request.circles]
        rectangles = [Rectangle(x=r.x, y=r.y, width=r.width, height=r.height) for r in request.rectangles]

        elements = CADElements(lines=lines, circles=circles, rectangles=rectangles)

        converter = CADConverter()
        success = converter.export_to_dxf_r12(elements, str(dxf_path))

        if not success:
            logger.error(f"DXF export failed for file_id={file_id}")
            raise HTTPException(500, "Failed to generate DXF file")

        if not dxf_path.exists():
            logger.error(f"DXF file not found after export: {dxf_path}")
            raise HTTPException(500, "Failed to generate DXF file")

        return FileResponse(dxf_path, media_type="application/dxf", filename=f"export_{file_id}.dxf")

    except HTTPException:
        if dxf_path.exists():
            dxf_path.unlink()
        raise
    except ValueError as e:
        logger.warning(f"Invalid input data: {e}")
        if dxf_path.exists():
            dxf_path.unlink()
        raise HTTPException(400, "Invalid shape data")
    except Exception as e:
        logger.exception(f"Unexpected error during DXF export: {e}")
        if dxf_path.exists():
            dxf_path.unlink()
        raise HTTPException(500, "Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
