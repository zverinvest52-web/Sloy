"""
CAD conversion module for Sloy project.
Converts processed images to DXF format using ezdxf.
"""

import cv2
import numpy as np
import ezdxf  # pyright: ignore[reportPrivateImportUsage]
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Polyline:
    """Represents a polyline (optionally closed)."""
    points: List[Tuple[float, float]]
    closed: bool = False
    layer: str = "POLYLINES"  # allows simple categorization


def _scale_points(points: np.ndarray, scale: float) -> List[Tuple[float, float]]:
    """Convert Nx2 array of pixel points to scaled tuples."""
    return [(float(x) * scale, float(y) * scale) for x, y in points]


def _dedupe_consecutive(points: List[Tuple[float, float]], eps: float = 1e-6) -> List[Tuple[float, float]]:
    """Remove consecutive duplicate points."""
    if not points:
        return points
    out = [points[0]]
    for p in points[1:]:
        if abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    return out


logger = logging.getLogger(__name__)


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
class Rectangle:
    """Represents a rectangle."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class CADElements:
    """Container for extracted CAD elements."""
    lines: List[Line] = field(default_factory=list)
    circles: List[Circle] = field(default_factory=list)
    polylines: List[Polyline] = field(default_factory=list)
    rectangles: List[Rectangle] = field(default_factory=list)
    # DXF coordinate system has Y going "up", while image coordinates have Y going
    # "down". When provided, we flip Y as: y_dxf = canvas_height - y.
    canvas_height: Optional[float] = None
    canvas_width: Optional[float] = None


class CADConverter:
    """Converts binary images to DXF format."""

    # Contour-based extraction is preferred for closed shapes because it produces
    # connected geometry suitable for DXF polylines (instead of many Hough segments).
    min_contour_area: float = 80.0
    # Keep only contours that are a meaningful fraction of the largest contour.
    # This filters UI/text noise on clean screenshots.
    keep_area_ratio_of_max: float = 0.008
    approx_epsilon_ratio: float = 0.01
    # When using HoughCircles fallback, take only the most plausible circle.
    hough_keep_top: int = 1
    # If Hough proposes circles with wildly different radii (often outer+inner),
    # we prefer the smaller one (usually the actual hole/round element in line art).
    hough_prefer_smaller: bool = True
    # If you need fewer LINE entities for orthogonal shapes, increase
    # approx_epsilon_ratio (e.g. 0.08–0.12) for that specific case.


    close_kernel_size: int = 3
    close_iterations: int = 1
    closed_point_dist_thresh: float = 3.0

    # Heuristic: only keep an "interior" line if it's long enough relative to the
    # detected outer geometry bbox.
    interior_line_min_length_ratio: float = 0.60
    border_touch_margin_px: int = 2

    # Snap nearly-horizontal/vertical lines to perfect axis alignment.
    snap_angle_degrees: float = 3.0

    def _line_angle_rad(self, line: Line) -> float:
        return float(np.arctan2(line.y2 - line.y1, line.x2 - line.x1))

    def _snap_and_extend_interior_line(self, line: Line, polylines: List[Polyline]) -> Line:
        """Snap near-axis interior line and extend it until it touches outer geometry."""
        if not polylines:
            return line

        pts = [p for pl in polylines for p in pl.points]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        min_x, max_x = float(min(xs)), float(max(xs))
        min_y, max_y = float(min(ys)), float(max(ys))

        # Direction and angle normalization
        ang = self._line_angle_rad(line)
        # Map angle to [0, pi)
        ang = float((ang + np.pi) % np.pi)
        tol = float(np.deg2rad(self.snap_angle_degrees))

        # Snap to horizontal
        if min(ang, abs(np.pi - ang)) <= tol:
            y = float((line.y1 + line.y2) / 2.0)
            return Line(x1=min_x, y1=y, x2=max_x, y2=y)

        # Snap to vertical
        if abs((np.pi / 2.0) - ang) <= tol:
            x = float((line.x1 + line.x2) / 2.0)
            return Line(x1=x, y1=min_y, x2=x, y2=max_y)

        # Otherwise: extend along its direction until it intersects the outer polyline.
        # We compute intersections of the infinite line with all outer polyline segments.
        p0 = np.array([line.x1, line.y1], dtype=np.float64)
        d = np.array([line.x2 - line.x1, line.y2 - line.y1], dtype=np.float64)
        norm = float(np.hypot(d[0], d[1]))
        if norm < 1e-9:
            return line
        d /= norm

        def intersect_infinite_with_segment(a: np.ndarray, b: np.ndarray) -> Optional[np.ndarray]:
            """Return intersection point if infinite line p0+t*d crosses segment a->b."""
            v = b - a
            denom = d[0] * v[1] - d[1] * v[0]
            if abs(float(denom)) < 1e-12:
                return None
            w = a - p0
            t = (w[0] * v[1] - w[1] * v[0]) / denom
            u = (w[0] * d[1] - w[1] * d[0]) / denom
            if float(u) < -1e-6 or float(u) > 1.0 + 1e-6:
                return None
            return p0 + t * d

        intersections: List[np.ndarray] = []
        for pl in polylines:
            p = pl.points
            for i in range(len(p) - 1):
                a = np.array(p[i], dtype=np.float64)
                b = np.array(p[i + 1], dtype=np.float64)
                ip = intersect_infinite_with_segment(a, b)
                if ip is not None:
                    intersections.append(ip)
            if pl.closed and len(p) >= 2:
                a = np.array(p[-1], dtype=np.float64)
                b = np.array(p[0], dtype=np.float64)
                ip = intersect_infinite_with_segment(a, b)
                if ip is not None:
                    intersections.append(ip)

        # Fallback: intersect with bbox if polygon intersections failed
        if len(intersections) < 2:
            # Intersect with rectangle bbox
            rect = [
                (np.array([min_x, min_y], dtype=np.float64), np.array([max_x, min_y], dtype=np.float64)),
                (np.array([max_x, min_y], dtype=np.float64), np.array([max_x, max_y], dtype=np.float64)),
                (np.array([max_x, max_y], dtype=np.float64), np.array([min_x, max_y], dtype=np.float64)),
                (np.array([min_x, max_y], dtype=np.float64), np.array([min_x, min_y], dtype=np.float64)),
            ]
            for a, b in rect:
                ip = intersect_infinite_with_segment(a, b)
                if ip is not None:
                    intersections.append(ip)

        if len(intersections) >= 2:
            # Pick farthest pair
            best_i, best_j = 0, 1
            best_dist = -1.0
            for i in range(len(intersections)):
                for j in range(i + 1, len(intersections)):
                    dist = float(np.hypot(intersections[i][0] - intersections[j][0], intersections[i][1] - intersections[j][1]))
                    if dist > best_dist:
                        best_dist = dist
                        best_i, best_j = i, j
            a = intersections[best_i]
            b = intersections[best_j]
            return Line(x1=float(a[0]), y1=float(a[1]), x2=float(b[0]), y2=float(b[1]))

        return line


    def _extract_polylines(self, image: np.ndarray) -> List[Polyline]:
        """Extract (mostly closed) polylines from a binary image.

        Expects image with white drawing on black background.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Close small gaps so contours become connected.
        k = np.ones((self.close_kernel_size, self.close_kernel_size), np.uint8)
        closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k, iterations=self.close_iterations)

        # Ensure binary 0/255
        _, bin_img = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter tiny contours relative to the largest one.
        # On clean drawings we typically want only the main geometry contours.
        max_area = 0.0
        for cnt in contours:
            a = float(cv2.contourArea(cnt))
            if a > max_area:
                max_area = a
        dynamic_min_area = max(self.min_contour_area, self.keep_area_ratio_of_max * max_area)

        polylines: List[Polyline] = []
        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < dynamic_min_area:
                continue

            peri = cv2.arcLength(cnt, True)
            eps = self.approx_epsilon_ratio * peri
            approx = cv2.approxPolyDP(cnt, eps, True)

            pts = approx.reshape(-1, 2)
            points = _dedupe_consecutive(_scale_points(pts, self.scale_factor))
            if len(points) < 2:
                continue

            # Contours returned by findContours are closed by definition.
            polylines.append(Polyline(points=points, closed=True, layer="POLYLINES"))

        return polylines


    def _polylines_to_lines(self, polylines: List[Polyline]) -> List[Line]:
        """Fallback: convert polylines into individual LINE segments."""
        lines: List[Line] = []
        for pl in polylines:
            pts = pl.points
            for i in range(len(pts) - 1):
                (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                lines.append(Line(x1=x1, y1=y1, x2=x2, y2=y2))
            if pl.closed and len(pts) >= 2:
                (x1, y1), (x2, y2) = pts[-1], pts[0]
                lines.append(Line(x1=x1, y1=y1, x2=x2, y2=y2))
        return lines


    def _preprocess_for_hough(self, image: np.ndarray) -> np.ndarray:
        """Small blur to stabilize Hough transforms."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return cv2.GaussianBlur(gray, (3, 3), 0)


    def _extract_lines_hough(self, image: np.ndarray) -> List[Line]:
        """Extract lines using Hough Line Transform."""
        img = self._preprocess_for_hough(image)
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines_raw = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.hough_min_line_length,
            maxLineGap=self.hough_max_line_gap,
        )

        if lines_raw is None:
            return []

        lines = []
        for line in lines_raw:
            x1, y1, x2, y2 = line[0]
            lines.append(
                Line(
                    x1=float(x1) * self.scale_factor,
                    y1=float(y1) * self.scale_factor,
                    x2=float(x2) * self.scale_factor,
                    y2=float(y2) * self.scale_factor,
                )
            )

        return self._merge_lines(lines)


    def _extract_lines(self, image: np.ndarray) -> List[Line]:
        """Extract lines.

        Prefer contour-derived polylines when possible; use Hough as a fallback.
        """
        polylines = self._extract_polylines(image)
        if polylines:
            return self._polylines_to_lines(polylines)
        return self._extract_lines_hough(image)


    def _extract_circles(self, image: np.ndarray) -> List[Circle]:
        """Extract circles using contour circularity.

        Expects image with white drawing on black background.
        """
        circles = self._extract_circles_contour(image)
        if circles:
            return circles
        return self._extract_circles_hough(image)


    def _extract_circles_contour(self, image: np.ndarray) -> List[Circle]:
        """Primary circle detector: contour circularity + simple radial fit."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bin_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        circles_raw: List[Circle] = []
        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < max(self.min_contour_area, 150.0):
                continue

            peri = float(cv2.arcLength(cnt, True))
            if peri <= 0:
                continue

            circularity = 4.0 * np.pi * area / (peri * peri)
            if circularity < 0.80:
                continue

            (cx, cy), r = cv2.minEnclosingCircle(cnt)
            if r <= 0:
                continue

            # Radial fit check: average deviation of contour points from radius
            pts = cnt.reshape(-1, 2).astype(np.float32)
            d = np.sqrt((pts[:, 0] - float(cx)) ** 2 + (pts[:, 1] - float(cy)) ** 2)
            mean_dev = float(np.mean(np.abs(d - float(r))))
            if mean_dev > 2.5:
                continue

            circles_raw.append(
                Circle(
                    x=float(cx) * self.scale_factor,
                    y=float(cy) * self.scale_factor,
                    radius=float(r) * self.scale_factor,
                )
            )

        # De-duplicate near-identical circles (common on thick strokes)
        circles: List[Circle] = []
        for c in circles_raw:
            merged = False
            for existing in circles:
                if (
                    abs(c.x - existing.x) <= 3.0 * self.scale_factor
                    and abs(c.y - existing.y) <= 3.0 * self.scale_factor
                    and abs(c.radius - existing.radius) <= 3.0 * self.scale_factor
                ):
                    merged = True
                    break
            if not merged:
                circles.append(c)

        return circles


    def _extract_circles_hough(self, image: np.ndarray) -> List[Circle]:
        """Fallback circle detector for cases where contour fit fails (thick strokes)."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(
            img,
            cv2.HOUGH_GRADIENT,
            dp=self.circle_dp,
            minDist=self.circle_min_dist,
            param1=self.circle_param1,
            param2=self.circle_param2,
            minRadius=self.circle_min_radius,
            maxRadius=self.circle_max_radius,
        )

        if circles is None:
            return []

        out: List[Circle] = []
        for x, y, r in circles[0]:
            out.append(
                Circle(
                    x=float(x) * self.scale_factor,
                    y=float(y) * self.scale_factor,
                    radius=float(r) * self.scale_factor,
                )
            )

        # De-dup near-identical
        dedup: List[Circle] = []
        for c in out:
            if any(
                abs(c.x - e.x) <= 3.0 * self.scale_factor
                and abs(c.y - e.y) <= 3.0 * self.scale_factor
                and abs(c.radius - e.radius) <= 3.0 * self.scale_factor
                for e in dedup
            ):
                continue
            dedup.append(c)

        if not dedup:
            return []

        # Prefer smaller radius if enabled (common when Hough finds inner+outer).
        if self.hough_prefer_smaller:
            dedup.sort(key=lambda c: c.radius)
        else:
            dedup.sort(key=lambda c: c.radius, reverse=True)

        return dedup[: max(1, int(self.hough_keep_top))]


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
        """Extract polylines, lines, and circles from a (mostly) binary image.

        Input convention: black drawing on white background.
        Internally we operate on white drawing on black background.
        """
        # Invert if needed
        if np.mean(binary_image) > 127:
            working_image = cv2.bitwise_not(binary_image)
        else:
            working_image = binary_image.copy()

        # 1) External closed geometry as polylines
        polylines = self._extract_polylines(working_image)

        # Heuristic: screenshots with multiple separate contours often benefit from
        # stronger polygon simplification to avoid too many tiny segments.
        if len(polylines) >= 3 and self.approx_epsilon_ratio < 0.10:
            old_eps = self.approx_epsilon_ratio
            self.approx_epsilon_ratio = 0.10
            try:
                polylines = self._extract_polylines(working_image)
            finally:
                self.approx_epsilon_ratio = old_eps

        # 2) Build residual image by erasing extracted polylines
        residual = working_image
        if polylines:
            mask = np.zeros_like(working_image)
            erase_thickness = max(3, self.close_kernel_size * 2 + 1)
            for pl in polylines:
                pts = np.array(pl.points, dtype=np.float32)
                pts = np.round(pts / self.scale_factor).astype(np.int32)  # back to pixels
                if len(pts) >= 2:
                    cv2.polylines(mask, [pts], isClosed=True, color=(255,), thickness=erase_thickness)
            residual = cv2.bitwise_and(working_image, cv2.bitwise_not(mask))

        # 3) Circles from residual (prevents corner/outline interference)
        circles = self._extract_circles(residual)

        # 4) Lines: for clean drawings we usually want interior lines only.
        #    Use Hough on residual and keep the longest segment.
        lines: List[Line] = []
        lines_raw = self._extract_lines_hough(residual)
        if lines_raw:
            def seg_len(l: Line) -> float:
                return float(np.hypot(l.x2 - l.x1, l.y2 - l.y1))

            longest = max(lines_raw, key=seg_len)

            # Keep only if it plausibly spans the shape (wall-to-wall).
            if polylines:
                pts = [p for pl in polylines for p in pl.points]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bbox_diag = float(np.hypot(max(xs) - min(xs), max(ys) - min(ys)))
                if bbox_diag > 1e-6 and seg_len(longest) / bbox_diag >= self.interior_line_min_length_ratio:
                    lines = [self._snap_and_extend_interior_line(longest, polylines)]
            else:
                lines = [longest]

        # Fallback if no polylines were extracted
        if not polylines and not lines:
            lines = self._extract_lines_hough(working_image)

        canvas_height = float(working_image.shape[0]) * self.scale_factor
        canvas_width = float(working_image.shape[1]) * self.scale_factor
        return CADElements(
            lines=lines,
            circles=circles,
            polylines=polylines,
            canvas_height=canvas_height,
            canvas_width=canvas_width,
        )


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
            doc.layers.add('POLYLINES', color=7)
            doc.layers.add('LINES', color=7)
            doc.layers.add('CIRCLES', color=3)

            def fy(y: float) -> float:
                if elements.canvas_height is None:
                    return y
                return float(elements.canvas_height - y)

            # Export polylines as individual LINE entities (AutoCAD-friendly counts)
            for pl in elements.polylines:
                pts = pl.points
                for i in range(len(pts) - 1):
                    (x1, y1), (x2, y2) = pts[i], pts[i + 1]
                    msp.add_line((x1, fy(y1)), (x2, fy(y2)), dxfattribs={'layer': 'LINES'})
                if pl.closed and len(pts) >= 2:
                    (x1, y1), (x2, y2) = pts[-1], pts[0]
                    msp.add_line((x1, fy(y1)), (x2, fy(y2)), dxfattribs={'layer': 'LINES'})

            # Interior / fallback lines
            for line in elements.lines:
                msp.add_line(
                    (line.x1, fy(line.y1)),
                    (line.x2, fy(line.y2)),
                    dxfattribs={'layer': 'LINES'}
                )

            # Circles
            for circle in elements.circles:
                msp.add_circle(
                    (circle.x, fy(circle.y)),
                    circle.radius,
                    dxfattribs={'layer': 'CIRCLES'}
                )

            # Save DXF file
            doc.saveas(output_path)
            return True

        except Exception as e:
            logger.error(f"Error creating DXF: {e}")
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

    def export_to_dxf_r12(self, elements: CADElements, output_path: str) -> bool:
        """
        Export CAD elements to DXF R12 format using POLYLINE.

        Args:
            elements: CADElements to export
            output_path: Path to save DXF file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create new DXF document in R12 format
            doc = ezdxf.new('R12')
            msp = doc.modelspace()

            # Add layers
            doc.layers.add('POLYLINES', color=7)
            doc.layers.add('LINES', color=7)
            doc.layers.add('CIRCLES', color=3)
            doc.layers.add('RECTANGLES', color=5)

            # Add polylines (R12 compatible)
            for pl in elements.polylines:
                points = [(x, y, 0) for x, y in pl.points]
                msp.add_polyline2d(points, close=pl.closed, dxfattribs={'layer': pl.layer})

            # Add lines as POLYLINE (R12 compatible)
            for line in elements.lines:
                points = [(line.x1, line.y1, 0), (line.x2, line.y2, 0)]
                msp.add_polyline2d(points, dxfattribs={'layer': 'LINES'})

            # Add rectangles as closed POLYLINE (R12 compatible)
            for rect in elements.rectangles:
                points = [
                    (rect.x, rect.y, 0),
                    (rect.x + rect.width, rect.y, 0),
                    (rect.x + rect.width, rect.y + rect.height, 0),
                    (rect.x, rect.y + rect.height, 0)
                ]
                msp.add_polyline2d(points, close=True, dxfattribs={'layer': 'RECTANGLES'})

            # Add circles as CIRCLE
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
            logger.error(f"Error creating DXF R12: {e}")
            return False
