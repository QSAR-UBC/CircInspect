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
import ast

class CodeSecurityValidator(ast.NodeVisitor):
    """AST-based security validator that catches bypass techniques."""
    
    BANNED_IMPORTS = {"os", "sys", "subprocess", "shutil", "pathlib", "urllib", "requests", "csv", "socket", "ctypes"}
    BANNED_ATTRS = {"__subclasses__", "__globals__", "__code__", "__builtins__", "__dict__", "__class__"}
    BANNED_CALLS = {"exec", "eval", "compile", "open", "breakpoint", "__import__"}

    def __init__(self):
        self.error = None

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in self.BANNED_IMPORTS:
                self.error = [f"No module named: {alias.name}", f" line {node.lineno}"]
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in self.BANNED_IMPORTS:
                self.error = [f"No module named: {node.module}", f" line {node.lineno}"]
                return
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in self.BANNED_ATTRS:
            self.error = [f"Access to restricted attribute '{node.attr}' is disabled.", f" line {node.lineno}"]
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.BANNED_CALLS:
            self.error = [f"Function '{node.func.id}()' is disabled.", f" line {node.lineno}"]
            return
        self.generic_visit(node)