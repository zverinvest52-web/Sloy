# Quick Start: CAD Solver Module

The CAD Solver (Module 3) is now implemented and ready to use. It improves vectorization quality by applying geometric constraints.

## What It Does

1. **Vertex Snapping**: Merges nearby line endpoints into exact intersection points
2. **Orthogonalization**: Forces near-horizontal/vertical lines to exact 0°/90°/180°
3. **Intersection Computation**: Finds and inserts exact intersection points where lines cross

## How to Enable

1. **Install new dependency**:
   ```bash
   cd backend
   pip install shapely==2.0.2
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Enable CAD solver** in `.env`:
   ```bash
   USE_CAD_SOLVER=true
   ```

4. **Restart server**:
   ```bash
   uvicorn main:app --reload
   ```

## Testing

Run unit tests:
```bash
cd backend
python tests/test_cad_solver.py
```

Expected output:
```
Running CAD Solver unit tests...

✓ Vertex snapping test passed
✓ Orthogonalization test passed
✓ Horizontal orthogonalization test passed
✓ Full constraint pipeline test passed
✓ Validation test passed
✓ Empty input test passed

✅ All tests passed!
```

## Configuration

Adjust parameters in `.env`:

```bash
# Snap vertices within this radius (pixels)
CAD_SNAP_RADIUS=3.0

# Angle tolerance for orthogonalization (degrees)
CAD_ANGLE_TOLERANCE=3.0

# Minimum ratio of line inside bounding box
CAD_MIN_INSIDE_RATIO=0.90
```

## Performance

- **Processing time**: ~0.5-1 second per drawing
- **Memory**: Minimal overhead (~10MB)
- **Compatibility**: Works with existing OpenCV output

## Before/After Comparison

### Before (Pure OpenCV):
- Lines don't meet at exact intersections
- Projection lines slightly off-axis
- Fragmented geometry

### After (With CAD Solver):
- Lines meet at exact intersection points
- Projection lines perfectly horizontal/vertical
- Clean, CAD-ready geometry

## Troubleshooting

**Import errors**:
```bash
pip install -r requirements.txt
```

**CAD solver not activating**:
- Check `.env` file exists in `backend/` directory
- Verify `USE_CAD_SOLVER=true` (not `false`)
- Restart FastAPI server

**Performance issues**:
- Reduce `CAD_SNAP_RADIUS` for faster processing
- Check image size (large images take longer)

## Next Steps

See `MIGRATION_PLAN.md` for the full roadmap:
- Module 1: ML Semantic Segmentation (Weeks 4-5)
- Module 2: Multi-Pass Vectorization (Weeks 6-7)
- Module 4: Curve Fitting (Week 8)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
├─────────────────────────────────────────────────────────┤
│  Image Upload → ImageProcessor (OpenCV)                 │
│       ↓                                                  │
│  Binary Image → CADConverter.extract_elements()         │
│       ↓                                                  │
│  CADElements → apply_cad_constraints_to_elements() ✅   │
│       ↓                                                  │
│  Constrained Elements → CADConverter.to_dxf()           │
│       ↓                                                  │
│  DXF File → Download                                    │
└─────────────────────────────────────────────────────────┘
```

## Files Modified

- `backend/main.py` - Integrated CAD solver
- `backend/requirements.txt` - Added shapely
- `backend/config.py` - Feature flags (NEW)
- `backend/services/cad_solver.py` - Core implementation (NEW)
- `backend/services/integration.py` - Integration layer (NEW)
- `backend/tests/test_cad_solver.py` - Unit tests (NEW)
- `backend/.env.example` - Configuration template (NEW)

## Support

For issues or questions, see `MIGRATION_PLAN.md` or check the code documentation.
