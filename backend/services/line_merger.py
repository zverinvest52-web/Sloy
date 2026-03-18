"""Enhanced CAD Converter with line merging for better quality."""

import cv2
import numpy as np
from typing import List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LineSegment:
    """Line segment with endpoints."""
    x1: float
    y1: float
    x2: float
    y2: float

    def length(self) -> float:
        """Calculate line length."""
        return np.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)

    def angle(self) -> float:
        """Calculate line angle in radians."""
        return np.arctan2(self.y2 - self.y1, self.x2 - self.x1)

    def midpoint(self) -> tuple:
        """Calculate midpoint."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


def merge_collinear_segments(lines: List[LineSegment],
                             angle_tolerance: float = 5.0,
                             distance_tolerance: float = 10.0) -> List[LineSegment]:
    """
    Merge collinear line segments that are close to each other.

    This significantly improves quality by combining fragmented lines
    (e.g., dashed lines detected as 50 segments → 1 line).

    Args:
        lines: List of line segments
        angle_tolerance: Maximum angle difference in degrees
        distance_tolerance: Maximum gap distance between segments

    Returns:
        Merged list of line segments
    """
    if not lines:
        return []

    logger.info(f"Merging {len(lines)} line segments...")

    # Convert angle tolerance to radians
    angle_tol_rad = np.deg2rad(angle_tolerance)

    # Sort lines by angle for efficient grouping
    lines_with_angles = [(line, line.angle()) for line in lines]
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
            if angle_diff > np.pi:
                angle_diff = 2 * np.pi - angle_diff

            if angle_diff > angle_tol_rad:
                break  # Sorted by angle, so no more matches

            # Check if lines are collinear and close
            if are_collinear_and_close(line1, line2, distance_tolerance):
                group.append(line2)
                used.add(j)

        # Merge the group into a single line
        if len(group) == 1:
            merged.append(group[0])
        else:
            merged_line = merge_line_group(group)
            merged.append(merged_line)

    logger.info(f"Merged to {len(merged)} line segments (reduction: {len(lines) - len(merged)})")
    return merged


def are_collinear_and_close(line1: LineSegment, line2: LineSegment,
                            distance_tolerance: float) -> bool:
    """
    Check if two lines are collinear and close enough to merge.

    Args:
        line1: First line segment
        line2: Second line segment
        distance_tolerance: Maximum distance between lines

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
    if min_dist > distance_tolerance:
        return False

    # Check collinearity: distance from line2 endpoints to line1
    # Using point-to-line distance formula
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
    return max(dist1, dist2) < distance_tolerance


def merge_line_group(lines: List[LineSegment]) -> LineSegment:
    """
    Merge a group of collinear lines into a single line.

    Args:
        lines: List of collinear line segments

    Returns:
        Single merged line segment
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

    return LineSegment(
        x1=float(p1[0]),
        y1=float(p1[1]),
        x2=float(p2[0]),
        y2=float(p2[1])
    )


# Example usage in CADConverter:
#
# def _extract_lines_hough(self, image: np.ndarray) -> List[Line]:
#     """Extract lines using Hough Line Transform with merging."""
#     # ... existing HoughLinesP code ...
#
#     # Convert to LineSegment objects
#     segments = [LineSegment(x1=l.x1, y1=l.y1, x2=l.x2, y2=l.y2) for l in lines]
#
#     # Merge collinear segments
#     merged_segments = merge_collinear_segments(
#         segments,
#         angle_tolerance=5.0,
#         distance_tolerance=10.0 * self.scale_factor
#     )
#
#     # Convert back to Line objects
#     return [Line(x1=s.x1, y1=s.y1, x2=s.x2, y2=s.y2) for s in merged_segments]
