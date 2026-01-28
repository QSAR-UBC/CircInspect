# Copyright 2025 UBC Quantum Software and Algorithms Research Lab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" This module has the fixtures to configure pytest to work with flask """

import pytest
from server.app import create_app


@pytest.fixture
def app():
    """Start the flask application in testing mode"""
    app = create_app({"TESTMODE": True})
    yield app


@pytest.fixture
def client(app):
    """Return the flask test client that simulates frontend requests"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """flask CLI runner for running tests on command-line with more options"""
    return app.test_cli_runner()
