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

from importlib.abc import MetaPathFinder

class ImportRestrictor(MetaPathFinder):
    """A MetaPathFinder that restricts imports to a predefined list of modules.

    This is used to prevent the execution of arbitrary modules like 'os' or 'sys'
    in the sandbox environment.
    """

    def __init__(self, allowed_modules: frozenset[str]):
        """Initializes the ImportRestrictor with a set of allowed modules.

        Args:
            allowed_modules (frozenset[str]): A set of module names that are allowed to be imported.
        """
        self.allowed_modules = allowed_modules

    def find_spec(self, fullname, path=None, target=None):
        """Finds the spec for a module being imported, enforcing restrictions.

        Args:
            fullname (str): The fully qualified name of the module being imported.
            path (list, optional): The module search path.
            target (module, optional): The target module object.

        Returns:
            ModuleSpec or None: None to let the default machinery handle allowed imports.

        Raises:
            ImportError: If the module is not in the allowed modules list.
        """
        if not any(fullname == m or fullname.startswith(m + ".")
                   for m in self.allowed_modules):
            raise ImportError(
                f"Module '{fullname}' is not available in CircInspect. "
                f"Allowed modules: {', '.join(sorted(self.allowed_modules))}"
            )
        return None  # let default machinery handle allowed imports
