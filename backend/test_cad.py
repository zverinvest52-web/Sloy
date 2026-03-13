"""
Test script for CAD converter.
"""

import cv2
import numpy as np
import sys
from pathlib import Path
from cad_converter import CADConverter


def test_cad_converter():
    """Test the CAD converter with a sample image."""

    print("Creating test drawing...")

    # Create a simple drawing with lines and circles
    width, height = 800, 600
    image = np.zeros((height, width), dtype=np.uint8)

    # Draw some lines
    cv2.line(image, (100, 100), (700, 100), 255, 2)
    cv2.line(image, (100, 100), (100, 500), 255, 2)
    cv2.line(image, (700, 100), (700, 500), 255, 2)
    cv2.line(image, (100, 500), (700, 500), 255, 2)

    # Draw some circles
    cv2.circle(image, (400, 300), 80, 255, 2)
    cv2.circle(image, (250, 200), 50, 255, 2)
    cv2.circle(image, (550, 400), 60, 255, 2)

    # Save test image
    test_path = "test_cad_input.png"
    cv2.imwrite(test_path, image)
    print(f"Test image saved to {test_path}")

    # Process with CAD converter
    print("\nExtracting CAD elements...")
    converter = CADConverter(scale_factor=0.1)  # 10 pixels = 1mm

    elements = converter.extract_elements(image)

    print(f"[OK] Found {len(elements.polylines)} polylines")
    print(f"[OK] Found {len(elements.lines)} lines")
    print(f"[OK] Found {len(elements.circles)} circles")

    # Convert to DXF
    output_path = "test_output.dxf"
    print(f"\nGenerating DXF file...")

    success = converter.to_dxf(elements, output_path)

    if success:
        print(f"[OK] DXF file saved to {output_path}")

        # Verify file exists and has content
        dxf_path = Path(output_path)
        if dxf_path.exists() and dxf_path.stat().st_size > 0:
            print(f"[OK] DXF file size: {dxf_path.stat().st_size} bytes")
            print("\n[OK] All CAD conversion tests passed!")
            return True
        else:
            print("[FAIL] DXF file is empty or missing")
            return False
    else:
        print("[FAIL] Failed to create DXF file")
        return False


if __name__ == "__main__":
    success = test_cad_converter()
    sys.exit(0 if success else 1)
