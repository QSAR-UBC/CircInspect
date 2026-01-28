# Performance Tests for CircInspect

## Use
If you enabled database and auth in CircInspect, generate a new auth token via the email subsystem and put this new token to `TEST_TOKEN` string in `helpers.py`.

Run each test as a usual Python script. E.g. `python3 test_depth.py`. Your test will generate a `.csv` file with the test name and the unix timestamp of the test start time.
