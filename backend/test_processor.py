"""
Test script for image processor.
"""

import cv2
import sys
from pathlib import Path
from image_processor import ImageProcessor


def test_image_processor():
    """Test the image processor with a sample image."""

    # Create test image (simulated paper with drawing)
    print("Creating test image...")

    # Create a white image (A4 proportions: 210x297)
    width, height = 800, 1131
    test_image = 255 * np.ones((height, width, 3), dtype=np.uint8)

    # Draw some simple shapes (simulating a drawing)
    cv2.rectangle(test_image, (100, 100), (700, 300), (0, 0, 0), 2)
    cv2.circle(test_image, (400, 565), 150, (0, 0, 0), 2)
    cv2.line(test_image, (100, 800), (700, 800), (0, 0, 0), 2)

    # Add some perspective distortion
    pts1 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    pts2 = np.float32([[50, 30], [width-30, 50], [width-50, height-30], [30, height-50]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    distorted = cv2.warpPerspective(test_image, M, (width, height))

    # Add some noise/texture
    noise = np.random.randint(0, 30, distorted.shape, dtype=np.uint8)
    distorted = cv2.add(distorted, noise)

    # Save test image
    test_path = Path("test_input.jpg")
    cv2.imwrite(str(test_path), distorted)
    print(f"Test image saved to {test_path}")

    # Process the image
    print("\nProcessing image...")
    processor = ImageProcessor()
    result = processor.process_image(str(test_path))

    if result.success:
        print("[OK] Processing successful!")

        # Save results
        if result.processed_image is not None:
            cv2.imwrite("test_output.png", result.processed_image)
            print("[OK] Processed image saved to test_output.png")

        if result.original_image is not None and result.contour is not None:
            # Draw contour on original
            debug_img = result.original_image.copy()
            cv2.drawContours(debug_img, [result.contour], -1, (0, 255, 0), 3)
            cv2.imwrite("test_debug.png", debug_img)
            print("[OK] Debug image saved to test_debug.png")

        print("\n[OK] All tests passed!")
        return True
    else:
        print(f"[FAIL] Processing failed: {result.error}")
        return False


if __name__ == "__main__":
    import numpy as np

    success = test_image_processor()
    sys.exit(0 if success else 1)
