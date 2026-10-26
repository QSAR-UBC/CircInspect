# Performance Tests for CircInspect

## Use
Run each test as a usual Python script. E.g. `python3 test_depth.py`. Your test will generate a `.csv` file with the test name and the unix timestamp of the test start time.

Each script starts a single sandbox container for its entire run (reused across every rerun/data point) rather than one container per call. To share a single container across the whole suite of sequential (non-concurrency) tests, run `python3 run_all.py` instead of invoking the scripts individually. `test_concurrent_performance.py` and `test_concurrent_performance_cold.py` are excluded from `run_all.py` since they intentionally manage their own pool of containers to measure multi-client behaviour.
