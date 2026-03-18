"""Unit tests for CAD Solver module."""

import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cad_solver import CADSolver


def test_vertex_snapping():
    """Test that nearby endpoints are merged."""
    solver = CADSolver(snap_radius=3.0)

    # Create two lines with endpoints 2px apart (should snap)
    line1 = [(0.0, 0.0), (10.0, 0.0)]
    line2 = [(10.0, 2.0), (20.0, 2.0)]

    polylines = [line1, line2]
    snapped = solver.snap_vertices(polylines)

    # Endpoints should now be identical
    assert snapped[0][-1] == snapped[1][0], f"Expected endpoints to snap, got {snapped[0][-1]} and {snapped[1][0]}"
    print("[PASS] Vertex snapping test passed")


def test_orthogonalization():
    """Test that near-vertical/horizontal lines are forced to exact alignment."""
    solver = CADSolver(angle_tolerance=3.0)

    # Create nearly vertical line (89.5°)
    line = [(0.0, 0.0), (0.1, 10.0)]

    polylines = [line]
    ortho = solver.orthogonalize_lines(polylines)

    # Should be exactly vertical now (same X coordinate)
    assert ortho[0][0][0] == ortho[0][1][0], f"Expected vertical line, got {ortho[0]}"
    print("[PASS] Orthogonalization test passed")


def test_horizontal_orthogonalization():
    """Test horizontal line orthogonalization."""
    solver = CADSolver(angle_tolerance=3.0)

    # Create nearly horizontal line (2°)
    line = [(0.0, 0.0), (10.0, 0.35)]

    polylines = [line]
    ortho = solver.orthogonalize_lines(polylines)

    # Should be exactly horizontal now (same Y coordinate)
    assert ortho[0][0][1] == ortho[0][1][1], f"Expected horizontal line, got {ortho[0]}"
    print("[PASS] Horizontal orthogonalization test passed")


def test_apply_constraints():
    """Test full constraint pipeline."""
    solver = CADSolver(snap_radius=3.0, angle_tolerance=3.0)

    # Create a simple drawing with two nearly-perpendicular lines
    line1 = [(0.0, 0.0), (10.1, 0.2)]  # Nearly horizontal
    line2 = [(10.0, 0.0), (10.2, 10.0)]  # Nearly vertical

    polylines = [line1, line2]
    constrained = solver.apply_constraints(polylines)

    # Validate results
    assert solver.validate_polylines(constrained), "Validation failed"

    # Check that lines are orthogonalized
    # Line 1 should be horizontal
    assert abs(constrained[0][0][1] - constrained[0][1][1]) < 0.01, "Line 1 should be horizontal"

    # Line 2 should be vertical
    assert abs(constrained[1][0][0] - constrained[1][1][0]) < 0.01, "Line 2 should be vertical"

    print("[PASS] Full constraint pipeline test passed")


def test_validation():
    """Test polyline validation."""
    solver = CADSolver()

    # Valid polylines
    valid = [[(0.0, 0.0), (10.0, 10.0)]]
    assert solver.validate_polylines(valid), "Valid polylines should pass"

    # Invalid: too few points
    invalid_short = [[(0.0, 0.0)]]
    assert not solver.validate_polylines(invalid_short), "Single-point polyline should fail"

    # Invalid: NaN values
    invalid_nan = [[(0.0, 0.0), (float('nan'), 10.0)]]
    assert not solver.validate_polylines(invalid_nan), "NaN values should fail"

    print("[PASS] Validation test passed")


def test_no_polylines():
    """Test that empty input is handled gracefully."""
    solver = CADSolver()

    result = solver.apply_constraints([])
    assert result == [], "Empty input should return empty output"

    print("[PASS] Empty input test passed")


if __name__ == "__main__":
    print("Running CAD Solver unit tests...\n")

    try:
        test_vertex_snapping()
        test_orthogonalization()
        test_horizontal_orthogonalization()
        test_apply_constraints()
        test_validation()
        test_no_polylines()

        print("\n[SUCCESS] All tests passed!")

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
