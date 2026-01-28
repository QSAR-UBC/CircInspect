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

import axios from "axios";
import './styles.css'
import 'reactjs-popup/dist/index.css';
import React, { useState,useEffect } from "react";
import Rodal from 'rodal';
import { LoadingIcon, PlusIcon, MinusIcon } from "./Icons"

// include styles
import 'rodal/lib/rodal.css';

/**
* TreeNode
*
* Renders a single node of the method expansion tree.
*/
const TreeNode = ({
	node,
	changeCircuitTree,
	currNode,
	modeValue,
	addMethodToExpandedMethods,
	checkIfMethodInExpandedMethods,
	removeMethodFromExpandedMethods,
	setCircuitDisplayedMethod,
	circuitDisplayed,
	deviceName,
	commands,
	numWires,
	numShots,
	sessionID,
	authToken,
  policyAccepted
}) => {
  
  const [nodeChildren, setNodeChildren] = useState([])
  const [isVisible, setIsVisible] = useState(false)
  const [showLoading, setShowLoading] = useState(false)

  const [methodExpanded, setMethodExpanded] = useState(false)

  /**
  * Runs when user presses the button to display circuit.
  * Calls updateCircuit to let other components know which
  * node to change to. Also, sends a data collection request.
  */
	const handleDisplayOnClick = () => {
		updateCircuit()
		axios.post('/dc/displayCircuit',
		{
			"token": authToken,
			"session_id": sessionID,
      "policy_accepted": policyAccepted,
			"timestamp": new Date().getTime(),
			"function": node
		}, {headers: {'Content-Type': 'application/json'}})
	}

  /**
  * Update information on other components about which node is currently being rendered.
  */
  const updateCircuit = () => {
    changeCircuitTree(node)
    setCircuitDisplayedMethod(node.id)
  }

  /**
  * Runs when the user presses the +/- button on the node to see the expansion 
  * of its submethods or to close the expansion.
  */
	useEffect(() => {
    if(circuitDisplayed == node.id){
      updateCircuit()
    }

    if(checkIfMethodInExpandedMethods(node.id)) {
      setMethodExpanded(true)
    }
    else {
      setMethodExpanded(false)
    }
    if(methodExpanded == true)
    {
      setShowLoading(true)
      axios.post('/expandMethod', 
				{
					"token": authToken,
					"session_id": sessionID,
          "policy_accepted": policyAccepted,
					"timestamp": new Date().getTime(),
					"name": node.name,
					"id": node.id,
					"end_idx" : node.end_idx,
					"real_time": false,
					"device_name": deviceName,
					"commands": commands,
					"num_wires": numWires,
					"num_shots": numShots
				}, 
          )
          .then(res => {
            node.children = []
            var res_data_children = res['data']['children']
            if(node.children.length == 0 && node.transform == false) {
            for(let i = 0; i < res_data_children.length; i++) {
              node.children.push({
                "name": res_data_children[i]["name"],
                "id": res_data_children[i]["id"],
                "line_number": res_data_children[i]["line_number"],
                "img": res_data_children[i]["image"],
                "children": [],
                "color_button" : false,
                "end_idx" : node.end_idx,
                "transform": false,
                "more_information": res_data_children[i]['more_information'],
								"has_children": res_data_children[i]["has_children"]
              })
            }}

            setNodeChildren(node.children)
            setShowLoading(false)
            if(modeValue == "Debugger Mode" && currNode != null && node['id'] == currNode['id']){
              updateCircuit()
            }
          })
          .catch(function (error) {      
            console.log(error);
          });   
        }  
        else {
          setNodeChildren([])
        }
      
      
      
      }, [methodExpanded]);

  /**
  * Use methods to deal with the expanded method list to set it according to user action.
  */
  	const updateExpandedMethods = () => {
		if(methodExpanded) {
			removeMethodFromExpandedMethods(node.id)
			setMethodExpanded(false)
		} else{
			addMethodToExpandedMethods(node.id)
			setMethodExpanded(true)
		}
	}

  /**
  * Show the card with function info related to this node.
  */
	const showFunctionInfo = () => {
		setIsVisible(true)
		axios.post('/dc/displayFuncInfo',
		{
			"token": authToken,
			"session_id": sessionID,
      "policy_accepted": policyAccepted,
			"timestamp": new Date().getTime(),
			"function": node
		}, {headers: {'Content-Type': 'application/json'}})
	}

  return (
    <div className="tree-node grid gap-1">

      <div className="toggle-icon">
      	<div>
        	<p 
        	className="hover:font-medium text-xs	functionName"
        	onClick = {showFunctionInfo}
					style={{marginRight:"0px", display:"inline"}}
					>
            line {node.line_number} - {node.name}:
          </p>   
            
             <button  
             style={{color: circuitDisplayed == node.id? "white": "", backgroundColor:circuitDisplayed == node.id? " rgb(34 197 94)": ""}} onClick={handleDisplayOnClick} className="py-1 rounded bg-white hover:bg-gray-100 text-gray-800s px-4 m-2 text-xs transition-colors duration-150 border shadow focus:shadow-outline ">Display Circuit</button>
						{node.has_children ? 
            	(!methodExpanded? 
            	<button onClick={updateExpandedMethods} className="text-xs"><PlusIcon/></button>:
							<button onClick={updateExpandedMethods} className="text-xs"><MinusIcon/></button>)
						:
						<></>}
              
          <Rodal 
          customStyles={{overflow:"auto", padding:"10px", cursor:"default"}}
          visible={isVisible}
					onClose={()=>{setIsVisible(false)}}
					>
          	<h5 className=" text-base font-bold">
              line {node.line_number} - <span className="font-mono">{node.name}</span>
            </h5>

            <div style={{ overflow:"auto", height:"fit-content"}}><pre >
              {node.more_information['Output'] &&
							<div>Output:
              	<ul>
                	<li>{node.more_information['Output']}</li>
                </ul>
							  <br/>
              </div>}
              {node.more_information['Arguments'] != null && node.more_information['Arguments'].length > 0 && 
              <div>
                 <p>Arguments:</p>
              {node.more_information['Arguments'].map((arg) => (
                <ul>
                  <li>{arg[0]}: {JSON.stringify(arg[1])}</li>
                </ul>
              ))}
              </div>
              }

              </pre></div>

          </Rodal>
      </div>

          
        </div>
        {methodExpanded && 
        <ul className="child">
        {showLoading ? <div role="status" className="py-1"><LoadingIcon/></div>
          : 
      <TreeView  setCircuitDisplayedMethod={setCircuitDisplayedMethod} removeMethodFromExpandedMethods={removeMethodFromExpandedMethods} checkIfMethodInExpandedMethods={checkIfMethodInExpandedMethods} addMethodToExpandedMethods={addMethodToExpandedMethods} data={nodeChildren} changeCircuitTree={changeCircuitTree} currNode={currNode} modeValue={modeValue} circuitDisplayed={circuitDisplayed} deviceName={deviceName} commands={commands} numWires={numWires} numShots={numShots} sessionID={sessionID} authToken={authToken} policyAccepted={policyAccepted}/>}
</ul>}
    </div>
  );
};

/**
* TreeView
*
* Renders a list of TreeNode objects
*/
const TreeView = ({
	data,
	changeCircuitTree,
	currentFcnInImage,
	currNode,
	modeValue,
	addMethodToExpandedMethods,
	checkIfMethodInExpandedMethods,
	removeMethodFromExpandedMethods,
	setCircuitDisplayedMethod,
	circuitDisplayed,
	deviceName,
	commands,
	numWires,
	numShots,
	sessionID,
	authToken,
  policyAccepted
}) => {
  return (

    <div className="tree-view grid gap-4">
<ul>
      {data.map((node) => (
        <TreeNode circuitDisplayed={circuitDisplayed} setCircuitDisplayedMethod={setCircuitDisplayedMethod} removeMethodFromExpandedMethods={removeMethodFromExpandedMethods} checkIfMethodInExpandedMethods={checkIfMethodInExpandedMethods} addMethodToExpandedMethods={addMethodToExpandedMethods} modeValue= {modeValue} currNode = {currNode} key={node.id} node={node} changeCircuitTree={changeCircuitTree} deviceName={deviceName} commands={commands} numWires={numWires} numShots={numShots} sessionID={sessionID} authToken={authToken} policyAccepted={policyAccepted}/>
       
      ))}

</ul>
    </div>

  );
};

export default TreeView;
