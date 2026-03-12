"""
CAD conversion module for Sloy project.
Converts processed images to DXF format using ezdxf.
"""

import cv2
import numpy as np
import ezdxf
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Line:
    """Represents a line segment."""
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class Circle:
    """Represents a circle."""
    x: float
    y: float
    radius: float


@dataclass
class CADElements:
    """Container for extracted CAD elements."""
    lines: List[Line]
    circles: List[Circle]


class CADConverter:
    """Converts binary images to DXF format."""

    def __init__(self, scale_factor: float = 1.0):
        """
        Initialize CAD converter.

        Args:
            scale_factor: Conversion factor from pixels to mm (default: 1.0)
        """
        self.scale_factor = scale_factor
        self.hough_threshold = 50
        self.hough_min_line_length = 50
        self.hough_max_line_gap = 10
        self.circle_dp = 1.2
        self.circle_min_dist = 50
        self.circle_param1 = 50
        self.circle_param2 = 30
        self.circle_min_radius = 10
        self.circle_max_radius = 200

    def extract_elements(self, binary_image: np.ndarray) -> CADElements:
        """
        Extract lines and circles from binary image.

        Args:
            binary_image: Binary image (black drawing on white background)

        Returns:
            CADElements containing detected lines and circles
        """
        # Invert if needed (Hough works better with white lines on black)
        if np.mean(binary_image) > 127:
            working_image = cv2.bitwise_not(binary_image)
        else:
            working_image = binary_image.copy()

        # Extract lines
        lines = self._extract_lines(working_image)

        # Extract circles
        circles = self._extract_circles(working_image)

        return CADElements(lines=lines, circles=circles)

    def _extract_lines(self, image: np.ndarray) -> List[Line]:
        """Extract lines using Hough Line Transform."""
        # Apply edge detection
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # Detect lines
        lines_raw = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.hough_min_line_length,
            maxLineGap=self.hough_max_line_gap
        )

        if lines_raw is None:
            return []

        # Convert to Line objects
        lines = []
        for line in lines_raw:
            x1, y1, x2, y2 = line[0]
            lines.append(Line(
                x1=float(x1) * self.scale_factor,
                y1=float(y1) * self.scale_factor,
                x2=float(x2) * self.scale_factor,
                y2=float(y2) * self.scale_factor
            ))

        # Merge close lines
        lines = self._merge_lines(lines)

        return lines

    def _extract_circles(self, image: np.ndarray) -> List[Circle]:
        """Extract circles using Hough Circle Transform."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Detect circles
        circles_raw = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=self.circle_dp,
            minDist=self.circle_min_dist,
            param1=self.circle_param1,
            param2=self.circle_param2,
            minRadius=self.circle_min_radius,
            maxRadius=self.circle_max_radius
        )

        if circles_raw is None:
            return []

        # Convert to Circle objects
        circles = []
        for circle in circles_raw[0]:
            x, y, r = circle
            circles.append(Circle(
                x=float(x) * self.scale_factor,
                y=float(y) * self.scale_factor,
                radius=float(r) * self.scale_factor
            ))

        return circles

    def _merge_lines(self, lines: List[Line], threshold: float = 10.0) -> List[Line]:
        """
        Merge lines that are close to each other.

        Args:
            lines: List of lines to merge
            threshold: Distance threshold for merging (in pixels)

        Returns:
            Merged list of lines
        """
        if not lines:
            return []

        # Simple merging: if two lines are very close and collinear, merge them
        merged = []
        used = set()

        for i, line1 in enumerate(lines):
            if i in used:
                continue

            # Check if this line can be merged with any other
            best_match = None
            best_dist = threshold

            for j, line2 in enumerate(lines[i+1:], start=i+1):
                if j in used:
                    continue

                # Check if lines are close and collinear
                dist = self._line_distance(line1, line2)
                if dist < best_dist:
                    best_dist = dist
                    best_match = j

            if best_match is not None:
                # Merge the two lines
                merged_line = self._merge_two_lines(line1, lines[best_match])
                merged.append(merged_line)
                used.add(i)
                used.add(best_match)
            else:
                merged.append(line1)
                used.add(i)

        return merged

    def _line_distance(self, line1: Line, line2: Line) -> float:
        """Calculate minimum distance between two line segments."""
        # Simplified: check endpoint distances
        d1 = np.sqrt((line1.x2 - line2.x1)**2 + (line1.y2 - line2.y1)**2)
        d2 = np.sqrt((line1.x1 - line2.x2)**2 + (line1.y1 - line2.y2)**2)
        return min(d1, d2)

    def _merge_two_lines(self, line1: Line, line2: Line) -> Line:
        """Merge two lines into one."""
        # Find the two farthest points
        points = [
            (line1.x1, line1.y1),
            (line1.x2, line1.y2),
            (line2.x1, line2.y1),
            (line2.x2, line2.y2)
        ]

        # Find max distance pair
        max_dist = 0
        p1, p2 = points[0], points[1]

        for i in range(len(points)):
            for j in range(i+1, len(points)):
                dist = np.sqrt((points[i][0] - points[j][0])**2 +
                             (points[i][1] - points[j][1])**2)
                if dist > max_dist:
                    max_dist = dist
                    p1, p2 = points[i], points[j]

        return Line(x1=p1[0], y1=p1[1], x2=p2[0], y2=p2[1])

    def to_dxf(self, elements: CADElements, output_path: str) -> bool:
        """
        Convert CAD elements to DXF file.

        Args:
            elements: CADElements to convert
            output_path: Path to save DXF file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create new DXF document
            doc = ezdxf.new('R2010')
            msp = doc.modelspace()

            # Add layers
            doc.layers.add('LINES', color=7)
            doc.layers.add('CIRCLES', color=3)

            # Add lines
            for line in elements.lines:
                msp.add_line(
                    (line.x1, line.y1),
                    (line.x2, line.y2),
                    dxfattribs={'layer': 'LINES'}
                )

            # Add circles
            for circle in elements.circles:
                msp.add_circle(
                    (circle.x, circle.y),
                    circle.radius,
                    dxfattribs={'layer': 'CIRCLES'}
                )

            # Save DXF file
            doc.saveas(output_path)
            return True

        except Exception as e:
            print(f"Error creating DXF: {e}")
            return False

    def process_image_to_dxf(
        self,
        binary_image: np.ndarray,
        output_path: str
    ) -> Tuple[bool, Optional[CADElements]]:
        """
        Complete pipeline: extract elements and save to DXF.

        Args:
            binary_image: Binary image to process
            output_path: Path to save DXF file

        Returns:
            Tuple of (success, elements)
        """
        # Extract elements
        elements = self.extract_elements(binary_image)

        # Convert to DXF
        success = self.to_dxf(elements, output_path)

        return success, elements if success else None
