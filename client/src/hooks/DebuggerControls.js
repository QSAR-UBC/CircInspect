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

import axios from "axios";
import { resolveDebugState, popTransform, getSiblingNodes, getNodeById } from "./DebuggerUtils";

/**
 * Initialises the mutable working state shared across all debugger step functions.
 * Clones the transform stack so mutations don't affect the original React state,
 * and normalises breakpoints to an array of strings once, up front.
 */
function createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints = []) {
    return {
        nextDebugIndex: debugIndex,
        nextTransformStack: [...transformStack],
        nextTransform: currentTransform,
        nextTransformIdx: currentTransformIdx,
        breakStrs: Array.isArray(breakpoints)
            ? breakpoints.map(String)
            : Array.from(breakpoints).map(String),
    };
}

/**
 * Returns the next debugger state after advancing to the next breakpoint.
 * Scans forward from the current position through flatNodes, updating the
 * transform stack as transforms are encountered, and stops at the first node
 * whose line number matches a breakpoint. Returns a completed state (index -1)
 * if no breakpoint is found ahead of the current position.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} debugIndex - Current position in flatNodes.
 * @param {string[]} transformStack - Stack of active transform node IDs.
 * @param {number} currentTransform - ID of the currently active transform.
 * @param {number} currentTransformIdx - flatNodes index of the current transform.
 * @param {string[]} breakpoints - Active breakpoint line numbers.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getNextBreakpointState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints, graphData) {
    let { nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, breakStrs } =
        createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints);

    for (let i = debugIndex + 1; i < flatNodes.length; i++) {
        const cmd = flatNodes[i];
        if (cmd.line_type === "transform") {
            nextTransformStack.push(cmd.id);
            nextTransform = cmd.id;
            nextTransformIdx = i;
        }
        if (breakStrs.includes(String(cmd.line_number))) {
            nextDebugIndex = i;
            break;
        }
    }
    if (nextDebugIndex === debugIndex) nextDebugIndex = -1;
    return resolveDebugState(flatNodes, nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, graphData);
}


/**
 * Returns the next debugger state after retreating to the previous breakpoint.
 * Scans backward from the current position, unwinding the transform stack as
 * transforms are passed over, and stops at the first node whose line number
 * matches a breakpoint. Returns a completed state (index -1) if no breakpoint
 * is found before the current position.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} debugIndex - Current position in flatNodes.
 * @param {string[]} transformStack - Stack of active transform node IDs.
 * @param {number} currentTransform - ID of the currently active transform.
 * @param {number} currentTransformIdx - flatNodes index of the current transform.
 * @param {string[]} breakpoints - Active breakpoint line numbers.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getPrevBreakpointState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints, graphData) {
    let { nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, breakStrs } =
        createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints);

    if (flatNodes[debugIndex] && flatNodes[debugIndex].line_type === "transform" && nextTransformStack.length > 0) {
        const popped = popTransform(nextTransformStack, flatNodes);
        nextTransform = popped.currentTransform;
        nextTransformIdx = popped.currentTransformIdx;
    }

    let found = false;
    for (let i = debugIndex - 1; i > 0; i--) {
        const cmd = flatNodes[i];
        const isBp = breakStrs.includes(String(cmd.line_number));
        if (cmd.line_type === "transform" && !isBp && nextTransformStack.length > 0) {
            const popped = popTransform(nextTransformStack, flatNodes);
            nextTransform = popped.currentTransform;
            nextTransformIdx = popped.currentTransformIdx;
        }
        if (isBp) {
            nextDebugIndex = i;
            found = true;
            break;
        }
    }
    if (!found) nextDebugIndex = -1;
    return resolveDebugState(flatNodes, nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, graphData);
}


/**
 * Returns the next debugger state after a "step over" action.
 * Advances to the next sibling of the current node (or a sibling of its
 * parent), skipping any nested transform body. Also stops early at a
 * breakpoint. Returns a completed state (index -1) if neither a sibling
 * landing nor a breakpoint is found.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} debugIndex - Current position in flatNodes.
 * @param {string[]} transformStack - Stack of active transform node IDs.
 * @param {number} currentTransform - ID of the currently active transform.
 * @param {number} currentTransformIdx - flatNodes index of the current transform.
 * @param {string[]} breakpoints - Active breakpoint line numbers.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getStepOverState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints, graphData) {
    let { nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, breakStrs } =
        createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints);

    const currCmd = flatNodes[debugIndex];
    const sibs = getSiblingNodes(flatNodes, currCmd);
    const parent = getNodeById(flatNodes, currCmd ? currCmd.parent_id : null);
    const parentSibs = getSiblingNodes(flatNodes, parent);

    let found = false;
    for (let i = debugIndex + 1; i < flatNodes.length; i++) {
        const cmd = flatNodes[i];
        const isBp = breakStrs.includes(String(cmd.line_number));
        const isSibLanding = sibs.some(s => String(s.id) === String(cmd.id)) || parentSibs.some(s => String(s.id) === String(cmd.id));

        if (isBp || isSibLanding) {
            if (cmd.line_type === "transform") {
                nextTransformStack.push(cmd.id);
                nextTransform = cmd.id;
                nextTransformIdx = i;
            }
            nextDebugIndex = i;
            found = true;
            break;
        }
    }
    if (!found) nextDebugIndex = -1;
    return resolveDebugState(flatNodes, nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, graphData);
}


/**
 * Returns the next debugger state after a "step into" action.
 * Advances exactly one position forward in flatNodes, entering any transform
 * body. Automatically skips "root" marker nodes, which are structural
 * placeholders that should not be surfaced to the user.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} debugIndex - Current position in flatNodes.
 * @param {string[]} transformStack - Stack of active transform node IDs.
 * @param {number} currentTransform - ID of the currently active transform.
 * @param {number} currentTransformIdx - flatNodes index of the current transform.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getStepIntoState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, graphData) {
    let { nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx } =
        createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx);

    if (debugIndex + 1 < flatNodes.length) {
        nextDebugIndex += 1;
        if (flatNodes[nextDebugIndex] && flatNodes[nextDebugIndex].line_type === "transform") {
            nextTransformStack.push(flatNodes[nextDebugIndex].id);
            nextTransform = flatNodes[nextDebugIndex].id;
            nextTransformIdx = nextDebugIndex;
        }
        if (flatNodes[nextDebugIndex] && flatNodes[nextDebugIndex].line_type === "root" && nextDebugIndex + 1 < flatNodes.length) {
            nextDebugIndex += 1;
        }
    } else {
        nextDebugIndex = -1;
    }
    return resolveDebugState(flatNodes, nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, graphData);
}


/**
 * Returns the next debugger state after a "step out" action.
 * Advances past the remaining nodes in the current transform's body and
 * lands on the next sibling of the transform's parent. Also stops early
 * at a breakpoint. Returns a completed state (index -1) if no parent
 * sibling landing or breakpoint is found.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} debugIndex - Current position in flatNodes.
 * @param {string[]} transformStack - Stack of active transform node IDs.
 * @param {number} currentTransform - ID of the currently active transform.
 * @param {number} currentTransformIdx - flatNodes index of the current transform.
 * @param {string[]} breakpoints - Active breakpoint line numbers.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getStepOutState(flatNodes, debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints, graphData) {
    let { nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, breakStrs } =
        createDebugState(debugIndex, transformStack, currentTransform, currentTransformIdx, breakpoints);

    const currCmd = flatNodes[debugIndex];
    if (currCmd && currCmd.line_type === "transform") {
        nextTransformStack.push(currCmd.id);
        nextTransform = currCmd.id;
        nextTransformIdx = debugIndex;
    }

    let ancestor = getNodeById(flatNodes, currCmd ? currCmd.parent_id : null);
    let parentSibs = getSiblingNodes(flatNodes, ancestor);
    let hasLandingAhead = parentSibs.some(s => flatNodes.findIndex(n => String(n.id) === String(s.id)) > debugIndex);
    while (ancestor && !hasLandingAhead) {
        ancestor = getNodeById(flatNodes, ancestor.parent_id);
        parentSibs = getSiblingNodes(flatNodes, ancestor);
        hasLandingAhead = parentSibs.some(s => flatNodes.findIndex(n => String(n.id) === String(s.id)) > debugIndex);
    }

    let found = false;
    if (ancestor) {
        for (let i = debugIndex + 1; i < flatNodes.length; i++) {
            const cmd = flatNodes[i];
            const isBp = breakStrs.includes(String(cmd.line_number));
            const isParentLanding = parentSibs.some(s => String(s.id) === String(cmd.id));

            if (cmd.line_type === "transform" && !(isBp || isParentLanding)) {
                nextTransformStack.push(cmd.id);
                nextTransform = cmd.id;
                nextTransformIdx = i;
            }
            if (isBp || isParentLanding) {
                if (cmd.line_type === "transform") {
                    nextTransformStack.push(cmd.id);
                    nextTransform = cmd.id;
                    nextTransformIdx = i;
                }
                nextDebugIndex = i;
                found = true;
                break;
            }
        }
    }
    if (!found) nextDebugIndex = -1;
    return resolveDebugState(flatNodes, nextDebugIndex, nextTransformStack, nextTransform, nextTransformIdx, graphData);
}


/**
 * Returns the initial debugger state, resetting to the first non-root node
 * (index 1) with an empty transform stack.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {Object} graphData - Full graph data used to build the resolved state.
 * @returns {Object} Resolved debug state from resolveDebugState.
 */
export function getRestartState(flatNodes, graphData) {
    return resolveDebugState(flatNodes, 1, [], -1, 1, graphData);
}

/**
 * Fetches the circuit diagram image and measurement output for the current
 * debug position by posting the active node IDs to the /debugOutput endpoint.
 *
 * @param {number|null} port - Backend simulator port. Returns empty result if null.
 * @param {string[]} nodeIds - IDs of the nodes currently visible in the circuit.
 * @param {number} transformRootIdx - ID of the active transform root node.
 * @param {Object} postselectOverrides - Map of qubit index to postselection value.
 * @returns {image: string|null, circuit_output: string} Circuit image
 *   (base64 or URL) and the measurement output string.
 */
export const getCircuitOutputandImg = async (sessionId, nodeIds, transformRootIdx, postselectOverrides) => {
    try {
        const res = await axios.post("/debugOutput", {
            session_id: sessionId,
            node_ids: nodeIds,
            transform_root_idx: transformRootIdx,
            postselect_overrides: postselectOverrides
        });

        return {
            image: res.data.image,
            circuit_output: res.data.circuit_output,
        };
    } catch (err) {
        console.error("debugOutput error:", err);
        return { image: null, circuit_output: `Error tracing output` };
    }
};
