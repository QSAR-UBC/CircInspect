# CircInspect
[![Ubuntu 22.04](https://img.shields.io/badge/Verified%20on-Ubuntu%2022.04-darkorange?logo=ubuntu)](https://ubuntu.com/)
[![Fedora 38](https://img.shields.io/badge/Verified%20on-Fedora%2038-blue?logo=fedora)](https://fedoraproject.org/)

The [Quantum Software and Algorithms Research Lab](https://glassnotes.github.io/qsar.html) at UBC introduces [CircInspect](https://circinspect.ece.ubc.ca/), the first visual tool for debugging quantum programs in PennyLane.

![image](https://github.com/user-attachments/assets/f0a810a5-0d6d-4157-91c9-89afb6f5c2f7)


Users can selectively observe inputs to subroutines and abstract away irrelevant details, enhancing program understanding.

![image](https://github.com/user-attachments/assets/a9b8a75f-2477-4e5e-90a0-bac401294cd5)

![image](https://github.com/user-attachments/assets/6a9d0660-257e-457e-b395-c62a6b6c428a)

Additionally, CircInspect offers a real-time visualization mode that dynamically updates the quantum circuit visualization as the code is modified.

![2025-04-27 20-10-11](https://github.com/user-attachments/assets/c359d720-2c96-455e-a07e-12bd9fb72e9b)

CircInspect is built by the [Quantum Software and Algorithms Research Lab](https://github.com/QSAR-UBC)  at the [Univeristy of British Columbia](https://www.ubc.ca/). More details on CircInspect can be found in our [QCE 24 conference paper](https://ieeexplore.ieee.org/document/10821435).

## Installation

CircInspect is [freely available online](https://circinspect.ece.ubc.ca/). The instructions below are for local installation.

CircInspect is developed with React for the front-end, while the back-end is powered by Python and Flask. Some UI elements and code editor setup were inspired by the blog "[How to Build a Code Editor with React that Compiles and Executes in 40+ Languages](https://www.freecodecamp.org/news/how-to-build-react-based-code-editor/)", written by [Manu Arora](https://manuarora.in/).  MongoDB is used to track how users interact with the application, specifically to monitor which features they use and how often they engage with different parts of CircInspect.

To install the backend server requirements, go into `CircInspect` directory (project root) and run
```
poetry install
```

To install the frontend server, install Node.js, go into `CircInspect/client` directory and run
```
npm i
```

To install the database, follow the instructions in the [MongoDB website](https://www.mongodb.com/docs/manual/administration/install-community/).

## Usage
To run the development servers:
1. If MongoDB is not running, run below command on your terminal to start MongoDB:
```
sudo systemctl start mongod
```
2. To check that MongoDB is running, run
```
sudo systemctl status mongod
```
3. Open three terminal windows

4. On the first one, go into `CircInspect` directory (project root) and run
```
poetry run flask --app server.app run --debug
```
5. On the second one, go into `CircInspect` directory (project root) and run
```
poetry run flask --app execserver.app run --debug --port=5001
```
6. On the third one, go into `CircInspect/client` directory and run
```
npm start
```

## Configurations
To enable authentication, change the `noAuth` flag in client/src/App.js to `false` and change the `NOAUTH` flag on server/app.py to `False`.

## Development and Testing 
Follow the instructions in [tests/README.md](tests/README.md) to run automated tests.
Follow the instructions in [performance_tests/README.md](performance_tests/README.md) to run performance tests that characterize the runtime of CircInspect.

## How to Contribute to CircInspect
CircInsepct is available open source under the Apache 2.0 License. Contributions are welcome. Please follow the instructions in the following link to contribute: [How to contribute?](https://github.com/QSAR-UBC/CircInspect-dev/blob/main/.github/CONTRIBUTING.md)

## Reference
The primary developers of CircInspect are Mushahid Khan
([@mushahidkhan835](https://github.com/mushahidkhan835)) and Cihan Bosnali ([@CihanBosnali](https://github.com/CihanBosnali)).

The authors acknowledge funding from the NSERC CREATE in Quantum Computing
Program (grant number 543245), NSERC Alliance Quantum, UBC 4YF, and
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

