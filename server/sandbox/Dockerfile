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

FROM python:3.14-slim

COPY server/sandbox/sandbox_requirements.txt /sandbox/sandbox_requirements.txt
RUN pip install --no-cache-dir -r /sandbox/sandbox_requirements.txt

RUN useradd -m -u 1000 sandbox

COPY server/sandbox/sandbox_server.py /sandbox/sandbox_server.py
COPY server/sandbox/import_restrictor.py /sandbox/import_restrictor.py
COPY server/sandbox/quantum_stack_trace.py /sandbox/quantum_stack_trace.py
COPY server/sandbox/allowed_modules.txt /sandbox/allowed_modules.txt
COPY server/helpers /sandbox/server/helpers
COPY server/command.py /sandbox/server/command.py
COPY server/code_security_validator.py /sandbox/server/code_security_validator.py

RUN chown -R sandbox:sandbox /sandbox

USER sandbox
WORKDIR /sandbox

# Internal port the Flask microserver listens on.`
# The actual host binding is done by `docker run -p 127.0.0.1:<port>:8080`
# so only the host loopback can reach this — not the internet or other hosts.
EXPOSE 8080

ENTRYPOINT ["python3", "/sandbox/sandbox_server.py"]