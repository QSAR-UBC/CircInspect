# Copyright 2026 UBC Quantum Software and Algorithms Research Lab

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
This module provides the stack trace needed to record information from
code execution
"""

import sys
import pennylane as qp
import inspect


class QuantumStackTrace:
    """Trace stack that runs with code execution

    Attributes:
        info_unexpanded: list of objects generated (without preprocessing)
        info: list of objects generated per code line
    """

    def __init__(self):
        self.info_unexpanded = []
        self.info = []

    def __enter__(self):
        sys.settrace(self.trace)
        return self

    def __exit__(self, *args):
        sys.settrace(None)

    def trace(self, frame, event, arg):
        """A function given to exec() to run with the code execution and
            record information about the state of the code execution after
            each line.

        Returns:
            Itself (to be used by code execution to trace the next line)
        """

        ins = None
        if (
            frame.f_code.co_name == "device"
            or frame.f_code.co_filename == "<string>"
            or type(arg) is qp.queuing.AnnotatedQueue
        ):
            ins_raw = inspect.getargvalues(frame)

            ins = ins_raw._replace(locals=dict(ins_raw.locals))

            self.info.append(
                (
                    frame.f_code.co_name,
                    frame.f_lineno,
                    arg,
                    frame.f_code.co_filename,
                    event,
                    ins,
                )
            )

        return self.trace

    def get_info_expanded(self):
        """In the case that info cannot be automatically expanded,
        this function can be run to indivudually add pieces of
        information to self.info
        """
        self.info = []
        for frame, event, arg in self.info_unexpanded:
            self.info.append(
                [
                    frame.f_code.co_name,
                    frame.f_lineno,
                    arg,
                    frame.f_code.co_filename,
                    event,
                    inspect.getargvalues(frame),
                ]
            )

    def get_stack(self):
        """Get the stack of PennyLane operations recorded while trace(self) was running
            with the code.

        Returns:
            Dictionary with a list of quantum and classical operation that ran
            when the code was executed.
        """
        res = {}
        for _, _, arg, _, _, _ in self.info:
            if type(arg) is qp.queuing.AnnotatedQueue:
                res["commands"] = arg
                break
        return res

    def get_qnode(self):
        """Get the PennyLane QNode encountered while trace(self) was running with the code. 

        Returns: 
            PennyLane QNode if one was found during execution, 
            otherwise None. 
        """
        for _, _, arg, _, _, argvals in self.info:
            if type(arg) is qp.QNode:
                return arg
            if argvals is not None and argvals.locals:
                for val in argvals.locals.values():
                    if type(val) is qp.QNode:
                        return val
        return None