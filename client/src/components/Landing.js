// Copyright 2026 UBC Quantum Software and Algorithms Research Lab

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// External Libraries
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ToastContainer } from "react-toastify";
import Rodal from "rodal";
import "react-toastify/dist/ReactToastify.css";
import "rodal/lib/rodal.css";

// Internal Utilities
import { defineTheme } from "../lib/defineTheme";

// Helpers
import { getSubtreeForLevel } from "../helpers/graphHelpers";

// Components
import OutputWindow from "./OutputWindow";
import Header from "./Header";
import {
  getNextBreakpointState,
  getPrevBreakpointState,
  getStepOverState,
  getStepIntoState,
  getStepOutState,
  getRestartState,
  getCircuitOutputandImg
} from "../hooks/DebuggerControls";
import { flattenGraphNodes } from "../hooks/DebuggerUtils";
import CommandTreeGraph from "./CommandTree.js";
import TransformTimeline from "./TransformTimeline.js";
import InfoPopup from "./InfoPopup.js";
import Qeditor from "../lib/Qeditor.jsx";
import {
  ContinueIcon,
  ReverseContinueIcon,
  StepOverIcon,
  StepIntoIcon,
  StepOutIcon,
  StepIntoIconDisabled,
  StepOutIconDisabled,
  RestartIcon,
  LoadingIcon,
  ClearBreakpointsIcon,
} from "./Icons";
import { MarkGithubIcon } from '@primer/octicons-react'

/**
 * Landing
 *
 * The main page where all the action happens.
 *
 * @param {string} pennylaneVersion - pennylane version used by the backend.
 */

const DEFAULT_CODE = `import pennylane as qp

dev = qp.device("default.qubit")

@qp.qnode(dev)
def my_circuit():
    qp.Hadamard(wires=0)
    qp.CNOT(wires=[0, 1])
    return qp.probs()

# Execute a QNode to render a circuit in the righthand pane
my_circuit()`;

const POST_SELECT_ERROR_MSG = "Invalid state: Post-selected measurement probability is 0";

const Landing = ({ pennylaneVersion }) => {
  // Identifies this tab to the backend so its debug state doesn't collide with other open tabs
  const [sessionId] = useState(() => crypto.randomUUID());

  // Code editor state
  const [codeEditorData, setCodeEditorData] = useState(DEFAULT_CODE);
  const [code, setCode] = useState("");
  const [errorInCode, setErrorInCode] = useState([]);

  // Debugger state
  const [debuggerActive, setDebuggerActive] = useState(false);
  const [readOnlyFlag, setReadOnlyFlag] = useState(false);
  const [breakpointLines, setBreakpointLines] = useState(new Set());
  const [line, setLine] = useState(-1);
  const [showLoading, setShowLoading] = useState(false);

  // Circuit visualization state
  const [imgsrc, setImgSrc] = useState("/defaultImage.png");

  // Theme state
  const [theme, setTheme] = useState("cobalt");

  // Breakpoints state
  const [breaks, setBreaks] = useState([]);

  // API / backend config state
  const [deviceName, setDeviceName] = useState("");
  const [commands, setCommands] = useState("");
  const [debugIndex, setDebugIndex] = useState(-1);
  const [transformStack, setTransformStack] = useState([]);
  const [currentTransform, setCurrentTransform] = useState(-1);
  const [currentTransformIdx, setCurrentTransformIdx] = useState(1);
  const [numWires, setNumWires] = useState(null);
  const [numShots, setNumShots] = useState(null);

  // Version / library state
  const [circInspectVersion] = useState("0.2.0");
  const [showLibraries, setShowLibraries] = useState(false);
  const [availableLibraries, setAvailableLibraries] = useState([]);

  // Graph / transform state
  const [graphData, setGraphData] = useState(null);
  const [fullGraphData, setFullGraphData] = useState(null);
  const [displayTransformLevel, setDisplayTransformLevel] = useState(0);
  const displayTransformLevelRef = React.useRef(0);
  const [showLoadingTree, setShowLoadingTree] = useState(false);
  const [presentTransforms, setPresentTransforms] = useState([]);
  const [activeTransforms, setActiveTransforms] = useState(null);
  const activeTransformsRef = React.useRef(null);
  const prevPresentTransformsRef = React.useRef([]);

  // Mid-circuit measurement postselect state
  const [postSelectOverrides, setPostSelectOverrides] = useState({});
  const postSelectOverridesRef = React.useRef({});
  const prevPostSelectOverridesRef = React.useRef({});

  // Effects

  /** Fetch available library versions and set the theme on mount, then run
   * the default circuit once. */
  useEffect(() => {
    axios
      .get("/library_version")
      .then((res) => {
        setAvailableLibraries([
          ["Numpy", res.data.numpy],
          ["Autograd", res.data.autograd],
          ["Tensorflow", "unavailable"],
          ["PyTorch", "unavailable"],
          ["JAX", res.data.jax],
        ]);
      })
      .catch((err) => console.error("Library version fetch failed:", err));

    defineTheme("tomorrow-night").then((_) =>
      setTheme({ value: "tomorrow-night", label: "tomorrow-night" })
    );

    getDataFromBackEnd(codeEditorData);
  }, []);

  /** Keep activeTransformsRef in sync with activeTransforms state. */
  useEffect(() => {
    activeTransformsRef.current = activeTransforms;
  }, [activeTransforms]);

  /** Keep displayTransformLevelRef in sync with displayTransformLevel state. */
  useEffect(() => {
    displayTransformLevelRef.current = displayTransformLevel;
  }, [displayTransformLevel]);

  /** Keep postSelectOverridesRef in sync with postSelectOverrides state. */
  useEffect(() => {
    postSelectOverridesRef.current = postSelectOverrides;
  }, [postSelectOverrides]);

  /** 
   * Synchronize activeTransforms with presentTransforms.
   * Ensures that newly added transforms are active (checked) by default,
   * while deleted transforms are removed and manually unchecked ones stay unchecked.
   */
  useEffect(() => {
    // If no transforms in code, clear active list
    if (presentTransforms.length === 0) {
      if (activeTransforms !== null && activeTransforms?.length !== 0) {
        setActiveTransforms([]);
        setDisplayTransformLevel(0);
        displayTransformLevelRef.current = 0;
      }
      prevPresentTransformsRef.current = [];
      return;
    }

    // Default to all active on first detection (when state is still null)
    if (activeTransforms === null) {
      setActiveTransforms(presentTransforms);
      prevPresentTransformsRef.current = presentTransforms;
      return;
    }

    const prevPresentTransformsSet = new Set(prevPresentTransformsRef.current.map(t => JSON.stringify(t)));
    const presentTransformsSet = new Set(presentTransforms.map(t => JSON.stringify(t)));

    const prunedActiveTransforms = activeTransforms.filter(t => presentTransformsSet.has(JSON.stringify(t)));
    const brandNewTransforms = presentTransforms.filter(t => !prevPresentTransformsSet.has(JSON.stringify(t)));
    const nextActiveTransforms = [...prunedActiveTransforms, ...brandNewTransforms];

    const hasChanged = nextActiveTransforms.length !== activeTransforms.length ||
      !nextActiveTransforms.every((t, i) => JSON.stringify(t) === JSON.stringify(activeTransforms[i]));

    if (hasChanged) {
      setActiveTransforms(nextActiveTransforms);
    }

    prevPresentTransformsRef.current = presentTransforms;
  }, [presentTransforms]);

  /**
   * When codeEditorData changes,
   * if it does not change again for 1 second after the first change,
   * send a request to the backend to process the current code.
   */
  useEffect(() => {
    const delaytime = setTimeout(() => {
      getDataFromBackEnd(codeEditorData, activeTransformsRef.current);
      setDebuggerActive(false);
    }, 1000);
    return () => clearTimeout(delaytime);
  }, [codeEditorData]);


  /**
   * Runs when user sets a new breakpoint on the editor. Sets the state that
   * represents all currently set breakpoints.
   */
  useEffect(() => {
    setBreakpointLines(breaks);
  }, [breaks]);

  /** Applies a subtree for a given level, updating graph data and circuit image. */
  const visualizeSubtreeForLevel = (graphData, level) => {
    const subtree = getSubtreeForLevel(graphData, level);
    setGraphData(subtree);

    if (subtree?.nodes?.length) {
      const subtreeTargetIds = new Set(subtree.edges.map(e => String(e.target)));
      const subtreeRoot = subtree.nodes.find(n => !subtreeTargetIds.has(String(n.id)));
      if (subtreeRoot?.subtree_circuit_img) {
        setImgSrc("data:image/png;base64,".concat(subtreeRoot.subtree_circuit_img));
        return;
      }
    }
    setImgSrc("/defaultImage.png");
  };

  // Handlers
  /** Updates the circuit image when a node is selected in the command tree. */
  const handleNodeSelect = (imageBase64) => {
    setImgSrc("data:image/png;base64,".concat(imageBase64));
  };

  /** Detects the transform level of a subtree by walking up its nodes in the full unified graph. */
  const detectLevelFromSubtree = (fullGraph, subtree) => {
    if (!fullGraph || !subtree || !subtree.nodes || subtree.nodes.length === 0) return -1;

    const subtreeNode = subtree.nodes[0];
    const targetNodeId = String(subtreeNode.id);

    const parentMap = {};
    fullGraph.edges.forEach(e => {
      parentMap[String(e.target)] = String(e.source);
    });

    const targetIds = new Set(fullGraph.edges.map(e => String(e.target)));
    const rootSearch = fullGraph.nodes.find(n => !targetIds.has(String(n.id)));
    if (!rootSearch) return -1;
    const rootId = String(rootSearch.id);

    const childrenOfRoot = fullGraph.edges
      .filter(e => String(e.source) === rootId)
      .map(e => String(e.target))
      .sort((a, b) => Number(a) - Number(b));

    const levelRoots = new Set(childrenOfRoot);

    let curr = targetNodeId;
    while (curr && !levelRoots.has(curr) && curr !== rootId) {
      curr = parentMap[curr];
    }

    if (levelRoots.has(curr)) {
      return childrenOfRoot.indexOf(curr);
    }

    return -1;
  };

  /**
   * Handles transform level changes purely on the frontend.
   * Filters the full unified graph data to the correct subtree branch and
   * updates the circuit image from that branch's root node.
   */
  const handleTransformSelect = (newActiveTransforms) => {
    setActiveTransforms(newActiveTransforms);
    activeTransformsRef.current = newActiveTransforms;

    if (!fullGraphData) return;

    const level = newActiveTransforms.length;
    setDisplayTransformLevel(level);
    displayTransformLevelRef.current = level;

    const subtree = getSubtreeForLevel(fullGraphData, level);

    if (subtree && subtree.nodes && subtree.nodes.length > 0) {
      setGraphData(subtree);
      const subtreeTargetIds = new Set(subtree.edges.map(e => String(e.target)));
      const subtreeRoot = subtree.nodes.find(n => !subtreeTargetIds.has(String(n.id)));
      if (subtreeRoot?.subtree_circuit_img) {
        setImgSrc("data:image/png;base64,".concat(subtreeRoot.subtree_circuit_img));
      }
    }
  };

  /** Re-runs visualization and updates the postselect overrides when user changes postselect overrides. */
  const handlePostSelectApply = (nodeId, value) => {
    setPostSelectOverrides(prev => {
      const next = { ...prev };
      if (value === null) {
        delete next[String(nodeId)];
      } else {
        next[String(nodeId)] = value;
      }
      prevPostSelectOverridesRef.current = { ...postSelectOverridesRef.current };
      postSelectOverridesRef.current = next;
      // Refresh the visualization data with the new overrides.
      setTimeout(() => getDataFromBackEnd(codeEditorData), 0);

      return next;
    });
  };


  // API Calls
  /**
   * The function to send main visualizeCircuit calls to the server
   * and process the returned JSON object.
   *
   * @param {string} data - user code to be sent to the server
   */
  const getDataFromBackEnd = (data) => {
    setErrorInCode([]);
    setShowLoadingTree(true);

    // show default image if the entire user code is deleted
    if (data.length < 5) {
      setImgSrc("/defaultImage.png");
    }
    const headers = {
      "Content-Type": "application/json",
    };
    axios
      .post(
        "/visualizeCircuit",
        {
          timestamp: new Date().getTime(),
          data: data,
          postselect_overrides: postSelectOverridesRef.current,
          session_id: sessionId,
        },
        { headers: headers }
      )
      .then((res) => {
        if ("error" in res["data"]) {
          setErrorInCode(res["data"]["error"]);
          setLine(parseInt(res["data"]["error"][1].split(" ")[2]));
          // On error, we keep the old graphData and presentTransforms to maintain the tree
          if (res["data"]["error"][0] === "Invalid state: Post-selected measurement probability is 0") {
            setPostSelectOverrides(prevPostSelectOverridesRef.current);
            postSelectOverridesRef.current = prevPostSelectOverridesRef.current;
          }
        } else {
          setLine(-1);
          setDeviceName(res["data"]["device_name"]);
          setDebugIndex(res["data"]["debug_index"]);
          setCommands((c) => res["data"]["commands"]);
          setNumWires(res["data"]["num_wires"]);
          setNumShots(res["data"]["num_shots"]);
          const newTransformDetails = res["data"]["transform_details"];
          setPresentTransforms(newTransformDetails);
          const newFullGraph = res["data"]["graph_data"];
          setFullGraphData(newFullGraph);

          // On first load, default to the highest level (all transforms applied).
          // Otherwise keep the user's selection, clamped to the new max level in
          // case a transform was commented out.
          const currentActive = activeTransformsRef.current;
          const rawLevel = currentActive !== null
            ? currentActive.length
            : newTransformDetails.length;  // first load, show all transforms applied
          const newLevel = Math.min(rawLevel, newTransformDetails.length);
          setDisplayTransformLevel(newLevel);
          displayTransformLevelRef.current = newLevel;


          // Immediately sync activeTransforms to the clamped level so the
          // timeline indicator always agrees with what getSubtreeForLevel renders.
          const clampedActiveTransforms = currentActive !== null
            ? newTransformDetails.slice(0, newLevel)
            : newTransformDetails;
          setActiveTransforms(clampedActiveTransforms);
          activeTransformsRef.current = clampedActiveTransforms;

          const subtree = getSubtreeForLevel(newFullGraph, newLevel);
          setGraphData(subtree);

          // If starting debugger, sync level
          if (res["data"]["debugger_active"]) {
            const level = detectLevelFromSubtree(newFullGraph, subtree);
            if (level !== -1) {
              setDisplayTransformLevel(level);
              displayTransformLevelRef.current = level;
              setActiveTransforms(newTransformDetails.slice(0, level));
            }
          }

          visualizeSubtreeForLevel(newFullGraph, newLevel);
        }
        setShowLoadingTree(false);
      })
      .catch(function (error) {
        console.log(error);
        setShowLoadingTree(false);
      });
  };

  /**
   * Filters out pure comment-only line changes to avoid unnecessary
   * re-renders. Sets codeEditorData only when meaningful code has changed.
   *
   * @param {string} action - Editor action (unused, passed by editor callback).
   * @param {string} data   - Full current editor content.
   */
  const showCircuit = (action, data) => {
    // Do not change data if only a comment line is changed
    const newLines = data.split("\n");
    const oldLines = codeEditorData.split("\n");
    if (newLines.length !== oldLines.length) {
      setCodeEditorData(data);
      return;
    }

    let changes = [];
    for (let i = 0; i < newLines.length; i++) {
      // Check that the line is changed
      if (newLines[i] !== oldLines[i]) {
        // If both old and new lines start with a "#", it is a single line comment change. Do not add to changes!
        // This covers the cases where the whole line is a comment.
        if (
          newLines[i].replace(/\s/g, "")[0] === "#" &&
          oldLines[i].replace(/\s/g, "")[0] === "#"
        ) {
          continue;
        }

        /* If the whole line is not commented out, use the rules below:
              If new or old line does not include a # at all, it is not a comment change. Add to changes!
              If new or old line includes multiple # characters with other characters in between, it is a complicated line. Add to changes!
              If both new and old lines include a single #, check if the parts before the # are equal. If not, add to changes!	
              Check if the # character is in a string by counting " and ' characters before the # character. If yes, add to changes!
        */
        let newLineArr = newLines[i].split("#").filter((e) => e !== ""); // The filter is used because some people start comments with multiple "#" on comments
        let oldLineArr = oldLines[i].split("#").filter((e) => e !== "");

        if (newLineArr.length !== 2 || oldLineArr.length !== 2) {
          changes.push(newLines[i]);
          continue;
        }

        if (newLineArr[0] !== oldLineArr[0]) {
          changes.push(newLines[i]);
          continue;
        }

        // If odd number of " or ' before #, # must be in a string
        if (
          (newLineArr[0].split('"') - 1) % 2 === 1 ||
          (newLineArr[0].split("'") - 1) % 2 === 1
        ) {
          changes.push(newLines[i]);
        }

        // At this point we now that the changed line includes a single # that is not in a single line string.
        // We also know that the change in the line happened after the #, so it is a comment change.
        // Unless there is a multi-line string wrapping the whole line.
      }
    }

    if (changes.length > 0) {
      setCodeEditorData(data);
    }
  };

  /**
   * Runs when a debugger button is pressed, sends information about
   * the current debugger run to the server, requesting the desired
   * action to be processed
   *
   * @param {string} action - Debugger action. E.g. step into, next breakpoint
   */
  const debugNext = async (action) => {
    // Generate flatNodes from full graph data
    const flatNodes = flattenGraphNodes(fullGraphData);
    if (!flatNodes || flatNodes.length === 0) return;

    // Convert Set breakpointLines to Array
    const bpArray = Array.from(breakpointLines).map(String);
    let nextState;
    switch (action) {
      case "next_breakpoint":
        nextState = getNextBreakpointState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, bpArray, fullGraphData);
        break;
      case "prev_breakpoint":
        nextState = getPrevBreakpointState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, bpArray, fullGraphData);
        break;
      case "step_over":
        nextState = getStepOverState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, bpArray, fullGraphData);
        break;
      case "step_into":
        nextState = getStepIntoState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, fullGraphData);
        break;
      case "step_out":
        nextState = getStepOutState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, bpArray, fullGraphData);
        break;
      case "restart":
        nextState = getRestartState(flatNodes, fullGraphData);
        break;
      default:
        return;
    }

    setDebugIndex(nextState.debugIndex);
    setTransformStack(nextState.transformStack);
    setCurrentTransform(nextState.currentTransform);
    setCurrentTransformIdx(nextState.currentTransformIdx);
    setLine(parseInt(nextState.lineToHighlight) || -1);

    const level = nextState.graphDataWithDebugState ? nextState.transformStack.length : -1;
    if (level !== -1) {
      setDisplayTransformLevel(level);
      displayTransformLevelRef.current = level;
      setActiveTransforms(presentTransforms.slice(0, level));
    }

    if (nextState.isComplete) {
      setReadOnlyFlag(false);
      setDebuggerActive(false);

      const currentActive = activeTransformsRef.current;
      const rawLevel = currentActive.length;
      const newLevel = Math.min(rawLevel, presentTransforms.length);
      setDisplayTransformLevel(newLevel);
      displayTransformLevelRef.current = newLevel;

      const clampedActiveTransforms = currentActive !== null
        ? presentTransforms.slice(0, newLevel)
        : presentTransforms;
      setActiveTransforms(clampedActiveTransforms);
      activeTransformsRef.current = clampedActiveTransforms;
      visualizeSubtreeForLevel(fullGraphData, newLevel);

      return;
    }

    const outputResult = await getCircuitOutputandImg(
      sessionId,
      nextState.renderNodeIds,
      nextState.transformRootIdx,
      postSelectOverridesRef.current
    );

    if (outputResult.image) {
      setImgSrc("data:image/png;base64,".concat(outputResult.image));
    } else {
      setImgSrc("/defaultImage.png");
    }

    if (outputResult.circuit_output && nextState.graphDataWithDebugState) {
      let subGraph = getSubtreeForLevel(nextState.graphDataWithDebugState, level !== -1 ? level : 0);
      subGraph.nodes = subGraph.nodes.map(n =>
        n.parent_id === null ? { ...n, output: outputResult.circuit_output } : n
      );
      setGraphData(subGraph);
    } else if (nextState.graphDataWithDebugState) {
      let subGraph = getSubtreeForLevel(nextState.graphDataWithDebugState, level !== -1 ? level : 0);
      setGraphData(subGraph);
    }
  };

  const clearBreakpoints = () => {
    setBreakpointLines([]);
    setBreaks((b) => []);
  };

  /**
   * Clear states to be ready for a new debugger session.
   * Then, send a visualizeCircuit call to process the
   * code and get the trace / objects needed for debugging.
   */
  const startStopDebugger = () => {
    setImgSrc("/defaultImage.png");

    setShowLoading(true);
    setLine(-1);

    if (debuggerActive) { //if debugger is active, stop it
      // call service to reset all global variables
      const headers = {
        "Content-Type": "application/json",
      };
      axios
        .post(
          "/visualizeCircuit",
          {
            timestamp: new Date().getTime(),
            data: codeEditorData,
            postselect_overrides: postSelectOverridesRef.current,
            session_id: sessionId,
          },
          { headers: headers }
        )
        .then((res) => {
          setGraphData(getSubtreeForLevel(res["data"]["graph_data"], 0));
          setImgSrc("data:image/png;base64,".concat(res["data"]["image"]));
          setLine(-1);
          setReadOnlyFlag(false);
          setDebuggerActive(false);
          setShowLoading(false);
          setTransformStack([]);
          setCurrentTransform(-1);
          setCurrentTransformIdx(1);
          getDataFromBackEnd(codeEditorData);
        });
    } else { //if debugger is not active, start it
      const headers = {
        "Content-Type": "application/json",
      };
      axios
        .post(
          "/visualizeCircuit",
          {
            timestamp: new Date().getTime(),
            data: codeEditorData,
            postselect_overrides: postSelectOverridesRef.current,
            session_id: sessionId,
          },
          { headers: headers }
        )
        .then((res) => {
          setErrorInCode([]);
          if ("error" in res["data"]) {
            setErrorInCode(res["data"]["error"]);
            setLine(parseInt(res["data"]["error"][1].split(" ")[2]));
          } else {
            setLine(-1);
            setDeviceName(res["data"]["device_name"]);
            setDebugIndex(0);
            setCommands((c) => res["data"]["commands"]);
            setNumWires(res["data"]["num_wires"]);
            setNumShots(res["data"]["num_shots"]);

            // Start at base qnode tree
            setTransformStack([]);
            setCurrentTransform(-1);
            setCurrentTransformIdx(1);
            setReadOnlyFlag(true);
            setDebuggerActive(true);
            setActiveTransforms([]);
            setDisplayTransformLevel(0);
            displayTransformLevelRef.current = 0;

            const subtree = getSubtreeForLevel(res["data"]["graph_data"], 0);
            setGraphData(subtree);
          }
          setShowLoading(false);
        })
        .catch(function (error) {
          console.log(error);
          setShowLoading(false);
        });
    }
  };



  // Render
  const isTransformCommand = presentTransforms && presentTransforms.some((t) => t[1] === parseInt(line));
  const isPostSelectError = errorInCode.length != 0 && errorInCode[0] == POST_SELECT_ERROR_MSG;
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
      <div className="h-screen flex flex-col overflow-hidden">
        <Header />
        <div className="flex flex-row shrink-0">
          <div className="px-4 py-2 basis-1/2 flex flex-row items-center">
            <div className="flex flex-row items-center space-x-4 w-full">
              <InfoPopup />

              <button
                onClick={startStopDebugger}
                className={`flex items-center justify-center h-10 rounded px-8 text-xs transition-colors duration-150 border focus:shadow-outline text-white font-semibold ${debuggerActive
                  ? "bg-red-500 hover:bg-red-600 border-red-500"
                  : "bg-green-500 hover:bg-green-600 border-green-500"
                  }`}
              >
                {debuggerActive ? "Stop Debugger" : "Start Debugger"}
              </button>
              <button
                onClick={clearBreakpoints}
                className="group flex items-center justify-center h-10 w-10 rounded bg-white hover:bg-red-300 text-xs transition-colors duration-150 border focus:shadow-outline"
              >
                <ClearBreakpointsIcon />
                <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                  Clear Breakpoints
                </span>
              </button>

              {showLoading && (
                <div role="status" className="flex items-center">
                  <LoadingIcon />
                </div>
              )}

              {/* Debugger button function calls */}
              {debuggerActive ? (
                <div>
                  <button
                    onClick={() => {
                      debugNext("next_breakpoint");
                    }}
                    className="group rounded bg-white hover:bg-gray-300 p-2.5 my-0 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline"
                  >
                    <ContinueIcon />
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Next Breakpoint
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      debugNext("prev_breakpoint");
                    }}
                    className="group rounded bg-white hover:bg-gray-300 p-2.5 my-0 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline"
                  >
                    <ReverseContinueIcon />
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Previous Breakpoint
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      debugNext("step_over");
                    }}
                    className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline"
                  >
                    <StepOverIcon />
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Step Over
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      debugNext("step_into");
                    }}
                    disabled={isTransformCommand}
                    className={"group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline" + (isTransformCommand ? " cursor-not-allowed pointer-events-none" : "")}
                  >
                    {isTransformCommand ? <StepIntoIconDisabled /> : <StepIntoIcon />}
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Step Into
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      debugNext("step_out");
                    }}
                    disabled={isTransformCommand}
                    className={"group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline" + (isTransformCommand ? " cursor-not-allowed pointer-events-none" : "")}
                  >
                    {isTransformCommand ? <StepOutIconDisabled /> : <StepOutIcon />}
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-black p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Step Out
                    </span>
                  </button>
                  <button
                    onClick={() => {
                      debugNext("restart");
                    }}
                    className="group rounded bg-white hover:bg-gray-300 p-2.5 mx-1 text-xs transition-colors duration-150 border focus:shadow-outline"
                  >
                    <RestartIcon />
                    <span className="absolute top-2 scale-0 rounded bg-gray-200 border border-gray-400 p-1 text-xs text-black group-hover:scale-100 transition-all">
                      Restart
                    </span>
                  </button>
                </div>
              ) : (
                <></>
              )}
            </div>
          </div>

          <div className="w-full px-4 py-2 basis-1/2 flex flex-row-reverse items-center">
            <a
              href="https://github.com/QSAR-UBC/CircInspect/issues"
              target="_blank"
            >
              <button className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-8 rounded ml-4">
                Give Feedback
              </button>
            </a>
            <p className="mx-8">
              You are currently using CircInspect{" "}
              <span className="text-pink-600">{circInspectVersion}</span> with
              Pennylane{" "}
              <a
                className="text-pink-600"
                href={
                  "https://github.com/PennyLaneAI/pennylane/releases/tag/v" +
                  pennylaneVersion
                }
                target="_blank"
                rel="noreferrer"
              >
                {pennylaneVersion}
              </a>
              <br />
              See a list of{" "}
              <button
                className="text-pink-600"
                onClick={() => setShowLibraries(true)}
              >
                available libraries
              </button>
              .
            </p>
          </div>
        </div>

        <div className="flex flex-row flex-1 min-h-0 gap-3 px-4 pb-2">
          <div className="w-1/2 h-full">
            <Qeditor
              className="CodeEditorWindow"
              height="100%"
              breaks={breaks}
              setbreaks={setBreaks}
              highlightline={line}
              focuson={true}
              value={code}
              setvalue={setCode}
              theme={theme.value}
              readOnly={readOnlyFlag}
              onChange={showCircuit}
              defaultValue={DEFAULT_CODE}
            />
          </div>

          <div className="flex-1 h-full flex flex-col gap-2">
            <div className="flex-1 min-h-0 overflow-hidden">
              <OutputWindow imgsrc={imgsrc} isError={errorInCode.length != 0} />
            </div>
            <div className="flex-1 min-h-0 relative overflow-hidden rounded-lg bg-[#1d1f21]">
              <div className="flex flex-col h-full relative">
                {/* Error Overlay */}
                {errorInCode.length != 0 && (
                  <div className="absolute inset-0 z-50 flex items-center justify-center p-6 bg-black bg-opacity-20 backdrop-blur-[1px]">
                    <div className="max-w-md w-full bg-[#2d1a1a] border border-red-500 rounded-xl p-6 shadow-2xl transform transition-all animate-in fade-in zoom-in duration-300 relative">
                      {isPostSelectError && (
                        <button
                          onClick={() => {
                            setErrorInCode([]);
                            setPostSelectOverrides(prevPostSelectOverridesRef.current);
                            postSelectOverridesRef.current = prevPostSelectOverridesRef.current;
                          }}
                          className="absolute top-3 right-3 text-red-400 hover:text-red-200 transition-colors"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                      <div className="flex items-center gap-3 mb-4 text-red-400">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <h3 className="text-lg font-bold">Execution Error</h3>
                      </div>
                      <div className="bg-black bg-opacity-30 rounded-lg p-4 font-mono text-sm text-red-200 border border-red-900 break-words whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {errorInCode[0]}: {errorInCode[1]}
                      </div>
                    </div>
                  </div>
                )}

                {/* Loading Overlay */}
                {showLoadingTree && (
                  <div className="absolute inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
                    <LoadingIcon />
                  </div>
                )}

                {/* Main Content Area */}
                <div className={`flex flex-row h-full transition-all duration-500 ${errorInCode.length !== 0 ? "blur-[3px] grayscale-[0.2] opacity-75 scale-[0.99]" : ""}`}>
                  {/* The Command Tree Graph */}
                  <div className="flex-1 min-h-0">
                    <CommandTreeGraph
                      graphData={graphData}
                      onNodeSelect={handleNodeSelect}
                      isDebuggerActive={debuggerActive}
                      onPostSelectApply={handlePostSelectApply}
                    />
                  </div>

                  {/* Transform Selection Area (Vertical Timeline) */}
                  {presentTransforms && presentTransforms.length > 0 && (
                    <TransformTimeline
                      presentTransforms={presentTransforms}
                      activeTransforms={activeTransforms}
                      onTransformSelect={handleTransformSelect}
                      isDebuggerActive={debuggerActive}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Rodal
        customStyles={{ overflow: "auto", padding: "10px", cursor: "default" }}
        visible={showLibraries}
        onClose={() => setShowLibraries(false)}
        height={480}
        width={400}
      >
        <h1 className="font-bold text-xl mx-4 mt-2">Available Libraries</h1>
        <div className="h-4"></div>
        <table className="w-5/6 m-auto border border-gray-700">
          <tbody>
            {availableLibraries.map((a) => (
              <tr className="even:bg-gray-300" key={a[0]}>
                <td className="p-1">{a[0]}</td>
                <td className={a[1] === "unavailable" ? "text-red-600" : ""}>
                  {a[1]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="h-4"></div>
        <p className="mx-4">
          If you need another library, please let us know by clicking the
          <b className="font-bold"> Give Feedback</b>{" "}
          <span className="inline-flex align-middle">
            <MarkGithubIcon size={24} />
          </span>{" "}
          button on the top right!
        </p>
      </Rodal>
    </>
  );
};
export default Landing;
