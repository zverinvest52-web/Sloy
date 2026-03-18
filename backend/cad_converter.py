"""CAD conversion module for Sloy project."""

import cv2
import numpy as np
import ezdxf
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Polyline:
    """Represents a polyline (optionally closed)."""
    points: List[Tuple[float, float]]
    closed: bool = False
    layer: str = "POLYLINES"


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
    canvas_height: Optional[float] = None
    canvas_width: Optional[float] = None


class CADConverter:
    """Converts binary images to DXF format."""

    min_contour_area: float = 80.0
    keep_area_ratio_of_max: float = 0.008
    approx_epsilon_ratio: float = 0.01
    hough_keep_top: int = 1
    hough_prefer_smaller: bool = True
    close_kernel_size: int = 3
    close_iterations: int = 1
    closed_point_dist_thresh: float = 3.0
    interior_line_min_length_ratio: float = 0.60
    border_touch_margin_px: int = 2
    interior_line_outside_margin_px: int = 3
    interior_line_min_inside_ratio: float = 0.90
    interior_line_allow_diagonal: bool = False
    interior_line_diagonal_tolerance_degrees: float = 7.0
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

        ang = self._line_angle_rad(line)
        ang = float((ang + np.pi) % np.pi)
        tol = float(np.deg2rad(self.snap_angle_degrees))

        if min(ang, abs(np.pi - ang)) <= tol:
            y = float((line.y1 + line.y2) / 2.0)
            return Line(x1=min_x, y1=y, x2=max_x, y2=y)

        if abs((np.pi / 2.0) - ang) <= tol:
            x = float((line.x1 + line.x2) / 2.0)
            return Line(x1=x, y1=min_y, x2=x, y2=max_y)

        p0 = np.array([line.x1, line.y1], dtype=np.float64)
        d = np.array([line.x2 - line.x1, line.y2 - line.y1], dtype=np.float64)
        norm = float(np.hypot(d[0], d[1]))
        if norm < 1e-9:
            return line
        d /= norm

        def intersect_infinite_with_segment(a: np.ndarray, b: np.ndarray) -> Optional[np.ndarray]:
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

        if len(intersections) < 2:
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
        """Extract (mostly closed) polylines from a binary image."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        def extract_from(binary_0_255: np.ndarray) -> List[Polyline]:
            contours, _ = cv2.findContours(binary_0_255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return []

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

                polylines.append(Polyline(points=points, closed=True, layer="POLYLINES"))

            return polylines

        _, bin_raw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
        polylines_raw = extract_from(bin_raw)

        k = np.ones((self.close_kernel_size, self.close_kernel_size), np.uint8)
        closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k, iterations=self.close_iterations)
        _, bin_closed = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY)
        polylines_closed = extract_from(bin_closed)

        if not polylines_raw:
            return polylines_closed
        if not polylines_closed:
            return polylines_raw

        raw_vertices = sum(len(pl.points) for pl in polylines_raw)
        closed_vertices = sum(len(pl.points) for pl in polylines_closed)
        return polylines_raw if raw_vertices >= closed_vertices else polylines_closed



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
        """Extract circles using contour circularity and Hough transform.

        Expects image with white drawing on black background.
        Uses both methods and merges results for better detection.
        """
        circles_contour = self._extract_circles_contour(image)
        circles_hough = self._extract_circles_hough(image)

        # Merge results, removing duplicates
        all_circles = circles_contour + circles_hough

        if not all_circles:
            return []

        # Remove near-duplicates
        unique_circles = []
        for c in all_circles:
            is_duplicate = False
            for existing in unique_circles:
                dist = np.sqrt((c.x - existing.x)**2 + (c.y - existing.y)**2)
                radius_diff = abs(c.radius - existing.radius)
                if dist < 5.0 * self.scale_factor and radius_diff < 5.0 * self.scale_factor:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_circles.append(c)

        return unique_circles


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

        if not circles:
            return []

        # Return all detected circles, not just the top 1
        # Sort by radius for consistency
        circles.sort(key=lambda c: c.radius)
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

        # Return all unique circles, sorted by radius
        dedup.sort(key=lambda c: c.radius)
        return dedup


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
        self.circle_min_radius = 3  # Lowered from 10 to detect small circles
        self.circle_max_radius = 500  # Increased from 200 for larger holes

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

        # If a "circle" got extracted as a polyline (common on noisy photos / thick strokes),
        # promote it into a true Circle so DXF/preview use an actual arc entity instead of
        # straight segments.
        circles_from_polylines: List[Circle] = []
        if polylines:
            kept_polylines: List[Polyline] = []
            for pl in polylines:
                pts_scaled = pl.points
                if len(pts_scaled) < 8:
                    kept_polylines.append(pl)
                    continue

                pts_px = (np.array(pts_scaled, dtype=np.float32) / float(self.scale_factor)).reshape(-1, 2)
                (cx, cy), r = cv2.minEnclosingCircle(pts_px)
                if r <= 0:
                    kept_polylines.append(pl)
                    continue

                d = np.sqrt((pts_px[:, 0] - float(cx)) ** 2 + (pts_px[:, 1] - float(cy)) ** 2)
                mean_dev = float(np.mean(np.abs(d - float(r))))

                bbox = cv2.boundingRect(pts_px.astype(np.int32))
                w, h = bbox[2], bbox[3]
                ar = float(w) / float(h) if h > 0 else 0.0

                if mean_dev <= 2.5 and 0.85 <= ar <= 1.15:
                    circles_from_polylines.append(
                        Circle(
                            x=float(cx) * self.scale_factor,
                            y=float(cy) * self.scale_factor,
                            radius=float(r) * self.scale_factor,
                        )
                    )
                else:
                    kept_polylines.append(pl)

            # If we found any, keep only one most plausible circle (consistent with existing behavior)
            if circles_from_polylines:
                circles_from_polylines.sort(key=lambda c: c.radius)
                circles_from_polylines = circles_from_polylines[:1]
                polylines = kept_polylines

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

        # 3) Circles: detect on BOTH residual and full image, then merge
        # This helps find circles that are close to contours
        circles_residual = self._extract_circles(residual)
        circles_full = self._extract_circles(working_image)

        # Merge and deduplicate
        all_circles = circles_residual + circles_full
        circles = []
        for c in all_circles:
            is_duplicate = False
            for existing in circles:
                dist = np.sqrt((c.x - existing.x)**2 + (c.y - existing.y)**2)
                radius_diff = abs(c.radius - existing.radius)
                if dist < 5.0 * self.scale_factor and radius_diff < 5.0 * self.scale_factor:
                    is_duplicate = True
                    break
            if not is_duplicate:
                circles.append(c)

        # Merge any circles we promoted from polylines.
        if circles_from_polylines:
            circles = circles_from_polylines

        # 4) Lines: prefer interior lines, but keep multiple good candidates (not just the longest).
        #    This helps photos where Hough splits the same "wall-to-wall" line into segments.
        lines: List[Line] = []
        lines_raw = self._extract_lines_hough(residual)
        if lines_raw:
            def seg_len(l: Line) -> float:
                return float(np.hypot(l.x2 - l.x1, l.y2 - l.y1))

            # Sort long-to-short and evaluate several candidates.
            lines_raw = sorted(lines_raw, key=seg_len, reverse=True)

            if polylines:
                pts = [p for pl in polylines for p in pl.points]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bbox_diag = float(np.hypot(max(xs) - min(xs), max(ys) - min(ys)))

                min_x, max_x = float(min(xs)), float(max(xs))
                min_y, max_y = float(min(ys)), float(max(ys))
                m = float(self.interior_line_outside_margin_px) * self.scale_factor

                def inside_ratio(l: Line) -> float:
                    n = 40
                    inside = 0
                    for i in range(n + 1):
                        t = i / n
                        x = l.x1 + (l.x2 - l.x1) * t
                        y = l.y1 + (l.y2 - l.y1) * t
                        if (min_x - m) <= x <= (max_x + m) and (min_y - m) <= y <= (max_y + m):
                            inside += 1
                    return inside / float(n + 1)

                def collect(min_len_ratio: float) -> List[Line]:
                    out: List[Line] = []
                    for raw in lines_raw[:50]:
                        cand = self._snap_and_extend_interior_line(raw, polylines)
                        if cand is None:
                            continue

                        if bbox_diag > 1e-6 and seg_len(raw) / bbox_diag < min_len_ratio:
                            continue

                        # Reject diagonal noise unless explicitly allowed.
                        ang = self._line_angle_rad(cand)
                        ang = float((ang + np.pi) % np.pi)
                        tol_axis = float(np.deg2rad(self.snap_angle_degrees))

                        is_h = min(ang, abs(np.pi - ang)) <= tol_axis
                        is_v = abs((np.pi / 2.0) - ang) <= tol_axis

                        if (not self.interior_line_allow_diagonal) and (not is_h) and (not is_v):
                            continue
                        if (not is_h) and (not is_v):
                            tol45 = float(np.deg2rad(self.interior_line_diagonal_tolerance_degrees))
                            if abs((np.pi / 4.0) - ang) > tol45 and abs((3.0 * np.pi / 4.0) - ang) > tol45:
                                continue

                        if inside_ratio(cand) < self.interior_line_min_inside_ratio:
                            continue

                        out.append(cand)
                    return out

                lines = collect(self.interior_line_min_length_ratio)

                # Photo fallback: if nothing survived the strict length ratio, relax it.
                if not lines:
                    lines = collect(0.20)

                # Merge collinear/near-duplicate segments.
                lines = self._merge_lines(lines)

                # If we ended up with multiple nearly-identical lines (common on thick strokes),
                # keep only the longest after merging.
                if len(lines) > 1:
                    lines = [max(lines, key=seg_len)]
            else:
                lines = [lines_raw[0]]

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
        Merge collinear lines that are close to each other.

        This significantly improves quality by combining fragmented lines
        (e.g., dashed lines detected as 50 segments → 1 line).

        Args:
            lines: List of lines to merge
            threshold: Distance threshold for merging (in scaled units)

        Returns:
            Merged list of lines
        """
        if not lines:
            return []

        logger.info(f"Merging {len(lines)} line segments...")

        # Convert angle tolerance to radians
        # Increased tolerance for diagonal lines
        angle_tolerance_deg = 10.0  # Increased from 5.0 for better diagonal line merging
        angle_tol_rad = np.deg2rad(angle_tolerance_deg)

        # Increased distance tolerance for better merging
        distance_tolerance = threshold * 2.0  # More lenient for diagonal lines

        # Calculate angles for all lines
        lines_with_angles = []
        for line in lines:
            angle = np.arctan2(line.y2 - line.y1, line.x2 - line.x1)
            # Normalize to [0, π)
            if angle < 0:
                angle += np.pi
            lines_with_angles.append((line, angle))

        # Sort by angle for efficient grouping
        lines_with_angles.sort(key=lambda x: x[1])

        merged = []
        used = set()

        for i, (line1, angle1) in enumerate(lines_with_angles):
            if i in used:
                continue

            # Start a new group with this line
            group = [line1]
            used.add(i)

            # Find all lines with similar angle
            for j, (line2, angle2) in enumerate(lines_with_angles[i+1:], start=i+1):
                if j in used:
                    continue

                # Check angle similarity
                angle_diff = abs(angle1 - angle2)
                if angle_diff > np.pi / 2:
                    angle_diff = np.pi - angle_diff

                if angle_diff > angle_tol_rad:
                    continue  # Different angle

                # Check if lines are collinear and close
                if self._are_collinear_and_close(line1, line2, distance_tolerance):
                    group.append(line2)
                    used.add(j)

            # Merge the group into a single line
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged_line = self._merge_line_group(group)
                merged.append(merged_line)

        logger.info(f"Merged to {len(merged)} line segments (reduced by {len(lines) - len(merged)})")
        return merged

    def _are_collinear_and_close(self, line1: Line, line2: Line, threshold: float) -> bool:
        """
        Check if two lines are collinear and close enough to merge.

        Args:
            line1: First line
            line2: Second line
            threshold: Maximum distance between lines

        Returns:
            True if lines should be merged
        """
        # Get all endpoints
        p1_start = np.array([line1.x1, line1.y1])
        p1_end = np.array([line1.x2, line1.y2])
        p2_start = np.array([line2.x1, line2.y1])
        p2_end = np.array([line2.x2, line2.y2])

        # Check if any endpoints are close
        distances = [
            np.linalg.norm(p1_end - p2_start),
            np.linalg.norm(p1_start - p2_end),
            np.linalg.norm(p1_end - p2_end),
            np.linalg.norm(p1_start - p2_start),
        ]

        min_dist = min(distances)
        if min_dist > threshold:
            return False

        # Check collinearity: distance from line2 endpoints to line1
        line1_vec = p1_end - p1_start
        line1_len = np.linalg.norm(line1_vec)

        if line1_len < 1e-6:
            return False

        line1_unit = line1_vec / line1_len

        # Distance from p2_start to line1
        vec_to_p2_start = p2_start - p1_start
        proj_length = np.dot(vec_to_p2_start, line1_unit)
        closest_point = p1_start + proj_length * line1_unit
        dist1 = np.linalg.norm(p2_start - closest_point)

        # Distance from p2_end to line1
        vec_to_p2_end = p2_end - p1_start
        proj_length = np.dot(vec_to_p2_end, line1_unit)
        closest_point = p1_start + proj_length * line1_unit
        dist2 = np.linalg.norm(p2_end - closest_point)

        # Both endpoints should be close to the line
        return max(dist1, dist2) < threshold

    def _merge_line_group(self, lines: List[Line]) -> Line:
        """
        Merge a group of collinear lines into a single line.

        Args:
            lines: List of collinear lines

        Returns:
            Single merged line
        """
        # Collect all endpoints
        points = []
        for line in lines:
            points.append(np.array([line.x1, line.y1]))
            points.append(np.array([line.x2, line.y2]))

        points = np.array(points)

        # Find the two farthest points (these will be the endpoints)
        max_dist = 0
        best_i, best_j = 0, 1

        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                dist = np.linalg.norm(points[i] - points[j])
                if dist > max_dist:
                    max_dist = dist
                    best_i, best_j = i, j

        p1 = points[best_i]
        p2 = points[best_j]

        return Line(
            x1=float(p1[0]),
            y1=float(p1[1]),
            x2=float(p2[0]),
            y2=float(p2[1])
        )

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
