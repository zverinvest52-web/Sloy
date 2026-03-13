"""Test export endpoint."""
import requests
# Test data
test_data = {
    "lines": [
        {"x1": 0, "y1": 0, "x2": 100, "y2": 0},
        {"x1": 100, "y1": 0, "x2": 100, "y2": 100}
    ],
    "circles": [
        {"x": 50, "y": 50, "radius": 25}
    ],
    "rectangles": [
        {"x": 150, "y": 150, "width": 100, "height": 50}
    ]
}

# Send request
response = requests.post(
    "http://localhost:8000/api/export",
    json=test_data
)

if response.status_code == 200:
    # Save DXF file
    with open("test_export.dxf", "wb") as f:
        f.write(response.content)
    print("OK Export successful: test_export.dxf created")
else:
    print(f"ERR Export failed: {response.status_code}")
    print(response.text)
