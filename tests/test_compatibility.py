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

"""
This set of tests confirm that the application works with different submodules
of pennylane and commonly used libraries
"""

from tests.functions4testing import visCircuit


def test_numpy_array_in_params(client):
    """This test confirms that the use of numpy arrays as parameters do not
    result in errors. Numpy arrays are usually a problem because they are
    not JSON serializable.
    """
    with open("test_cases/numpy_in_params.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_devices_subpackage(client):
    """Device initialization can be done as qml.devices.DeviceName instead
    of usual qml.device("device.name"). This test confirms that the app
    is compatible with initializing devices using qml.devices subpackage.
    """
    with open("test_cases/qml_devices_subpackage.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_device_no_wires(client):
    """Pennylane allows users to initialize a device without specifying wires.
    Initial implementation of this app looked at the device initialization
    for the number of wires. Current implementation looks at all operations
    and the wires they act on.
    """
    with open("test_cases/qml_device_no_wires.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_device_no_wires_2(client):
    """This is a more complicated version of no wires test. A naive bugfix
    of the first one fails this because more functinality is dependent
    on the number of wires being specified. Current implementation finds
    the total number of wires if it is not specified.
    """
    with open("test_cases/qml_device_no_wires_2.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qft_with_range_wires(client):
    """When wires are specified as a range, they are not JSON serializable.
    JSON Encoder is modified to make sure all objects of the range class
    can be serialized. This test ensures the range() object is correctly
    serialiable.
    """
    with open("test_cases/qft_with_range_wires.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_midcircuit_measure(client):
    """Test that the app works with the midcircuit measurement functionality
    of the pennylane package. This failed initially because lambdas were
    not supported by pickle. Using dill instead of pickle for serialization
    fixed the issue.
    """
    with open("test_cases/qml_midcircuit_measure.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_default_mixed_device_support(client):
    """Confirm that default.mixed device does not result in no visualization"""
    with open("test_cases/qml_default_mixed_device_support.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_default_qutrit_device_support(client):
    """Confirm that default.qutrit device does not result in no visualization"""
    with open("test_cases/qml_default_qutrit_device_support.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None
