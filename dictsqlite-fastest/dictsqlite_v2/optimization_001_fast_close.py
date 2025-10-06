"""Optimization #1: Non-blocking close() with optional background flush

This optimization addresses the CRITICAL threading bottleneck identified in profiling.

Problem: close() spends 70-80% of time waiting for background flush thread to join
Solution: Make background flush optional and implement non-blocking close

Expected Impact: 70-80% reduction in close() time
Risk: Medium (threading changes)
"""

# The optimization will be to add a parameter to DictSQLiteV2 __init__:
#   enable_background_flush: bool = False  (default False to avoid blocking)
#
# Or better: Add a fast_close parameter that skips thread join
#   fast_close: bool = True (default True for performance)
#
# This gives users control over the tradeoff between close() speed and
# ensuring all background operations complete.

# Implementation approach:
# 1. Add fast_close parameter to DictSQLiteV2.__init__
# 2. Store it as instance variable
# 3. Pass it through to parent class or handle in our close() override
# 4. When fast_close=True, set stop event but don't wait for thread
# 5. Thread will finish naturally in background

# This maintains data integrity because:
# - _flush_write_buffer() is still called synchronously in close()
# - Background thread only does periodic flushes
# - Any pending data is flushed before close returns

print("""
Optimization Plan: Fast Close Option

1. Add 'fast_close' parameter (default True)
2. When True: Skip thread.join() in close()
3. When False: Wait for thread (current behavior)
4. Always call _flush_write_buffer() to ensure data safety

Benefits:
- 70-80% faster close() for most use cases
- Maintains data integrity (flush before return)
- User can choose safety vs speed
- Backward compatible (can default to fast)

Implementation in core.py:
- Override __init__ to add fast_close parameter
- Override close() to skip join when fast_close=True
""")
