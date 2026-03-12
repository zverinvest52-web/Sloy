"""
Image processing module for Sloy project.
Handles contour detection, perspective correction, and drawing extraction.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result of image processing pipeline."""
    success: bool
    processed_image: Optional[np.ndarray] = None
    original_image: Optional[np.ndarray] = None
    contour: Optional[np.ndarray] = None
    error: Optional[str] = None


class ImageProcessor:
    """Handles OpenCV-based image processing for drawing digitization."""

    def __init__(self):
        self.gaussian_kernel = (5, 5)
        self.canny_threshold1 = 50
        self.canny_threshold2 = 150
        self.poly_epsilon = 0.02
        self.min_contour_area = 1000

    def process_image(self, image_path: str) -> ProcessingResult:
        """
        Main processing pipeline.

        Args:
            image_path: Path to input image

        Returns:
            ProcessingResult with processed image or error
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return ProcessingResult(
                    success=False,
                    error="Failed to load image"
                )

            original = image.copy()

            # Step 1: Detect paper contour
            contour = self.detect_paper_contour(image)
            if contour is None:
                return ProcessingResult(
                    success=False,
                    error="Failed to detect paper contour"
                )

            # Step 2: Apply perspective transform
            warped = self.apply_perspective_transform(image, contour)
            if warped is None:
                return ProcessingResult(
                    success=False,
                    error="Failed to apply perspective transform"
                )

            # Step 3: Extract drawing (binarization)
            processed = self.extract_drawing(warped)

            return ProcessingResult(
                success=True,
                processed_image=processed,
                original_image=original,
                contour=contour
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"Processing error: {str(e)}"
            )

    def detect_paper_contour(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect the contour of the paper sheet.

        Args:
            image: Input image

        Returns:
            Contour points or None if not found
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, self.gaussian_kernel, 0)

        # Edge detection
        edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)

        # Find contours
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Sort by area and get the largest
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        for contour in contours[:5]:  # Check top 5 largest
            # Approximate contour
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, self.poly_epsilon * peri, True)

            # Check if it's a quadrilateral with sufficient area
            if len(approx) == 4 and cv2.contourArea(approx) > self.min_contour_area:
                return approx

        return None

    def apply_perspective_transform(
        self, image: np.ndarray, contour: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Apply perspective transformation to correct the view.

        Args:
            image: Input image
            contour: 4-point contour of the paper

        Returns:
            Warped image or None if failed
        """
        if len(contour) != 4:
            return None

        # Reshape contour
        pts = contour.reshape(4, 2)

        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = self._order_points(pts)

        # Calculate dimensions
        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))

        # Destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype=np.float32)

        # Calculate perspective transform matrix
        M = cv2.getPerspectiveTransform(rect.astype(np.float32), dst)

        # Apply transformation
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        return warped

    def extract_drawing(self, image: np.ndarray) -> np.ndarray:
        """
        Extract drawing by binarization and cleaning.

        Args:
            image: Warped image

        Returns:
            Binary image with drawing
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

        # Invert if needed (drawing should be black on white)
        if np.mean(binary) < 127:
            binary = cv2.bitwise_not(binary)

        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        return binary

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """
        Order points in clockwise order starting from top-left.

        Args:
            pts: 4 points

        Returns:
            Ordered points [tl, tr, br, bl]
        """
        rect = np.zeros((4, 2), dtype=np.float32)

        # Sum and diff
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        rect[0] = pts[np.argmin(s)]      # top-left
        rect[2] = pts[np.argmax(s)]      # bottom-right
        rect[1] = pts[np.argmin(diff)]   # top-right
        rect[3] = pts[np.argmax(diff)]   # bottom-left

        return rect
