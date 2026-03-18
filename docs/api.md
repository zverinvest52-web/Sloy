# Sloy API Documentation

## Overview

Sloy is a drawing digitization service that converts scanned images of technical drawings into CAD-compatible DXF files. The API provides endpoints for image processing, shape detection, and DXF export.

**Base URL:** `http://localhost:8000` (development) or your deployed server URL

**API Version:** 1.0.0

## Features

- **Image Processing**: Automatic perspective correction and binarization
- **Shape Detection**: Detects lines, circles, rectangles, and polylines
- **DXF Export**: Generates DXF R12 format files compatible with AutoCAD, LibreCAD, and other CAD applications
- **Direct Export**: Export shapes programmatically without image processing
- **Preview Generation**: Get visual previews of detected shapes

## Authentication

Currently, the API does not require authentication. CORS is configured to allow requests from localhost on any port.

## Rate Limiting

No rate limiting is currently implemented. For production deployments, consider implementing rate limiting based on your requirements.

## Error Handling

All errors are returned as JSON with appropriate HTTP status codes:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| 200 | OK | Request succeeded |
| 400 | Bad Request | Invalid input data or file format |
| 404 | Not Found | Requested resource not found |
| 500 | Internal Server Error | Server error during processing |

## Endpoints

### 1. Root Endpoint

**GET** `/`

Welcome endpoint with API information.

**Response:**
```json
{
  "message": "Welcome to Sloy API",
  "version": "1.0.0",
  "git_version": "abc1234 Commit message",
  "endpoints": {
    "upload": "POST /api/upload",
    "process": "POST /api/process/{id}",
    "download": "GET /api/download/{id}"
  }
}
```

---

### 2. Health Check

**GET** `/health`

Check API health status and verify installed dependencies.

**Response:**
```json
{
  "status": "healthy",
  "git_version": "abc1234 Commit message",
  "opencv_version": "4.8.0",
  "has_corner_filter": true,
  "has_beads_filter": true
}
```

**Status Codes:**
- `200 OK` - API is healthy

---

### 3. Version Information

**GET** `/api/version`

Get detailed version and environment information.

**Response:**
```json
{
  "git_version": "abc1234 Commit message",
  "opencv_version": "4.8.0",
  "numpy_version": "1.24.0",
  "has_corner_filter": true,
  "has_beads_filter": true
}
```

**Status Codes:**
- `200 OK` - Version information retrieved

---

### 4. Upload and Process Image

**POST** `/api/upload`

Upload an image for processing. The API will perform perspective correction, detect shapes, and generate a DXF file.

**Request:**
- Content-Type: `multipart/form-data`
- Parameter: `file` (required) - Image file (JPEG, PNG, BMP, etc.)

**Response:**
```json
{
  "success": true,
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_url": "/api/files/550e8400-e29b-41d4-a716-446655440000_warped.png",
  "warped_original_url": "/api/files/550e8400-e29b-41d4-a716-446655440000_warped.png",
  "processed_url": "/api/files/550e8400-e29b-41d4-a716-446655440000_processed.png",
  "vector_preview_url": "/api/files/550e8400-e29b-41d4-a716-446655440000_vector_preview.png",
  "dxf_url": "/api/download/550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "polylines_detected": 5,
    "lines_detected": 12,
    "circles_detected": 3
  },
  "error": null
}
```

**Response Fields:**
- `success` (boolean) - Whether processing succeeded
- `id` (string) - Unique identifier for this job
- `original_url` (string) - URL to perspective-corrected original image
- `warped_original_url` (string) - Same as original_url (for frontend compatibility)
- `processed_url` (string) - URL to binarized/processed image
- `vector_preview_url` (string) - URL to vector preview (rasterized CAD elements)
- `dxf_url` (string) - URL to download the DXF file
- `metadata` (object) - Detection statistics
- `error` (string|null) - Error message if processing failed

**Status Codes:**
- `200 OK` - Processing completed (check `success` field)
- `400 Bad Request` - File is not a valid image
- `500 Internal Server Error` - Processing error occurred

**Error Response (Processing Failed):**
```json
{
  "success": false,
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Failed to generate DXF"
}
```

---

### 5. Get File

**GET** `/api/files/{filename}`

Retrieve an uploaded or processed file (images only).

**Parameters:**
- `filename` (string, path) - Name of the file to retrieve

**Response:**
- Binary file content with appropriate media type (image/png, image/jpeg, etc.)

**Status Codes:**
- `200 OK` - File retrieved successfully
- `404 Not Found` - File not found

---

### 6. Download DXF

**GET** `/api/download/{file_id}`

Download the generated DXF file.

**Parameters:**
- `file_id` (string, path) - Unique identifier from upload endpoint

**Response:**
- Binary DXF file with filename: `drawing_{file_id}.dxf`
- Content-Type: `application/dxf`

**Status Codes:**
- `200 OK` - DXF file downloaded successfully
- `404 Not Found` - DXF file not found

---

### 7. Export Shapes to DXF

**POST** `/api/export`

Export geometric shapes directly to DXF format without image processing.

**Request:**
- Content-Type: `application/json`

**Request Body:**
```json
{
  "lines": [
    {
      "x1": 0,
      "y1": 0,
      "x2": 100,
      "y2": 100
    },
    {
      "x1": 100,
      "y1": 0,
      "x2": 0,
      "y2": 100
    }
  ],
  "circles": [
    {
      "x": 50,
      "y": 50,
      "radius": 25
    }
  ],
  "rectangles": [
    {
      "x": 10,
      "y": 10,
      "width": 80,
      "height": 80
    }
  ]
}
```

**Request Constraints:**
- `lines`: Array of line objects (max 10,000 items)
  - `x1`, `y1`, `x2`, `y2`: Coordinates (-1,000,000 to 1,000,000)
- `circles`: Array of circle objects (max 10,000 items)
  - `x`, `y`: Center coordinates (-1,000,000 to 1,000,000)
  - `radius`: Positive value (0 < radius ≤ 1,000,000)
- `rectangles`: Array of rectangle objects (max 10,000 items)
  - `x`, `y`: Top-left corner (-1,000,000 to 1,000,000)
  - `width`, `height`: Positive values (0 < dimension ≤ 1,000,000)

**Response:**
- Binary DXF file with filename: `export_{file_id}.dxf`
- Content-Type: `application/dxf`

**Status Codes:**
- `200 OK` - DXF file generated successfully
- `400 Bad Request` - Invalid shape data
- `500 Internal Server Error` - Server error during export

**Error Response:**
```json
{
  "detail": "Invalid shape data"
}
```

---

## Usage Examples

### Python with Requests

#### Upload and Process Image

```python
import requests
from pathlib import Path

# Upload image
url = "http://localhost:8000/api/upload"
with open("drawing.png", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

result = response.json()

if result["success"]:
    file_id = result["id"]
    print(f"Processing successful! ID: {file_id}")

    # Download DXF
    dxf_url = f"http://localhost:8000{result['dxf_url']}"
    dxf_response = requests.get(dxf_url)

    with open(f"output_{file_id}.dxf", "wb") as f:
        f.write(dxf_response.content)

    print(f"DXF saved to output_{file_id}.dxf")
    print(f"Detected: {result['metadata']['polylines_detected']} polylines, "
          f"{result['metadata']['circles_detected']} circles")
else:
    print(f"Error: {result['error']}")
```

#### Export Shapes to DXF

```python
import requests

url = "http://localhost:8000/api/export"

shapes = {
    "lines": [
        {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
        {"x1": 100, "y1": 0, "x2": 0, "y2": 100}
    ],
    "circles": [
        {"x": 50, "y": 50, "radius": 25}
    ],
    "rectangles": [
        {"x": 10, "y": 10, "width": 80, "height": 80}
    ]
}

response = requests.post(url, json=shapes)

if response.status_code == 200:
    with open("export.dxf", "wb") as f:
        f.write(response.content)
    print("DXF exported successfully!")
else:
    print(f"Error: {response.json()}")
```

#### Get File Preview

```python
import requests
from PIL import Image
from io import BytesIO

# Get processed image preview
file_id = "550e8400-e29b-41d4-a716-446655440000"
url = f"http://localhost:8000/api/files/{file_id}_processed.png"

response = requests.get(url)
img = Image.open(BytesIO(response.content))
img.show()
```

---

### JavaScript/TypeScript with Fetch

#### Upload and Process Image

```javascript
async function uploadImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("http://localhost:8000/api/upload", {
    method: "POST",
    body: formData,
  });

  const result = await response.json();

  if (result.success) {
    console.log(`Processing successful! ID: ${result.id}`);
    console.log(`Detected: ${result.metadata.polylines_detected} polylines, ${result.metadata.circles_detected} circles`);

    // Download DXF
    const dxfUrl = `http://localhost:8000${result.dxf_url}`;
    const dxfResponse = await fetch(dxfUrl);
    const blob = await dxfResponse.blob();

    // Save file
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `drawing_${result.id}.dxf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  } else {
    console.error(`Error: ${result.error}`);
  }
}

// Usage
const fileInput = document.getElementById("imageInput");
fileInput.addEventListener("change", (e) => {
  uploadImage(e.target.files[0]);
});
```

#### Export Shapes to DXF

```javascript
async function exportShapes() {
  const shapes = {
    lines: [
      { x1: 0, y1: 0, x2: 100, y2: 100 },
      { x1: 100, y1: 0, x2: 0, y2: 100 },
    ],
    circles: [{ x: 50, y: 50, radius: 25 }],
    rectangles: [{ x: 10, y: 10, width: 80, height: 80 }],
  };

  const response = await fetch("http://localhost:8000/api/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(shapes),
  });

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "export.dxf";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    console.log("DXF exported successfully!");
  } else {
    const error = await response.json();
    console.error(`Error: ${error.detail}`);
  }
}
```

#### Get File Preview

```javascript
async function getPreview(fileId) {
  const url = `http://localhost:8000/api/files/${fileId}_vector_preview.png`;
  const response = await fetch(url);
  const blob = await response.blob();

  const img = document.createElement("img");
  img.src = URL.createObjectURL(blob);
  document.body.appendChild(img);
}
```

---

### cURL Examples

#### Upload Image

```bash
curl -X POST \
  -F "file=@drawing.png" \
  http://localhost:8000/api/upload
```

#### Download DXF

```bash
curl -X GET \
  http://localhost:8000/api/download/550e8400-e29b-41d4-a716-446655440000 \
  -o drawing.dxf
```

#### Export Shapes

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "lines": [
      {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
    ],
    "circles": [
      {"x": 50, "y": 50, "radius": 25}
    ],
    "rectangles": []
  }' \
  http://localhost:8000/api/export \
  -o export.dxf
```

#### Get File

```bash
curl -X GET \
  http://localhost:8000/api/files/550e8400-e29b-41d4-a716-446655440000_processed.png \
  -o processed.png
```

#### Health Check

```bash
curl -X GET http://localhost:8000/health
```

---

## Response Models

### ProcessResponse

Used by the `/api/upload` endpoint.

```typescript
interface ProcessResponse {
  success: boolean;
  id: string;
  original_url?: string;
  warped_original_url?: string;
  processed_url?: string;
  vector_preview_url?: string;
  dxf_url?: string;
  error?: string;
  metadata?: {
    polylines_detected: number;
    lines_detected: number;
    circles_detected: number;
  };
}
```

### ExportRequest

Used by the `/api/export` endpoint.

```typescript
interface LineModel {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface CircleModel {
  x: number;
  y: number;
  radius: number;
}

interface RectangleModel {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface ExportRequest {
  lines?: LineModel[];
  circles?: CircleModel[];
  rectangles?: RectangleModel[];
}
```

---

## Workflow Examples

### Complete Image Processing Workflow

1. **Upload Image**
   ```
   POST /api/upload
   ```
   Returns: `file_id`, preview URLs, and DXF download URL

2. **View Previews** (Optional)
   ```
   GET /api/files/{file_id}_original.png
   GET /api/files/{file_id}_processed.png
   GET /api/files/{file_id}_vector_preview.png
   ```

3. **Download DXF**
   ```
   GET /api/download/{file_id}
   ```

### Direct Shape Export Workflow

1. **Prepare Shapes**
   - Define lines, circles, and rectangles with coordinates

2. **Export to DXF**
   ```
   POST /api/export
   ```
   Returns: DXF file

---

## Best Practices

### Image Upload

- **Supported Formats**: JPEG, PNG, BMP, TIFF
- **Recommended Resolution**: 300+ DPI for best results
- **File Size**: Keep under 50MB for optimal performance
- **Image Quality**: Clear, high-contrast drawings work best

### Shape Export

- **Coordinate System**: Use consistent units (e.g., millimeters)
- **Validation**: Ensure all coordinates are within valid ranges
- **Batch Operations**: For large exports, consider splitting into multiple requests
- **Error Handling**: Always check response status codes

### Performance

- **Concurrent Requests**: The API can handle multiple concurrent uploads
- **File Cleanup**: Processed files are stored on the server; implement cleanup policies
- **Caching**: Cache preview URLs if displaying multiple times

---

## Troubleshooting

### Common Issues

**Issue**: Upload returns 400 "File must be an image"
- **Solution**: Ensure the file has a valid image MIME type (image/jpeg, image/png, etc.)

**Issue**: DXF download returns 404
- **Solution**: Verify the file_id is correct and processing completed successfully

**Issue**: Export returns 400 "Invalid shape data"
- **Solution**: Check that all coordinates are within valid ranges and dimensions are positive

**Issue**: Processing takes a long time
- **Solution**: Large or complex images may take longer; consider reducing image size or resolution

---

## API Versioning

The current API version is **1.0.0**. Breaking changes will increment the major version number. Check the `/api/version` endpoint for current version information.

---

## Support

For issues, questions, or feature requests, please refer to the project repository or contact the development team.
