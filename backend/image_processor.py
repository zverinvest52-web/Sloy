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
    warped_original_image: Optional[np.ndarray] = None
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

            # Step 1: Detect paper contour (optional)
            contour = self.detect_paper_contour(image)

            # If we can't find a paper quad (common for clean screenshots), skip
            # perspective correction and just binarize the full image.
            if contour is None:
                processed = self.extract_drawing(image)
                return ProcessingResult(
                    success=True,
                    processed_image=processed,
                    original_image=original,
                    warped_original_image=None,
                    contour=None,
                )

            # Step 2: Apply perspective transform
            warped = self.apply_perspective_transform(image, contour)
            if warped is None:
                processed = self.extract_drawing(image)
                return ProcessingResult(
                    success=True,
                    processed_image=processed,
                    original_image=original,
                    warped_original_image=None,
                    contour=contour,
                )

            # Step 3: Extract drawing (binarization)
            processed = self.extract_drawing(warped)

            return ProcessingResult(
                success=True,
                processed_image=processed,
                original_image=original,
                warped_original_image=warped,
                contour=contour
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                error=f"Processing error: {str(e)}"
            )

    def detect_paper_contour(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Detect a paper-like quadrilateral for perspective correction.

        The goal is to work for real photos (paper may not touch borders) while
        avoiding false warps on clean CAD screenshots/UI frames.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        def score_quad(approx: np.ndarray) -> Optional[float]:
            if len(approx) != 4 or cv2.contourArea(approx) <= self.min_contour_area:
                return None
            if not cv2.isContourConvex(approx):
                return None

            quad_area = float(cv2.contourArea(approx))
            area_ratio = quad_area / float(w * h)
            if area_ratio < 0.25:
                return None

            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [approx], -1, (255,), thickness=-1)
            inside_mean = float(cv2.mean(gray, mask=mask)[0])
            if inside_mean < 150.0:
                return None

            outside_mean = float(cv2.mean(gray, mask=cv2.bitwise_not(mask))[0])
            contrast = inside_mean - outside_mean

            x, y, bw, bh = cv2.boundingRect(approx)
            border_tol = int(0.03 * min(w, h))
            touches_border = (
                x <= border_tol
                or y <= border_tol
                or (x + bw) >= (w - 1 - border_tol)
                or (y + bh) >= (h - 1 - border_tol)
            )

            # CAD screenshots tend to have globally bright backgrounds (low contrast).
            if outside_mean > 200.0 and contrast < 20.0:
                return None

            # Require either strong contrast (photo on darker background) or at least
            # some contrast + border touch (paper filling the frame).
            if (contrast < 25.0) and (not (touches_border and contrast >= 10.0)):
                return None

            return area_ratio * max(0.0, contrast)

        candidates: List[np.ndarray] = []

        # Pass 1: edges-based candidates (good for high-contrast photos)
        blurred = cv2.GaussianBlur(gray, self.gaussian_kernel, 0)
        edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(contours)

        # Pass 2: brightness segmentation candidates (good for low-contrast / blurry photos)
        _, th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Ensure paper (bright) is foreground
        if float(np.mean(gray[th == 255])) < float(np.mean(gray[th == 0])):
            th = cv2.bitwise_not(th)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
        contours2, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(contours2)

        if not candidates:
            return None

        candidates = sorted(candidates, key=cv2.contourArea, reverse=True)

        best_score = None
        best_quad = None
        for contour in candidates[:12]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, self.poly_epsilon * peri, True)
            s = score_quad(approx)
            if s is None:
                continue
            if best_score is None or s > best_score:
                best_score = s
                best_quad = approx

        return best_quad

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
