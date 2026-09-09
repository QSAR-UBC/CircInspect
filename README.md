# CircInspect
[![Ubuntu 22.04](https://img.shields.io/badge/Verified%20on-Ubuntu%2022.04-darkorange?logo=ubuntu)](https://ubuntu.com/)
[![macOS Tahoe (Apple M4)](https://img.shields.io/badge/Verified%20on-macOS%20Tahoe%20(M4)-lightgrey?logo=apple)](https://www.apple.com/macos/)

[CircInspect](https://circinspect.ece.ubc.ca/) is a visual tool for debugging quantum programs in PennyLane, developed by the [Quantum Software and Algorithms Research Lab](https://glassnotes.github.io/qsar.html) at UBC. It offers adaptive visualization of quantum circuits, enabling you to explore your quantum programs at varying levels of abstraction. You can zoom into subroutines, trace program structure and output (including for mid-circuit measurements), and set breakpoints to isolate the source of a bug.

## How to get started with CircInspect

You can try CircInspect right away [online](https://circinspect.ece.ubc.ca/), or install it locally (see [Installation](#installation) below).

CircInspect visualizes the structure of your circuit and updates it dynamically as you type, providing immediate feedback and deeper insight into how code translates into quantum circuits. It also includes an integrated debugger for monitoring structural and behavioural changes at breakpoints.

To use CircInspect, write PennyLane code containing a single QNode execution and paste or type it into the editor.

<img width="1918" height="926" alt="LiveDemo" src="https://github.com/user-attachments/assets/1971edea-e77c-42aa-a750-d331c0857815" />

With the debugger, you can isolate and examine individual quantum circuit components while monitoring changes in program structure and output at breakpoints. To set a breakpoint, click on the line number. You can then click "Start Debugger" and use the buttons to step through your code.

<img width="1918" height="926" alt="image" src="https://github.com/user-attachments/assets/8fee62e4-3cd3-4aa8-be69-05b62f2cb7db" />


You can selectively observe inputs to subroutines and main circuit output by using the tree structure of commands under the circuit visualization. Click on the fullscreen button and click on one of the nodes to create a popup with additional information. 

<img width="1918" height="926" alt="image" src="https://github.com/user-attachments/assets/9ac50b88-1d7e-44d8-a4ad-239c2a9799af" />

To see the output of the QNode, click on the top-most node of the command tree structure to see the output in the side panel popup. Alternatively, you can hover over the same top-most node. 

<img width="1918" height="926" alt="image" src="https://github.com/user-attachments/assets/3ecee8f1-63cb-4ef2-9e5f-e8fe59fca10b" />


You can also postselect on mid-circuit measurement values while the debugger is inactive. This will allow you to simulate the effect of postselection on the output of the circuit. To do so, click the fullscreen button on the command tree structure and click on the mid-circuit measurement node you want to apply a postselection value to. 

<img width="1918" height="926" alt="PostSelectionDemo" src="https://github.com/user-attachments/assets/8f191fe4-fca4-474d-8ce1-84bf0eecead7" />

### Working with transforms

If your QNode has one or more [PennyLane transforms](https://docs.pennylane.ai/en/stable/code/qml_transforms.html) applied to it (built-in transforms such as `qp.transforms.merge_rotations`, or your own custom transform defined with `@qp.transform`), CircInspect shows a transform timeline next to the circuit visualization while the debugger is inactive. The timeline has a step for "Base" (your circuit before any transforms) followed by one step per transform, in the order the decorators are applied. Click or drag along the timeline to see the circuit as it looks at each stage of the transform pipeline. The timeline is locked while a debugging session is active.

Only transforms applied as decorators (e.g. `@qp.transforms.merge_rotations` above your `@qp.qnode` decorator) are picked up. Transforms applied inline (e.g. `circuit = qp.transforms.merge_rotations(circuit)`) are not detected and won't appear on the timeline.

<img width="1918" height="926" alt="transforms_recording_circinspect" src="https://github.com/user-attachments/assets/0aac9853-2bde-47f2-aea1-cacd0edd7340" />

We are researching how quantum developers debug their programs and CircInspect is a part of that effort. If you're building algorithms with PennyLane, please give it a try and send us your feedback.


## Installation

CircInspect is [freely available online](https://circinspect.ece.ubc.ca/). The instructions below are for local installation.

CircInspect is developed with React for the front-end, while the back-end is powered by Python and Flask. Some UI elements and code editor setup were inspired by the blog "[How to Build a Code Editor with React that Compiles and Executes in 40+ Languages](https://www.freecodecamp.org/news/how-to-build-react-based-code-editor/)", written by [Manu Arora](https://manuarora.in/).

This is the public, local-only version of CircInspect: everything runs on your own machine, with no Docker, database, or authentication required.

### Requirements

- Python 3.14, managed via [Poetry](https://python-poetry.org/)
- Node.js and npm. Use an older/LTS release (e.g. 22.x or 24.x) rather than the newest available version

CircInspect works on Linux (verified on Ubuntu 22.04, see badge above), macOS (verified on an Apple M4 MacBook running macOS Tahoe 26.6.2), and WSL.

To install the backend server requirements, go into `CircInspect` directory (project root) and run
```
poetry install
```

To install the frontend server, install Node.js, go into `CircInspect/client` directory and run
```
npm i
```

## Usage
To run the development servers, open two terminal windows.

1. On the first one, go into `CircInspect` directory (project root) and run
```
poetry run python -m server.sandbox.sandbox_server
```
2. On the second one, go into `CircInspect/client` directory and run
```
npm start
```

## Troubleshooting

**`npm start` fails with `Invalid options object ... options.allowedHosts[0] should be a non-empty string`:**
This is a known, unresolved issue in `react-scripts`' dev server setup (see [react/create-react-app#12304](https://github.com/react/create-react-app/issues/12304)). It happens because the dev server tries to auto-detect your machine's LAN IP address to restrict which hosts can connect to it, and fails to find one on some network setups (VPN-only connections, no active Wi-Fi/Ethernet, etc.). Work around it by running:
```
DANGEROUSLY_DISABLE_HOST_CHECK=true npm start
```
Despite the name, this is safe for local development: it only disables the dev server's check on which hostnames are allowed to connect to it on your machine. It has no effect on the production build and doesn't expose anything beyond what the dev server already serves.

## Development and Testing 
Follow the instructions in [tests/README.md](tests/README.md) to run automated tests.
Follow the instructions in [performance_tests/README.md](performance_tests/README.md) to run performance tests that characterize the runtime of CircInspect. To reproduce the exact benchmark numbers reported in the paper, contact the [QSAR Lab](https://glassnotes.github.io/qsar.html); those were measured on a different internal deployment.

## How to Contribute to CircInspect
CircInspect is available open source under the Apache 2.0 License. Contributions are welcome. Please follow the instructions in the following link to contribute: [How to contribute?](https://github.com/QSAR-UBC/CircInspect-dev/blob/main/.github/CONTRIBUTING.md)

## Reference
The primary developers of CircInspect are Mushahid Khan
([@mushahidkhan835](https://github.com/mushahidkhan835)), Chirag Raisingh ([@ChiragRaisingh](https://github.com/ChiragRaisingh)) and Cihan Bosnali ([@CihanBosnali](https://github.com/CihanBosnali)).

The authors acknowledge funding from the NSERC CREATE in Quantum Computing
Program (grant number 543245), NSERC Alliance Quantum, NSERC Alliance International Catalyst Quantum, UBC 4YF, and
UBC WLIURA programs. Thanks to Prashant Nair, QSAR Lab members, and the PennyLane team at Xanadu
for testing and providing feedback on CircInspect.

If you use CircInspect as part of your workflow, we would appreciate if you cite it using the BibTeX below.
```
@INPROCEEDINGS{10821435,
  author={Khan, Mushahid and Nair, Prashant J. and Di Matteo, Olivia},
  booktitle={2024 IEEE International Conference on Quantum Computing and Engineering (QCE)}, 
  title={CircInspect: Integrating Visual Circuit Analysis, Abstraction, and Real-Time Development in Quantum Debugging}, 
  year={2024},
  volume={01},
  number={},
  pages={1000-1006},
  doi={10.1109/QCE60285.2024.00119}}

```

