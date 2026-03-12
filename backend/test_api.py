"""
Test script for FastAPI endpoints.
"""

import requests
import sys
from pathlib import Path
import time


def test_api():
    """Test the FastAPI endpoints."""

    base_url = "http://localhost:8000"

    print("Testing Sloy API...")

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Health check passed")
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to API. Is the server running?")
        print("Start server with: uvicorn main:app --reload")
        return False

    # Test root endpoint
    print("\n2. Testing root endpoint...")
    response = requests.get(f"{base_url}/")
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] Root endpoint: {data['message']}")
    else:
        print(f"[FAIL] Root endpoint failed: {response.status_code}")
        return False

    # Test upload endpoint
    print("\n3. Testing upload endpoint...")

    # Create a test image if it doesn't exist
    test_image = Path("test_input.jpg")
    if not test_image.exists():
        print("[FAIL] Test image not found. Run test_processor.py first.")
        return False

    with open(test_image, "rb") as f:
        files = {"file": ("test.jpg", f, "image/jpeg")}
        response = requests.post(f"{base_url}/api/upload", files=files, timeout=30)

    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            print(f"[OK] Upload successful")
            print(f"    - Lines detected: {data['metadata']['lines_detected']}")
            print(f"    - Circles detected: {data['metadata']['circles_detected']}")
            print(f"    - DXF URL: {data['dxf_url']}")

            file_id = data["id"]

            # Test download endpoint
            print("\n4. Testing download endpoint...")
            response = requests.get(f"{base_url}/api/download/{file_id}", timeout=10)
            if response.status_code == 200:
                print(f"[OK] DXF download successful ({len(response.content)} bytes)")

                # Save downloaded DXF
                with open("downloaded_test.dxf", "wb") as f:
                    f.write(response.content)
                print("[OK] DXF saved to downloaded_test.dxf")

                print("\n[OK] All API tests passed!")
                return True
            else:
                print(f"[FAIL] Download failed: {response.status_code}")
                return False
        else:
            print(f"[FAIL] Upload failed: {data.get('error')}")
            return False
    else:
        print(f"[FAIL] Upload request failed: {response.status_code}")
        return False


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
