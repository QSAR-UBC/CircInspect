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
This module provides the stack trace needed to record information from
code execution
"""

import sys
import pennylane as qml
import inspect


class MagicallyTraceStack:
    """Trace stack that runs with code execution

    Attributes:
        info_unexpanded: list of objects generated (without preprocessing)
        info: list of objects generated per code line
        lines_to_ignore: list of lines to ignore
    """

    def __init__(self, lines_to_ignore):
        self.info_unexpanded = []
        self.info = []
        self.lines_to_ignore = lines_to_ignore

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
            or type(arg) is qml.queuing.AnnotatedQueue
        ):
            ins = inspect.getargvalues(frame)
            self.info.append(
                (frame.f_code.co_name, frame.f_lineno, arg, frame.f_code.co_filename, event, ins)
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
        """Get the stack of operations recorded while trace(self) was running
            with the code.

        Returns:
            Dictionary with a list of quantum and classical operation that ran
            when the code was executed.
        """
        res = {}
        got_queue = False
        for co_name, lineno, arg, filename, event, argvals in self.info:
            if type(arg) is qml.queuing.AnnotatedQueue and not got_queue:
                res["commands"] = arg
                got_queue = True

        return res
