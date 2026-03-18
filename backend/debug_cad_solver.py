"""Debug script to visualize CAD solver improvements."""

import cv2
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cad_converter import CADConverter
from services.integration import apply_cad_constraints_to_elements
from config import Config
import logging

logging.basicConfig(level=logging.INFO)


def create_test_drawing():
    """Create a test drawing with common issues."""
    img = np.ones((600, 800), dtype=np.uint8) * 255

    # Draw a rectangle with slightly off-axis lines
    # Top line: nearly horizontal but 2 degrees off
    cv2.line(img, (100, 100), (700, 110), 0, 2)
    # Right line: nearly vertical but 2 degrees off
    cv2.line(img, (700, 110), (710, 500), 0, 2)
    # Bottom line: nearly horizontal
    cv2.line(img, (710, 500), (100, 510), 0, 2)
    # Left line: nearly vertical
    cv2.line(img, (100, 510), (100, 100), 0, 2)

    # Add an interior line that should snap to edges
    cv2.line(img, (400, 103), (403, 507), 0, 2)

    return img


def visualize_elements(elements, output_path, title=""):
    """Visualize CAD elements."""
    h = int(elements.canvas_height) if elements.canvas_height else 600
    w = int(elements.canvas_width) if elements.canvas_width else 800

    vis = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw polylines in blue
    for pl in elements.polylines:
        pts = np.array(pl.points, dtype=np.int32)
        cv2.polylines(vis, [pts], pl.closed, (255, 0, 0), 2)

        # Mark vertices with circles
        for pt in pts:
            cv2.circle(vis, tuple(pt), 3, (0, 0, 255), -1)

    # Draw lines in green
    for line in elements.lines:
        pt1 = (int(line.x1), int(line.y1))
        pt2 = (int(line.x2), int(line.y2))
        cv2.line(vis, pt1, pt2, (0, 255, 0), 2)
        cv2.circle(vis, pt1, 3, (0, 0, 255), -1)
        cv2.circle(vis, pt2, 3, (0, 0, 255), -1)

    # Add title
    cv2.putText(vis, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    cv2.imwrite(output_path, vis)
    print(f"Saved visualization to {output_path}")


if __name__ == "__main__":
    print("Creating test drawing...")
    img = create_test_drawing()
    cv2.imwrite("test_drawing.png", img)

    print("\nExtracting elements WITHOUT CAD solver...")
    converter = CADConverter(scale_factor=1.0)
    elements_before = converter.extract_elements(img)

    print(f"Before: {len(elements_before.polylines)} polylines, {len(elements_before.lines)} lines")
    visualize_elements(elements_before, "before_cad_solver.png", "Before CAD Solver")

    print("\nApplying CAD solver...")
    elements_after = apply_cad_constraints_to_elements(elements_before, Config)

    print(f"After: {len(elements_after.polylines)} polylines, {len(elements_after.lines)} lines")
    visualize_elements(elements_after, "after_cad_solver.png", "After CAD Solver")

    print("\nComparison:")
    print(f"  Polylines: {len(elements_before.polylines)} -> {len(elements_after.polylines)}")
    print(f"  Lines: {len(elements_before.lines)} -> {len(elements_after.lines)}")

    if elements_before.polylines and elements_after.polylines:
        before_vertices = sum(len(pl.points) for pl in elements_before.polylines)
        after_vertices = sum(len(pl.points) for pl in elements_after.polylines)
        print(f"  Total vertices: {before_vertices} -> {after_vertices}")

    print("\nCheck the output images:")
    print("  - test_drawing.png (original)")
    print("  - before_cad_solver.png (without CAD solver)")
    print("  - after_cad_solver.png (with CAD solver)")
    print("\nLook for:")
    print("  - Lines should be perfectly horizontal/vertical")
    print("  - Vertices should snap to exact intersections")
    print("  - Red dots show vertex positions")
