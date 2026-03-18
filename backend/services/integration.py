"""Integration module - Bridges legacy code with new hybrid architecture."""

import numpy as np
from typing import List, Tuple, Optional
import logging

try:
    from cad_converter import CADElements, Polyline
    from services.cad_solver import CADSolver
    from config import Config
except ModuleNotFoundError:
    from backend.cad_converter import CADElements, Polyline
    from backend.services.cad_solver import CADSolver
    from backend.config import Config

logger = logging.getLogger(__name__)


def apply_cad_constraints_to_elements(
    elements: CADElements,
    config: Optional[Config] = None
) -> CADElements:
    """
    Apply CAD solver constraints to extracted elements.

    This function bridges the legacy CADConverter output with the new
    CAD solver module. It converts polylines to the format expected by
    CADSolver, applies constraints, and converts back.

    Args:
        elements: CADElements from legacy converter
        config: Configuration object (uses default if None)

    Returns:
        CADElements with constraints applied
    """
    if config is None:
        config = Config

    if not config.USE_CAD_SOLVER:
        logger.info("CAD solver disabled, returning original elements")
        return elements

    logger.info("Applying CAD solver constraints")

    # Convert Polyline objects to list format
    polylines_list = [pl.points for pl in elements.polylines]

    if not polylines_list:
        logger.info("No polylines to process")
        return elements

    # Initialize CAD solver
    solver = CADSolver(
        snap_radius=config.CAD_SNAP_RADIUS,
        angle_tolerance=config.CAD_ANGLE_TOLERANCE,
        min_inside_ratio=config.CAD_MIN_INSIDE_RATIO
    )

    # Apply constraints
    try:
        constrained_polylines = solver.apply_constraints(polylines_list)

        # Validate results
        if not solver.validate_polylines(constrained_polylines):
            logger.warning("Validation failed, returning original elements")
            return elements

        # Convert back to Polyline objects
        new_polylines = []
        for i, points in enumerate(constrained_polylines):
            original_pl = elements.polylines[i]
            new_polylines.append(Polyline(
                points=points,
                closed=original_pl.closed,
                layer=original_pl.layer
            ))

        # Create new CADElements with constrained polylines
        return CADElements(
            lines=elements.lines,
            circles=elements.circles,
            polylines=new_polylines,
            rectangles=elements.rectangles,
            canvas_height=elements.canvas_height,
            canvas_width=elements.canvas_width
        )

    except Exception as e:
        logger.error(f"Error applying CAD constraints: {e}", exc_info=True)
        logger.warning("Returning original elements due to error")
        return elements


def get_processing_stats(elements: CADElements) -> dict:
    """
    Get statistics about processed elements.

    Args:
        elements: CADElements to analyze

    Returns:
        Dictionary with statistics
    """
    total_vertices = sum(len(pl.points) for pl in elements.polylines)
    total_segments = sum(
        max(0, len(pl.points) - 1) + (1 if pl.closed and len(pl.points) >= 2 else 0)
        for pl in elements.polylines
    )

    return {
        'polylines': len(elements.polylines),
        'lines': len(elements.lines),
        'circles': len(elements.circles),
        'rectangles': len(elements.rectangles),
        'total_vertices': total_vertices,
        'total_segments': total_segments + len(elements.lines),
    }
