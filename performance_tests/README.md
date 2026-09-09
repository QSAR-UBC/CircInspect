# Performance Tests for CircInspect

## Use
With the sandbox server running locally (`poetry run python -m server.sandbox.sandbox_server`), run each test as a usual Python script. E.g. `python3 test_depth.py`. Your test will generate a `.csv` file with the test name and the unix timestamp of the test start time, with columns `<resource>,total_time,processing_time,execution_time`: total client-side wall-clock time, CircInspect's own processing time, and PennyLane's circuit execution time.

Run `python3 run_all.py` to run every test in one go.

Use `results/plot_results.py <results.csv> ...` to turn any of those CSVs into scaling/breakdown plots.

Note: these tests characterize the performance of *your* local run, not the exact benchmark numbers reported in the CircInspect paper. See the top-level [README](../README.md#performance-benchmarks) if you want to reproduce those.
