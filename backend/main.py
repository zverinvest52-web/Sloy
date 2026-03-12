"""
FastAPI application for Sloy - Drawing digitization service.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import cv2
import numpy as np
from pathlib import Path
import shutil

from image_processor import ImageProcessor, ProcessingResult
from cad_converter import CADConverter

app = FastAPI(title="Sloy API", version="1.0.0")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
