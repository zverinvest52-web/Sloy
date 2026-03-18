"""CAD Solver - Module 3: Geometric Constraints for Engineering Drawings.

This module applies CAD-level geometric constraints to vectorized drawings:
1. Vertex snapping: Merge nearby endpoints into exact intersection points
2. Orthogonalization: Force near-axis lines to exact 0°/90°/180°
3. Intersection computation: Find and insert exact intersection points

Performance: ~0.5-1s for typical drawings with 100-500 lines.
"""

import numpy as np
from scipy.spatial import KDTree
from shapely.geometry import LineString, Point
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class CADSolver:
    """Applies geometric constraints to improve CAD precision."""

    def __init__(
        self,
        snap_radius: float = 3.0,
        angle_tolerance: float = 3.0,
        min_inside_ratio: float = 0.90
    ):
        """
        Initialize CAD solver.

        Args:
            snap_radius: Maximum distance for vertex snapping (in same units as coordinates)
            angle_tolerance: Angle tolerance in degrees for orthogonalization
            min_inside_ratio: Minimum ratio of line inside bounding box (for validation)
        """
        self.snap_radius = snap_radius
        self.angle_tolerance = angle_tolerance
        self.min_inside_ratio = min_inside_ratio

    def apply_constraints(
        self,
        polylines: List[List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Apply all CAD constraints to polylines.

        Args:
            polylines: List of polylines, where each polyline is a list of (x, y) points

        Returns:
            Constrained polylines with snapped vertices and orthogonalized lines
        """
        if not polylines:
            return polylines

        logger.info(f"Applying CAD constraints to {len(polylines)} polylines")

        # Step 1: Snap vertices at intersections
        polylines = self.snap_vertices(polylines)

        # Step 2: Orthogonalize near-axis lines
        polylines = self.orthogonalize_lines(polylines)

        # Step 3: Compute and insert exact intersections
        polylines = self.compute_line_intersections(polylines)

        logger.info("CAD constraints applied successfully")
        return polylines

    def snap_vertices(
        self,
        polylines: List[List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Merge nearby endpoints into exact intersection points using KD-Tree.

        This ensures that lines that should meet at a point actually share
        the exact same coordinates, which is critical for CAD software.

        Args:
            polylines: List of polylines

        Returns:
            Polylines with snapped vertices
        """
        if not polylines:
            return polylines

        # Collect all endpoints with references
        endpoints = []
        endpoint_refs = []  # (polyline_idx, vertex_idx, position)

        for i, polyline in enumerate(polylines):
            if len(polyline) < 2:
                continue

            # Start point
            endpoints.append(polyline[0])
            endpoint_refs.append((i, 0, 'start'))

            # End point
            endpoints.append(polyline[-1])
            endpoint_refs.append((i, len(polyline) - 1, 'end'))

        if len(endpoints) < 2:
            return polylines

        endpoints_array = np.array(endpoints, dtype=np.float64)

        # Build KD-Tree for fast spatial queries
        tree = KDTree(endpoints_array)

        # Find clusters of nearby points
        clusters = tree.query_ball_tree(tree, r=self.snap_radius)

        # Merge each cluster to its centroid
        visited = set()
        for i, cluster in enumerate(clusters):
            if i in visited:
                continue

            if len(cluster) <= 1:
                visited.add(i)
                continue

            # Mark all points in cluster as visited
            visited.update(cluster)

            # Compute exact intersection point (centroid)
            cluster_points = endpoints_array[cluster]
            intersection = cluster_points.mean(axis=0)

            # Update all polylines in this cluster
            for idx in cluster:
                poly_idx, vertex_idx, position = endpoint_refs[idx]
                polylines[poly_idx][vertex_idx] = (float(intersection[0]), float(intersection[1]))

        return polylines

    def orthogonalize_lines(
        self,
        polylines: List[List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Force near-horizontal/vertical lines to exact 0°/90°/180°.

        Engineering drawings typically have axis-aligned projection lines.
        This function snaps lines that are nearly horizontal or vertical
        to exact alignment.

        Args:
            polylines: List of polylines

        Returns:
            Polylines with orthogonalized segments
        """
        if not polylines:
            return polylines

        angle_tol_rad = np.deg2rad(self.angle_tolerance)

        for polyline in polylines:
            for i in range(len(polyline) - 1):
                p1 = np.array(polyline[i], dtype=np.float64)
                p2 = np.array(polyline[i + 1], dtype=np.float64)

                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]

                # Skip zero-length segments
                if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                    continue

                # Compute angle (0 to π)
                angle = np.arctan2(dy, dx)
                angle = (angle + np.pi) % np.pi

                # Check if near horizontal (0° or 180°)
                if angle < angle_tol_rad or angle > (np.pi - angle_tol_rad):
                    # Force same Y coordinate
                    polyline[i + 1] = (polyline[i + 1][0], polyline[i][1])

                # Check if near vertical (90°)
                elif abs(angle - np.pi / 2) < angle_tol_rad:
                    # Force same X coordinate
                    polyline[i + 1] = (polyline[i][0], polyline[i + 1][1])

        return polylines

    def compute_line_intersections(
        self,
        polylines: List[List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """
        Find and insert intersection points where lines cross.

        This ensures that crossing lines have a vertex at their intersection,
        which is important for CAD topology.

        Args:
            polylines: List of polylines

        Returns:
            Polylines with intersection points inserted
        """
        if not polylines:
            return polylines

        # Convert polylines to line segments
        segments = []
        segment_refs = []  # (polyline_idx, segment_idx)

        for i, polyline in enumerate(polylines):
            for j in range(len(polyline) - 1):
                segments.append(LineString([polyline[j], polyline[j + 1]]))
                segment_refs.append((i, j))

        if len(segments) < 2:
            return polylines

        # Find intersections between all pairs of segments
        intersections_to_insert = []  # (polyline_idx, segment_idx, point)

        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                # Skip segments from the same polyline that are adjacent
                poly_i, seg_i = segment_refs[i]
                poly_j, seg_j = segment_refs[j]

                if poly_i == poly_j and abs(seg_i - seg_j) <= 1:
                    continue

                # Compute intersection
                try:
                    intersection = segments[i].intersection(segments[j])

                    if intersection.is_empty:
                        continue

                    # Only handle point intersections (not overlapping segments)
                    if intersection.geom_type == 'Point':
                        x, y = intersection.x, intersection.y

                        # Check if intersection is not at segment endpoints
                        # (endpoints are already handled by vertex snapping)
                        seg_i_start = segments[i].coords[0]
                        seg_i_end = segments[i].coords[1]
                        seg_j_start = segments[j].coords[0]
                        seg_j_end = segments[j].coords[1]

                        eps = 1e-6
                        is_endpoint_i = (
                            (abs(x - seg_i_start[0]) < eps and abs(y - seg_i_start[1]) < eps) or
                            (abs(x - seg_i_end[0]) < eps and abs(y - seg_i_end[1]) < eps)
                        )
                        is_endpoint_j = (
                            (abs(x - seg_j_start[0]) < eps and abs(y - seg_j_start[1]) < eps) or
                            (abs(x - seg_j_end[0]) < eps and abs(y - seg_j_end[1]) < eps)
                        )

                        if not is_endpoint_i:
                            intersections_to_insert.append((poly_i, seg_i, (x, y)))

                        if not is_endpoint_j:
                            intersections_to_insert.append((poly_j, seg_j, (x, y)))

                except Exception as e:
                    logger.warning(f"Error computing intersection: {e}")
                    continue

        # Insert intersection points into polylines
        # Sort by polyline_idx and segment_idx in reverse order to maintain indices
        intersections_to_insert.sort(key=lambda x: (x[0], x[1]), reverse=True)

        for poly_idx, seg_idx, point in intersections_to_insert:
            # Insert point after segment start (at seg_idx + 1)
            if poly_idx < len(polylines) and seg_idx + 1 <= len(polylines[poly_idx]):
                polylines[poly_idx].insert(seg_idx + 1, point)

        return polylines

    def validate_polylines(
        self,
        polylines: List[List[Tuple[float, float]]]
    ) -> bool:
        """
        Validate that polylines are well-formed after constraint application.

        Args:
            polylines: List of polylines to validate

        Returns:
            True if valid, False otherwise
        """
        for i, polyline in enumerate(polylines):
            if len(polyline) < 2:
                logger.warning(f"Polyline {i} has fewer than 2 points")
                return False

            # Check for NaN or infinite values
            for j, point in enumerate(polyline):
                if not (np.isfinite(point[0]) and np.isfinite(point[1])):
                    logger.warning(f"Polyline {i}, point {j} has invalid coordinates: {point}")
                    return False

        return True
