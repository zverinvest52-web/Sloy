# CAD Solver Issue Report

## Problem

User reported that enabling CAD Solver (Module 3) causes severe geometry corruption:
- "делает полную хрень" (makes complete garbage)
- "он все окружностями делает" (it makes everything into circles)

## Status

**DISABLED** - `USE_CAD_SOLVER=false` in .env

## What CAD Solver Does

The CAD solver processes polylines to:
1. Snap vertices within 3px radius to merge endpoints
2. Orthogonalize near-horizontal/vertical lines (within 3° tolerance)
3. Compute exact line intersections
4. Convert standalone lines to polylines for processing

## Potential Issues

1. **Line-to-Polyline Conversion Bug** (lines 54-57 in integration.py):
   - Converts standalone Line objects to polylines
   - Then clears the lines list (line 102)
   - May be causing geometry loss or corruption

2. **Vertex Snapping Too Aggressive**:
   - 3px snap radius might be merging unrelated geometry
   - Could be collapsing small features

3. **Orthogonalization Breaking Curves**:
   - Forces lines to 0°/90°/180° within 3° tolerance
   - May be destroying intentionally angled geometry

4. **Intersection Computation Issues**:
   - Uses shapely for line intersection
   - May be creating spurious intersections

## Investigation Needed

1. Get example DXF file that shows the issue
2. Compare DXF output with CAD solver ON vs OFF
3. Check if circles are being created or if polylines are being corrupted
4. Review integration.py lines 54-102 for line conversion logic
5. Test with different snap_radius and angle_tolerance values

## Temporary Solution

CAD Solver is disabled by default. Users can enable it by setting:
```
USE_CAD_SOLVER=true
```

But this is NOT recommended until the issue is fixed.

## Next Steps

1. User should provide example drawing that shows the problem
2. Debug with logging enabled to see what CAD solver is doing
3. Consider making CAD solver optional per-element (only process polylines, skip lines)
4. Add more validation to detect when CAD solver corrupts geometry
