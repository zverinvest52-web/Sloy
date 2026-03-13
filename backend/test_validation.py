"""Test validation and error handling."""
import requests
BASE_URL = "http://localhost:8000/api/export"

# Test 1: Invalid radius (negative)
print("Test 1: Negative radius...")
response = requests.post(BASE_URL, json={
    "circles": [{"x": 0, "y": 0, "radius": -10}]
})
print(f"Status: {response.status_code} (expected 422)")
assert response.status_code == 422, "Should reject negative radius"

# Test 2: Too many shapes
print("\nTest 2: Too many shapes...")
response = requests.post(BASE_URL, json={
    "lines": [{"x1": 0, "y1": 0, "x2": 1, "y2": 1}] * 10001
})
print(f"Status: {response.status_code} (expected 422)")
assert response.status_code == 422, "Should reject >10k shapes"

# Test 3: Coordinates out of range
print("\nTest 3: Coordinates out of range...")
response = requests.post(BASE_URL, json={
    "circles": [{"x": 2e6, "y": 0, "radius": 10}]
})
print(f"Status: {response.status_code} (expected 422)")
assert response.status_code == 422, "Should reject out-of-range coordinates"

# Test 4: Valid request
print("\nTest 4: Valid request...")
response = requests.post(BASE_URL, json={
    "lines": [{"x1": 0, "y1": 0, "x2": 100, "y2": 0}],
    "circles": [{"x": 50, "y": 50, "radius": 25}],
    "rectangles": [{"x": 150, "y": 150, "width": 100, "height": 50}]
})
print(f"Status: {response.status_code} (expected 200)")
assert response.status_code == 200, "Should accept valid request"

print("\nOK All validation tests passed!")
