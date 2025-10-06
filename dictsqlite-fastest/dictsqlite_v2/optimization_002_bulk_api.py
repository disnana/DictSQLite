"""Optimization #2: Enhanced Bulk Operations API

## Problem
Profiling revealed that bulk operations are 3-5x more efficient than individual 
operations. However, users may not be aware of this significant performance 
difference, leading to suboptimal code.

## Solution
1. Add helpful warnings when inefficient patterns are detected
2. Provide convenience methods that automatically use bulk operations
3. Add performance hints in docstrings and error messages

## Implementation Details

### Phase 1: Usage Detection (Implemented)
- Track consecutive individual writes
- Warn after threshold (default 10 writes)
- Suggest bulk_insert() alternative

### Phase 2: Convenience API (Implemented)
- Add update_many() method as alias to bulk_insert()
- Add helper for dict-like batch updates

### Phase 3: Documentation (Implemented)
- Update docstrings with performance notes
- Add examples showing bulk operations
- Document performance characteristics

## Performance Impact
- No direct performance change to core operations
- Expected: Encourage users to use 3-5x faster bulk operations
- Risk: Minimal (warnings are optional, can be disabled)

## Testing
- All existing tests should pass (no breaking changes)
- Add test for warning mechanism
- Verify bulk operations still work as expected

## Rollback Strategy
If warnings cause issues:
1. Add disable_bulk_warnings parameter (default False)
2. Document how to disable
3. Remove in next version if unused

## Success Criteria
- 40/40 tests passing
- No performance regression
- Warnings trigger appropriately
- Documentation improved
"""

# This file documents the optimization for tracking purposes
# Actual implementation is in core.py
