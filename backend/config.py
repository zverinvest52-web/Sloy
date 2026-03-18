"""Configuration module for Sloy - Feature flags and settings."""

import os
from typing import Optional


class Config:
    """Application configuration with feature flags."""

    # Feature flags for hybrid architecture modules
    USE_ML_SEGMENTATION: bool = os.getenv('USE_ML_SEGMENTATION', 'false').lower() == 'true'
    USE_CAD_SOLVER: bool = os.getenv('USE_CAD_SOLVER', 'false').lower() == 'true'
    USE_CURVE_FITTING: bool = os.getenv('USE_CURVE_FITTING', 'false').lower() == 'true'
    USE_MULTI_PASS_VECTORIZATION: bool = os.getenv('USE_MULTI_PASS_VECTORIZATION', 'false').lower() == 'true'

    # CAD Solver parameters
    CAD_SNAP_RADIUS: float = float(os.getenv('CAD_SNAP_RADIUS', '3.0'))
    CAD_ANGLE_TOLERANCE: float = float(os.getenv('CAD_ANGLE_TOLERANCE', '3.0'))
    CAD_MIN_INSIDE_RATIO: float = float(os.getenv('CAD_MIN_INSIDE_RATIO', '0.90'))

    # Performance settings
    MAX_IMAGE_SIZE: int = int(os.getenv('MAX_IMAGE_SIZE', '3000'))
    PROCESSING_TIMEOUT: int = int(os.getenv('PROCESSING_TIMEOUT', '30'))

    @classmethod
    def get_active_modules(cls) -> dict:
        """Return dictionary of active feature flags."""
        return {
            'ml_segmentation': cls.USE_ML_SEGMENTATION,
            'cad_solver': cls.USE_CAD_SOLVER,
            'curve_fitting': cls.USE_CURVE_FITTING,
            'multi_pass_vectorization': cls.USE_MULTI_PASS_VECTORIZATION,
        }

    @classmethod
    def log_config(cls) -> str:
        """Return configuration summary for logging."""
        active = cls.get_active_modules()
        active_features = [k for k, v in active.items() if v]
        return f"Active modules: {', '.join(active_features) if active_features else 'none (legacy mode)'}"
