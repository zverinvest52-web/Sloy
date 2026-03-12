"""
FastAPI application for Sloy - Drawing digitization service.
"""

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

from image_processor import ImageProcessor, ProcessingResult
from cad_converter import CADConverter, CADElements, Line, Circle, Rectangle

app = FastAPI(title="Sloy API", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
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
    """Response model for processing endpoint."""
    success: bool
    id: str
    original_url: Optional[str] = None
    processed_url: Optional[str] = None
    dxf_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class LineModel(BaseModel):
    """Line model for export endpoint."""
    x1: float = Field(ge=-1e6, le=1e6)
    y1: float = Field(ge=-1e6, le=1e6)
    x2: float = Field(ge=-1e6, le=1e6)
    y2: float = Field(ge=-1e6, le=1e6)


class CircleModel(BaseModel):
    """Circle model for export endpoint."""
    x: float = Field(ge=-1e6, le=1e6)
    y: float = Field(ge=-1e6, le=1e6)
    radius: float = Field(gt=0, le=1e6)


class RectangleModel(BaseModel):
    """Rectangle model for export endpoint."""
    x: float = Field(ge=-1e6, le=1e6)
    y: float = Field(ge=-1e6, le=1e6)
    width: float = Field(gt=0, le=1e6)
    height: float = Field(gt=0, le=1e6)


class ExportRequest(BaseModel):
    """Request model for export endpoint."""
    lines: list[LineModel] = Field(default=[], max_length=10000)
    circles: list[CircleModel] = Field(default=[], max_length=10000)
    rectangles: list[RectangleModel] = Field(default=[], max_length=10000)


@app.get("/")
async def root():
    """Root endpoint."""
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
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/upload", response_model=ProcessResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload and process an image.

    Args:
        file: Image file to process

    Returns:
        ProcessResponse with results
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "File must be an image")

        # Generate unique ID
        file_id = str(uuid.uuid4())

        # Save uploaded file
        original_path = UPLOAD_DIR / f"{file_id}_original{Path(file.filename).suffix}"
        with original_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process image
        processor = ImageProcessor()
        result = processor.process_image(str(original_path))

        if not result.success:
            return ProcessResponse(
                success=False,
                id=file_id,
                error=result.error
            )

        # Save processed image
        processed_path = PROCESSED_DIR / f"{file_id}_processed.png"
        cv2.imwrite(str(processed_path), result.processed_image)

        # Convert to DXF
        converter = CADConverter(scale_factor=0.1)
        dxf_path = DXF_DIR / f"{file_id}.dxf"

        success, elements = converter.process_image_to_dxf(
            result.processed_image,
            str(dxf_path)
        )

        if not success:
            return ProcessResponse(
                success=False,
                id=file_id,
                error="Failed to generate DXF"
            )

        # Build response
        return ProcessResponse(
            success=True,
            id=file_id,
            original_url=f"/api/files/{original_path.name}",
            processed_url=f"/api/files/{processed_path.name}",
            dxf_url=f"/api/download/{file_id}",
            metadata={
                "lines_detected": len(elements.lines),
                "circles_detected": len(elements.circles)
            }
        )

    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    """
    Get uploaded or processed file.

    Args:
        filename: Name of the file

    Returns:
        File response
    """
    # Check in uploads
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)

    # Check in processed
    file_path = PROCESSED_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)

    raise HTTPException(404, "File not found")


@app.get("/api/download/{file_id}")
async def download_dxf(file_id: str):
    """
    Download DXF file.

    Args:
        file_id: ID of the processed file

    Returns:
        DXF file
    """
    dxf_path = DXF_DIR / f"{file_id}.dxf"

    if not dxf_path.exists():
        raise HTTPException(404, "DXF file not found")

    return FileResponse(
        dxf_path,
        media_type="application/dxf",
        filename=f"drawing_{file_id}.dxf"
    )


@app.post("/api/export")
async def export_shapes(request: ExportRequest) -> FileResponse:
    """
    Export detected shapes to DXF R12 format.

    Args:
        request: ExportRequest with lists of shapes

    Returns:
        DXF file in R12 format

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    file_id = str(uuid.uuid4())
    dxf_path = DXF_DIR / f"{file_id}.dxf"

    try:
        # Convert request models to CAD elements
        lines = [Line(x1=l.x1, y1=l.y1, x2=l.x2, y2=l.y2) for l in request.lines]
        circles = [Circle(x=c.x, y=c.y, radius=c.radius) for c in request.circles]
        rectangles = [Rectangle(x=r.x, y=r.y, width=r.width, height=r.height) for r in request.rectangles]

        elements = CADElements(lines=lines, circles=circles, rectangles=rectangles)

        # Export to DXF R12
        converter = CADConverter()
        success = converter.export_to_dxf_r12(elements, str(dxf_path))

        if not success:
            logger.error(f"DXF export failed for file_id={file_id}")
            raise HTTPException(500, "Failed to generate DXF file")

        # Verify file was created
        if not dxf_path.exists():
            logger.error(f"DXF file not found after export: {dxf_path}")
            raise HTTPException(500, "Failed to generate DXF file")

        # Return the file
        return FileResponse(
            dxf_path,
            media_type="application/dxf",
            filename=f"export_{file_id}.dxf"
        )

    except HTTPException:
        # Cleanup on failure
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
