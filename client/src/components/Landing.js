// Copyright 2025 UBC Quantum Software and Algorithms Research Lab

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import React, { useEffect, useState } from "react";
        
import axios from "axios";
import { ModeOptions } from "../constants/ModeOptions";

import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import { defineTheme } from "../lib/defineTheme";
import OutputWindow from "./OutputWindow";

import ModeDropdown from "./ModeDropdown";
import ReportBugForm from "./ReportBugForm";
import TreeView from "./Tree";
import { ContinueIcon, ReverseContinueIcon, StepOverIcon, StepIntoIcon, StepOutIcon, RestartIcon, LoadingIcon } from "./Icons"

import Rodal from "rodal";
import 'rodal/lib/rodal.css';

import Qeditor from '../lib/Qeditor.jsx'

const javascriptDefault = ``;

/**
* Landing
*
* The main page where all the action happens.
*
* @param {string} authToken - authentication token for currently logged in user. "NOAUTH" if auth is disabled.
* @param {string} userEmail - email provided by user in login. "NOAUTH" if auth is disabled.

* @param {string} pennylaneVersion - pennylane version used by the backend. "0.41.0" is used as a placeholder if auth is disabled.
*/


const Landing = ({authToken, userEmail, pennylaneVersion}) => {

  // States for user code collection
  const [codeEditorData, setCodeEditorData] = useState('import pennylane as qml\ndev = qml.device("default.qubit", wires=2)\n@qml.qnode(dev)\ndef my_circuit():\n    qml.Hadamard(wires=0)\n    qml.CNOT(wires=[0, 1])\n    return qml.probs()\n\n# Execute a QNode to render a circuit in the righthand pane\nmy_circuit()')
  const [code, setCode] = useState(javascriptDefault);
  const [errorInCode, setErrorInCode] = useState([])

  // States for method tree
  const [showLoadingTree, setShowLoadingTree] = useState(false)
  const [showLoading, setShowLoading] = useState(false)
  const [expandedMethods, setExpandedMethods] = useState(new Set([0])) 
  const [onlyTransformsToLookAt, setOnlyTransformsToLookAt] = useState(false)
  const [currNode, setCurrNode] = useState(null);

  // States for debugger mode
  const [debugStart, setDebugStart] = useState(true)
  const [debuggerMainFcnInfo, setDebuggerMainFcnInfo] = useState([])
  const [readOnlyFlag, setReadOnlyFlag] = useState(false)
  const [debugLines, setDebugLines] = useState(new Set())
  const [line, setLine] = useState(-1)
  const [transformDetailsForDebugger, setTransformDetailsForDebugger] = useState([])
  const [transformIndexForDebugger, setTransformIndexForDebugger] = useState(0)
  const [transformIndiciesSeen, setTransformIndiciesSeen] = useState([])

  // States for circuit visualization
  const [imgsrc, setImgSrc] = useState("/defaultImage.png")
  const [currentFcnInImage, setCurrentFcnInImage] = useState(null)
  const [circuitDisplayed, setCircuitDisplayed] = useState(-1)

  // States for page theme
  const [theme, setTheme] = useState("cobalt");

  // States for mode and data initialization
  const [mode, setMode] = useState(ModeOptions[0]);
  const [initData, setInitData] = useState([])

	// States for breakpoints editor integration
	const [breaks, setBreaks] = useState([]);
 
	// States for API config
	const [deviceName, setDeviceName] = useState("");
	const [commands, setCommands] = useState("");
	const [debugIndex, setDebugIndex] = useState(-1);
	const [numWires, setNumWires] = useState(null);
	const [numShots, setNumShots] = useState(null);

	// States for data collection
	const [sessionID, setSessionID] = useState(null);

	// States for versions
	const [circInspectVersion, setCircInspectVersion] = useState("0.1.1")
	const [showLibraries, setShowLibraries] = useState(false)

  // States for data collection policy
  const [showPolicy, setShowPolicy] = useState(true)
  const [policyAccepted, setPolicyAccepted] = useState(false)

	const availableLibraries = [
		["Numpy", "1.26.2"],
		["Autograd", "1.6.2"],
		["Tensorflow", "unavailable"],
		["PyTorch", "unavailable"],
		["JAX", "unavailable"]
	]

  /**
  * A callback to trigger when user changes modes between real-time and debugger
  *
  * @param {object} mode -
  */
  const onSelectChange = (mode) => {
    setMode(mode);

		if(mode.value == "Debugger Mode"){
			axios.post('/dc/enterDebuggerMode', 
			{
				"token": authToken, 
				"session_id": sessionID,
        "policy_accepted": policyAccepted,
				"timestamp": new Date().getTime()
			}, {headers: {'Content-Type': 'application/json'}})

			setImgSrc("/defaultImage.png")
			setInitData([]) 
		} 
    
    else {
			axios.post('/dc/enterRealTimeMode', 
			{
				"token": authToken, 
				"session_id": sessionID,
        "policy_accepted": policyAccepted,
				"timestamp": new Date().getTime()
			}, {headers: {'Content-Type': 'application/json'}})

			setImgSrc("/defaultImage.png")
			setInitData([])  

			getDataFromBackEnd(codeEditorData)
			setLine(-1)
			setDebugLines(new Set())
			setReadOnlyFlag(false)
			setDebugStart(true)
			setShowLoading(false)

			setBreaks(b => [])
		}
  };
 
  /**
  * Set the id of which circuit visualization is currently being displayed.
  */
  const setCircuitDisplayedMethod = (id) => {
    setCircuitDisplayed(id)
  }

  /**
  * Methods to deal with the list of subcircuits / methods
  */
  const addMethodToExpandedMethods = (methodId) => {
    expandedMethods.add(methodId)
    setExpandedMethods(expandedMethods)
  }

  /**
  * Methods to deal with the list of subcircuits / methods
  */
  const removeMethodFromExpandedMethods = (methodId) => { 
    expandedMethods.delete(methodId)
    setExpandedMethods(expandedMethods)
  }

  /**
  * Methods to deal with the list of subcircuits / methods
  */
  const checkIfMethodInExpandedMethods = (methodId) => {
    return expandedMethods.has(methodId)
  }

  /**
  * The function to send main visualizeCircuit calls to the server
  * and process the returned JSON object.
  *
  * @param {string} data - user code to be sent to the server
  */
  const getDataFromBackEnd = (data) => {
    setErrorInCode([])
    setShowLoadingTree(true)

    // show default image if the entire user code is deleted
		if (data.length < 5) {setImgSrc("/defaultImage.png")}
    const headers = {
      'Content-Type': 'application/json'
    }
		axios.post('/visualizeCircuit', { 
			"token": authToken,
			"session_id": sessionID,
      "policy_accepted": policyAccepted,
			"timestamp": new Date().getTime(),
			"data": data,
			"mode": mode.value
		}, {headers: headers}
		)
		.then(res => { 
			if("error" in res["data"]){
				setErrorInCode(res["data"]["error"])
				setLine(parseInt(res["data"]["error"][1].split(" ")[2]))
			} else {
				setLine(-1)
			}
			setDeviceName(res["data"]["device_name"]);
			setDebugIndex(res["data"]["debug_index"]);
      setCommands(c => res["data"]["commands"]);
			setNumWires(res["data"]["num_wires"]);
			setNumShots(res["data"]["num_shots"]);

			if (res['data']['image'] !== null && res['data']['image'] !== undefined) {
				setImgSrc( "data:image/png;base64,".concat(res['data']["image"]))
			}
			setCircuitDisplayedMethod(res['data']['id'])
			var init_data = []
			for(let i = 0; i < res['data']['transform_details'].length; i++){
				
				init_data.push({
					"name":res['data']['transform_details'][i][2],
					"id": res['data']['transform_details'][i][3],
					"line_number": res['data']['transform_details'][i][4],
					"children": [],
					"img" : res['data']['transform_details'][i][0],
					"arguments":  [],
					"color_button" : false,
					"transform": true,
					"end_idx": -1,
					"more_information": {"Arguments": null, "Output": res['data']['transform_details'][i][1]}
				})
			}
			init_data.push({
				"name":res['data']['name'],
				"id": res['data']['id'],
				"line_number": res['data']['line_number'],
				"children": [],
				"img" :res['data']['image'],
				"arguments": res['data']['arguments'],
				"color_button" : true,
				"transform": false,
				"end_idx": "-1",
				"more_information":res['data']['more_information'],
				"has_children": res["data"]["has_children"]
			}
		)
			setInitData(init_data)
			setShowLoadingTree(false)
		})
		.catch(function (error) {      
			console.log(error);
			setShowLoadingTree(false)

		});
	}


  /**
  * When codeEditorData changes,
  * if it does not change again for 1 second after the first change,
  * send a request to the backend to process the current code.
  */
  useEffect(() => {
		const delaytime = setTimeout(() => {
    	if(mode.value == "Real-Time Development"){
      	getDataFromBackEnd(codeEditorData)
      	setInitData([])
      	setDebugStart(true)
    	}
		}, 1000)
		return () => clearTimeout(delaytime)
	}, [codeEditorData])

  /**
  * Set codeEditorData by preprocessing the code in the editor
  */
  const showCircuit = (action, data) => {
		// Do not change data if only a comment line is changed
		const newLines = data.split("\n")
		const oldLines = codeEditorData.split("\n")
		if (newLines.length !== oldLines.length) {
			setCodeEditorData(data)
			return
		}

		let changes = []
		for (let i=0; i<newLines.length; i++) {
			// Check that the line is changed
			if (newLines[i] !== oldLines[i]) {
				// If both old and new lines start with a "#", it is a single line comment change. Do not add to changes!
				// This covers the cases where the whole line is a comment.
				if (newLines[i].replace(/\s/g, "")[0] === "#" && oldLines[i].replace(/\s/g, "")[0] === "#") {
					continue
				}

				/* If the comment is at the end of the line, use the rules below:
							If new or old line does not include a # at all, it is not a comment change. Add to changes!
							If new or old line includes multiple # characters with other characters in between, it is a complicated line. Add to changes!
							If both new and old lines include a single #, check if the parts before the # are equal. If not, add to changes!	
							Check if the # character is in a string by counting " and ' characters before the # character. If yes, add to changes!
				*/
				let newLineArr = newLines[i].split("#").filter(e => e !== "") // The filter is used because some people start comments with multiple "#" on comments
				let oldLineArr = oldLines[i].split("#").filter(e => e !== "")

				if (newLineArr.length !== 2 || oldLineArr.length !== 2) {
					changes.push(newLines[i])
					continue
				}

				if (newLineArr[0] !== oldLineArr[0]) {
					changes.push(newLines[i])
					continue
				}

				// If odd number of " or ' before #, # must be in a string
				if ((newLineArr[0].split("\"") - 1) % 2 === 1 || (newLineArr[0].split("'") - 1) % 2 === 1) {
					changes.push(newLines[i])
				}

				// At this point we now that the changed line includes a single # that is not in a single line string.
				// We also know that the change in the line happened after the #, so it is a comment change.
				// Unless there is a multi-line string wrapping the whole line.
			}
		}

		if (changes.length > 0) {
    	setCodeEditorData(data)
		}
  };

  /**
  * Change the color of the button that is related to the circuit visualization currently rendereed on the page.
  */
  const updateCircuitShownButton = (curr_node, node) => {      
    curr_node.color_button = curr_node.id == node.id;
    for(let i = 0; i < curr_node.children.length; i ++) {
        updateCircuitShownButton(curr_node.children[i], node)
    }
  }
    
  /**
  * Change which circuit is being rendered on the visualization box.
  */
  const changeCircuit = (node) => {
    for(let i = 0; i < initData.length; i++){
      updateCircuitShownButton(initData[i], node)
    }
    setCurrentFcnInImage(node.id)
    setImgSrc("data:image/png;base64,".concat(node['img']))
    setCurrNode(node)
  }

  /**
  * Change which circuit is being rendered on the visualization box.
  */
  const showCircuitOfId = (d) => {
    for(let i = 0; i < d.length; i ++) {
      if(d[i]['id'] == currNode.id) {
        setImgSrc("data:image/png;base64,".concat(d[i]['img']))
        return
      }
    }
  }
  
  /**
  * Runs when the user enters the landing page after auth and / or when
  * user accepts or rejects the data collection policy. Sets session id
  * and color theme. If policy is accepted, starts data collection by
  * sending a sessionEnter with the new session id.
  */
  useEffect(() => {
		if (authToken == null) {return () => {}}

		const session = (new Date().getTime().toString(16) + "_" + Math.floor(Math.random() * Number.MAX_SAFE_INTEGER).toString(16)).toUpperCase()
		setSessionID(session)

    defineTheme("tomorrow-night").then((_) =>
      setTheme({ value: "tomorrow-night", label: "tomorrow-night" })
    );

		axios.post('/dc/sessionEnter',
			{
				"token": authToken,
				"session_id": session,
        "policy_accepted": policyAccepted,
				"timestamp": new Date().getTime()
			},
			{headers: {'Content-Type': 'application/json'}}
		)

		const handleBeforeUnload = (event) => {
      // Perform actions before the component unloads
      event.preventDefault();
      event.returnValue = '';
			axios.post('/dc/sessionExit',
				{
					"token": authToken,
					"session_id": session,
          "policy_accepted": policyAccepted,
					"timestamp": new Date().getTime()
				},
				{headers: {'Content-Type': 'application/json'}}
			)
    };

		window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
			window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [authToken, policyAccepted]);


  /**
  * Runs when a debugger button is pressed, sends information about
  * the current debugger run to the server, requesting the desired
  * action to be processed
  *
  * @param {string} action - Debugger action. E.g. step into, next breakpoint
  */
  const debugNext = (action) => {
    const headers = {
      'Content-Type': 'application/json'
    }
    axios.post('/debugNext',
			{
				"token": authToken,
				"session_id": sessionID,
        "policy_accepted": policyAccepted,
				"timestamp": new Date().getTime(),
				"data": debugLines,
				"device_name": deviceName,
				"commands": commands,
				"debug_index": debugIndex,
				"num_wires": numWires,
				"num_shots": numShots,
				"debug_action": action
			},{headers: headers})
      .then(res => {

          setDebugIndex(res["data"]["debug_index"]);

          var data = []
          setInitData([])
          // expandedMethods.add(res['data']['id'])
          // setExpandedMethods(expandedMethods)
          if(circuitDisplayed == -1) {
          setCircuitDisplayedMethod(res['data']['id'])
        }
          data.push({
            "name":res['data']['name'],
            "id": res['data']['id'],
            "line_number": res['data']['line_number'],
            "children": [],
						"has_children": res['data']['has_children'],
            "img" :res['data']['image'],
            "arguments": res['data']['arguments'],
            "color_button" : false,
            "transform": false,
            "more_information": {"Output": res['data']['circuit_output'], "Arguments": debuggerMainFcnInfo["Arguments"]},
            "end_idx": res['data']['end_idx']
          })
          if(currNode == null) {
            data[data.length - 1]['color_button'] = true
          }
          setLine(res['data']['line_number_to_highlight'])

          if(res['data']['line_number_to_highlight'] == -1) {
            data[0]["more_information"] = debuggerMainFcnInfo
            setOnlyTransformsToLookAt(true)
          }
          if(onlyTransformsToLookAt || res['data']['line_number_to_highlight'] == -1){
            if(transformDetailsForDebugger.length > 0) {
              var debugLinesSet = new Set()
              if(debugLines.length > 0){
                  debugLinesSet = new Set(debugLines.split(" "))
              }
              var i = transformIndexForDebugger
              while(i >= 0){
                if(!debugLinesSet.has(String(transformDetailsForDebugger[i][4])) ||
                transformIndiciesSeen.includes(String(transformDetailsForDebugger[i][4]))
                ){
                  data.unshift({
                    "name":transformDetailsForDebugger[i][2],
                    "id": transformDetailsForDebugger[i][3],
                    "line_number": transformDetailsForDebugger[i][4],
                    "children": [],
                    "img" : transformDetailsForDebugger[i][0],
                    "arguments":  [],
                    "color_button" : false,
                    "transform": true,
                    "end_idx": -1,
                    "more_information": {"Arguments": null, "Output": transformDetailsForDebugger[i][1]}
                  })
                  i -= 1
              }

                else {
                  debugLinesSet.delete(String(transformDetailsForDebugger[i][4]))
                  transformIndiciesSeen.push((String(transformDetailsForDebugger[i][4])))
                  setLine(transformDetailsForDebugger[i][4])
                  // setTransformIndexForDebugger(i)
                  break
                  
                }
                if(i == -1) {
                  setReadOnlyFlag(false)
                  setDebugStart(true)                }
              }
            }
          
            else {
            setReadOnlyFlag(false)
            setDebugStart(true)
            }
          }
          setInitData(data)

          if(currNode == null){
            setImgSrc( "data:image/png;base64,".concat(res['data']["image"]))
            }
            else {
              showCircuitOfId(data)
            }
          setShowLoadingTree(false)

      })
      .catch(function (error) {      
        console.log(error)

      });
  }

  const getDebugLineNumbers = (lines) => {
    setDebugLines(lines)
  }

  /**
  * Clear states to be ready for a new debugger session.
  * Then, send a visualizeCircuit call to process the
  * code and get the trace / objects needed for debugging.
  */
  const startDebugger = () => {
    setImgSrc("/defaultImage.png")
    setCurrNode(null)
    setInitData([])
    setShowLoading(true)
    setLine(-1)
    setExpandedMethods(new Set())

    if(debugStart == false) {
      // call service to reset all global variables and remove red color
      setLine(-1)
      setReadOnlyFlag(false)
      setDebugStart(true)
      setShowLoading(false)

    }
  
    else {
      setCircuitDisplayed(-1)

    const headers = {
      'Content-Type': 'application/json'
    }
    axios.post('/visualizeCircuit', {
			"token": authToken,
			"session_id": sessionID,
			"timestamp": new Date().getTime(),
      "policy_accepted": policyAccepted,
			"data": codeEditorData,
			"mode": mode.value
		}, {headers: headers}
    )
      .then(res => {
        setErrorInCode([])
        if("error" in res["data"]){
          setErrorInCode(res["data"]["error"])
					setLine(parseInt(res["data"]["error"][1].split(" ")[2]))
        } else {
					setLine(-1)
				}

				setDeviceName(res["data"]["device_name"]);
				setDebugIndex(res["data"]["debug_index"]);
				setCommands(c => res["data"]["commands"]);
				setNumWires(res["data"]["num_wires"]);
				setNumShots(res["data"]["num_shots"]);

        setOnlyTransformsToLookAt(false)
        setTransformIndiciesSeen([])
        setTransformDetailsForDebugger([])
        setDebuggerMainFcnInfo(res['data']['more_information'])


        if(res['data']['transform_details'].length > 0){
          setTransformDetailsForDebugger(res['data']['transform_details'])
          setTransformIndexForDebugger(res['data']['transform_details'].length - 1)
        }
        setReadOnlyFlag(true)
        setDebugStart(false)

          setShowLoading(false)

      })
      .catch(function (error) {      

        console.log(error);
        setShowLoading(false)

      });
  }

}

  /**
  * Runs when user sets a new breakpoint on the editor. Sets the state that
  * represents all currently set breakpoints.
  */
	useEffect(() => {
		if (mode.value == "Real-Time Development" && (breaks.length !== 0)) {
			setBreaks(b => []);
		}
		let breaksStr = "";
		breaks.forEach((b) => breaksStr += (b + " "));
		getDebugLineNumbers(breaksStr);
	},[breaks])


  return (
    <>
      <ToastContainer
        position="top-right"
        autoClose={2000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />
      <div className="h-4 w-full bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500"></div>
			
      <div className="flex flex-row">
        <div className="px-4 py-2 basis-1/2 flex flex-row">
          <div className="flex flex-row space-x-8 items-start w-ful">
          <ModeDropdown onSelectChange={onSelectChange} />
          {mode.value == "Debugger Mode" && <button onClick={startDebugger} className="rounded bg-white hover:bg-gray-300 py-2.5 px-8 text-xs transition-colors duration-150 border focus:shadow-outline">
            {debugStart ? "Start Debugger" : "Stop Debugger"}</button> 
          }
          {showLoading ? <div role="status" className="py-1"><LoadingIcon/></div> : <div></div>}
					


    {/* Debugger button function calls */}
		{(mode.value == "Debugger Mode" && !debugStart) ? <div> 
        <button  
          onClick={() => {debugNext("next_breakpoint")}}
          className="group rounded bg-white hover:bg-gray-300 p-2.5 my-0 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<ContinueIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">Next Breakpoint</span>
				</button>
        <button  
          onClick={() => {debugNext("prev_breakpoint")}}
          className="group rounded bg-white hover:bg-gray-300 p-2.5 my-0 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<ReverseContinueIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">Previous Breakpoint</span>
				</button>
				<button
          onClick={() => {debugNext("step_over")}}
					className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<StepOverIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">Step Over</span>
				</button>
				<button
          onClick={() => {debugNext("step_into")}}
					className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<StepIntoIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">Step Into</span>
				</button>
				<button
          onClick={() => {debugNext("step_out")}}
					className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<StepOutIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">Step Out</span>
				</button>
				<button
          onClick={() => {debugNext("restart")}}
					className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline">
				<RestartIcon/>
				<span className="absolute top-2 scale-0 rounded bg-gray-200 border border-gray-400 p-1 text-xs text-black group-hover:scale-100 transition-all">Restart</span>
				</button>
			</div>:<></>}
              </div>
        </div>

			<div className="w-full px-4 py-2 basis-1/2 flex flex-row-reverse">
		  <a href="https://ubc.ca1.qualtrics.com/jfe/form/SV_3aAEHg7YUmCJ0WO" target="_blank"><button className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-8 rounded ml-4">Give Feedback</button></a>
				<p className="mx-8">You are currently using CircInspect {circInspectVersion} with Pennylane <a className="text-pink-600" href={"https://github.com/PennyLaneAI/pennylane/releases/tag/v"+pennylaneVersion} target="_blank" rel="noreferrer" >{pennylaneVersion}</a>
				<br/>
				See a list of <button className="text-pink-600" onClick={() => setShowLibraries(true)}>available libraries</button>.</p>
       
      </div> 
      </div>

      <div className="flex flex-row space-x-4 items-start px-4 py-1">
        <div className="flex flex-col w-1/2 h-full justify-start items-end">
				<Qeditor
					className="CodeEditorWindow"
					breaks={breaks}
					setbreaks={setBreaks}
					highlightline={line}
					focuson={true}
					value={code}
					setvalue={setCode}
					theme={theme.value}
					readOnly={readOnlyFlag}
					onChange={showCircuit}
					defaultValue={'import pennylane as qml\ndev = qml.device("default.qubit", wires=2)\n@qml.qnode(dev)\ndef my_circuit():\n    qml.Hadamard(wires=0)\n    qml.CNOT(wires=[0, 1])\n    return qml.probs()\n\n# Execute a QNode to render a circuit in the righthand pane\nmy_circuit()'}
				/>

        </div>

        <div className="right-container flex flex-shrink-0 w-[49%] flex-col space-y-3 ">
          <OutputWindow imgsrc={imgsrc} isError={errorInCode.length != 0}/>
          <div className="flex flex-col ">

          
      <div className="flex space-x-1 function-areas " style={{overflowY:"auto"}}>

      {(errorInCode.length != 0) ? <p className="border-red-400 text-red-700">{errorInCode[0]} - {errorInCode[1]} <br/> Cannot render a new visualization due to error</p> : 
      ( showLoadingTree? <div role="status" className="py-1">
   <LoadingIcon/> 
</div>:
            <div className="grid gap-1  w-full ">
              <TreeView circuitDisplayed={circuitDisplayed} setCircuitDisplayedMethod={setCircuitDisplayedMethod} removeMethodFromExpandedMethods={removeMethodFromExpandedMethods} checkIfMethodInExpandedMethods={checkIfMethodInExpandedMethods} addMethodToExpandedMethods={addMethodToExpandedMethods} modeValue ={mode.value} currNode = {currNode} currentFcnInImage = {currentFcnInImage} changeCircuitTree= {changeCircuit} data={initData} handleCallback={changeCircuit} deviceName={deviceName} commands={commands} numWires={numWires} numShots={numShots} sessionID={sessionID} authToken={authToken} policyAccepted={policyAccepted}/>
            </div>
    )}
      </div>
          </div>
        </div>
      </div>

			<Rodal customStyles={{overflow:"auto", padding:"10px", cursor:"default"}}
					 visible={showLibraries}
					 onClose={() => setShowLibraries(false)}
					 height={480}
					 width={400}>
							<h1 className="font-bold text-xl mx-4 mt-2">Available Libraries</h1>
							<div className="h-4"></div>
							<table className="w-5/6 m-auto border border-gray-700"><tbody>
								{availableLibraries.map((a) => <tr className="even:bg-gray-300" key={a[0]}><td className="p-1">{a[0]}</td><td className={a[1] === "unavailable" ? "text-red-600" : ""}>{a[1]}</td></tr>)}	
							</tbody></table>
							<div className="h-4"></div>
							<p className="mx-4">Please let us know at <b className="font-bold">qsar@ece.ubc.ca</b> if you need another library to work with CircInspect!</p>
			</Rodal>

			<Rodal customStyles={{overflow:"auto", padding:"10px", cursor:"default"}}
					 visible={showPolicy}
           showCloseButton={false}
					 height={550}
					 width={800}>
							<h1 className="font-bold text-xl mx-4 mt-2">CircInspect: Integrating Visual Circuit Analysis, Abstraction, and Real-Time Development in Quantum Debugging</h1>
<div className="m-4">
							<p className="mb-2 text-justify">Thank you for using CircInspect, our quantum debugging tool. To improve CircInspect and advance research in quantum debugging, we collect anonymous usage data. This includes:</p>
<ul className="mb-2">
<li>The debugging features and buttons you interact with</li>
<li>How you navigate and use CircInspect</li>
<li>Any errors or unexpected behaviors you encounter</li>
<li>Code snippets processed through the debugger</li>
</ul>
<p className="mb-2 text-justify">This data helps us understand how users engage with the debugger, what they consider to be bugs, and how they approach the debugging process. The collected information is used for both tool improvement and research on quantum debugging methodologies. This is part of a University of British Columbia study. The primary investigator for this project is Professor Olivia Di Matteo from the Department of Electrical and Computer Engineering. The email address of Olivia is olivia@ece.ubc.ca. The email address of the co-investigator, Mushahid Khan, is mkhan103@student.ubc.ca. If you have any concerns or complaints about your rights as a research participant and/or your experiences while participating in this study, contact the Research Participant Complaint Line in the UBC Office of Research Ethics at 604-822-8598 or if long distance e-mail RSIL@ors.ubc.ca or call toll free 1-877-822-8598.</p>
<p className="mb-2 text-justify">By clicking on “I accept”, you acknowledge and agree to this data collection. We do not collect any personally identifiable information, and all data is used solely for research and development purposes. If you click on “I reject”, then we will not be collecting any data.
</p> 
</div>
		<div className="mt-4">
		<button className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={()=>{setPolicyAccepted(true); setShowPolicy(false)}}>I accept</button>
		<button className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={()=>{setPolicyAccepted(false); setShowPolicy(false)}}>I reject</button>
		</div>
			</Rodal>
		</>
  );
};
export default Landing;
