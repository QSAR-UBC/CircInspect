# Tests

# Running Tests
1. Run the code execution server on port 5001 by running this command inside `CircInspect/` directory:
```
  flask --app execserver.app run --debug --port=5001
```
2. Run all automated tests using Pytest by running this command inside `CircInspect/tests` directory:
```
  pytest
```
Run it as `pytest -v` to get more information in case of an error.

# Test Groups
| Test Group | # of Tests | Description |
|------------|------------|-------------|
| `test_compatibility` | 6 | confirms that the application works with different submodules of `pennylane` and commonly used libraries such as `numpy` |
| `test_concurrency`| 6 | confirms that the application works concurrently for mutiple users without holding global state related to a user's session on the backend. |
| `test_malicious` | 9 | confirms that backend will safely raise an error instead of running user code that includes malicious activities such as reading a file, writing a file and accessing the web. |
| `test_malicious_breaking` | 5 | confirms that backend will safely raise an error instead of running user code that can break the code execution server. |
| `test_parsing` | 3 | confirms that code parsing works. |
| `test_helpers` | 12 | unit tests for helper functions. |
| `test_misc` | 3 | confirms that fixed bugs that do not belong to any test groups are not reintroduced. |

