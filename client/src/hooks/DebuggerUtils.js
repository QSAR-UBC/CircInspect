/**
 * Flattens a graph (nodes + edges) into a DFS-ordered array of node objects.
 * The traversal starts from the root — the node that is not the target of any
 * edge — and visits children in ascending numeric ID order. Transforms and
 * their nested commands are therefore encountered in execution order.
 *
 * @param {Object} graphData - Graph object with `nodes` (array) and `edges` (array).
 * @returns {Object[]} Flat, DFS-ordered array of node objects, or [] if graphData
 *   is missing or malformed.
 */
export function flattenGraphNodes(graphData) {
    if (!graphData || !graphData.nodes || !graphData.edges) return [];

    const nodeMap = {};
    graphData.nodes.forEach(n => nodeMap[n.id] = n);

    const adjList = {};
    graphData.edges.forEach(edge => {
        if (!adjList[edge.source]) adjList[edge.source] = [];
        adjList[edge.source].push(edge.target);
    });

    // Root node is minimal ID that isn't a target, usually id: 0 (the base qnode) or 1
    const rootNodes = graphData.nodes.filter(n => !graphData.edges.some(e => e.target === n.id));
    let root = rootNodes.length > 0 ? rootNodes[0] : nodeMap["0"] || nodeMap["1"];

    const flatNodes = [];
    const visited = new Set();

    function dfs(nodeId) {
        if (nodeId == null || visited.has(nodeId)) return;
        visited.add(nodeId);
        if (nodeMap[nodeId]) {
            flatNodes.push({ ...nodeMap[nodeId] });
        }
        if (adjList[nodeId]) {
            adjList[nodeId].sort((a, b) => parseInt(a) - parseInt(b)).forEach(childId => {
                dfs(childId);
            });
        }
    }

    if (root) dfs(root.id);
    return flatNodes;
}

/**
 * Returns all nodes in flatNodes that share the same parent transform as `node`,
 * i.e. nodes whose `parent_id` matches `node.parent_id`. These are the siblings
 * that a "step over" or "step out" action should land on.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {Object|null} node - The reference node. Returns [] if null or has no parent.
 * @returns {Object[]} Array of sibling nodes (includes `node` itself).
 */
export function getSiblingNodes(flatNodes, node) {
    if (!node || !node.parent_id) return [];
    return flatNodes.filter(n => String(n.parent_id) === String(node.parent_id));
}

/**
 * Looks up a node in flatNodes by its ID, comparing as strings to avoid
 * strict type mismatches between numeric and string IDs.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number|null} id - The ID to search for.
 * @returns {Object|null} The matching node, or null if not found.
 */
export function getNodeById(flatNodes, id) {
    if (!id) return null;
    return flatNodes.find(n => String(n.id) === String(id)) || null;
}

/**
 * Pops the top entry off the transform stack and returns the resulting
 * active transform ID and its index in flatNodes. Used when navigating
 * backward past a transform boundary. Mutates a copy of the stack, not
 * the original.
 *
 * @param {string[]} transformStack - Current stack of active transform node IDs.
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @returns {{ currentTransform: number, currentTransformIdx: number }}
 *   The new active transform ID (-1 if the stack is now empty) and its
 *   flatNodes index (defaults to 1 if not found).
 */
export function popTransform(transformStack, flatNodes) {
    const newStack = [...transformStack];
    newStack.pop();
    if (newStack.length === 0) {
        return { currentTransform: -1, currentTransformIdx: 1, newStack };
    }
    const currentTransformId = newStack[newStack.length - 1];

    let currentTransformIdx = 1;
    const idx = flatNodes.findIndex(n => String(n.id) === String(currentTransformId));
    if (idx !== -1) {
        currentTransformIdx = idx;
    }
    return { currentTransform: currentTransformId, currentTransformIdx, newStack };
}

/**
 * Computes the full resolved debug state to be stored in React state.
 * Determines which nodes are active, dimmed, or complete based on the
 * proposed debug index, then derives the set of node IDs to render in
 * the circuit panel and the source line to highlight in the code editor.
 *
 * @param {Object[]} flatNodes - DFS-ordered flat array of all graph nodes.
 * @param {number} newDebugIdx - Proposed next debug index (-1 signals completion).
 * @param {string[]} newTransformStack - Updated transform stack after the step.
 * @param {number} newCurrTransform - Updated active transform node ID.
 * @param {number} newCurrTransformIdx - flatNodes index of the active transform.
 * @param {Object} graphData - Full graph data whose node dim/active flags will
 *   be updated to reflect the new debug position.
 * @returns {{
 *   debugIndex: number,
 *   transformStack: string[],
 *   currentTransform: number,
 *   currentTransformIdx: number,
 *   lineToHighlight: string,
 *   isComplete: boolean,
 *   graphDataWithDebugState: Object,
 *   renderNodeIds: string[],
 *   transformRootIdx: number|null
 * }} The complete debug state object consumed by Landing.js.
 */
export function resolveDebugState(flatNodes, newDebugIdx, newTransformStack, newCurrTransform, newCurrTransformIdx, graphData) {
    let finalDebugIdx = newDebugIdx;
    let isComplete = false;

    if (finalDebugIdx === -1 || finalDebugIdx >= flatNodes.length) {
        finalDebugIdx = flatNodes.length;
        isComplete = true;
    }

    const nodesCopy = flatNodes.map(n => ({ ...n }));
    let lineToHighlight = "-1";

    if (isComplete) {
        finalDebugIdx = -1;
        nodesCopy.forEach(node => {
            node.node_dimmed = false;
            node.active_debug = false;
        });
    } else {
        nodesCopy.forEach(node => {
            node.node_dimmed = true;
            node.active_debug = false;
        });
        if (finalDebugIdx >= 0 && finalDebugIdx < nodesCopy.length) {
            nodesCopy[finalDebugIdx].active_debug = true;
            nodesCopy[finalDebugIdx].node_dimmed = false;
        }

        const targetCommand = nodesCopy[finalDebugIdx];
        if (targetCommand && targetCommand.line_type === "transform") {
            // Undim all children of the transform
            targetCommand.children.forEach(childId => {
                const childNode = nodesCopy.find(n => String(n.id) === String(childId));
                if (childNode) childNode.node_dimmed = false;
            });
        } else {
            for (let i = newCurrTransformIdx; i <= finalDebugIdx; i++) {
                if (nodesCopy[i]) nodesCopy[i].node_dimmed = false;
            }
        }
        lineToHighlight = targetCommand && targetCommand.line_number != null ? String(targetCommand.line_number) : "-1";
    }

    let renderNodeIds = [];
    if (finalDebugIdx !== -1) {
        const target = nodesCopy[finalDebugIdx];
        let currentId = target ? target.parent_id : null;
        const activePath = new Set();
        while (currentId !== null && currentId !== undefined) {
            activePath.add(String(currentId));
            const pNode = nodesCopy.find(n => String(n.id) === String(currentId));
            if (pNode) currentId = pNode.parent_id;
            else break;
        }

        if (target && target.line_type === "transform") {
            target.children.forEach(childId => {
                const childNode = nodesCopy.find(n => String(n.id) === String(childId));
                if (childNode) renderNodeIds.push(childNode.id);
            });
        } else {
            for (let i = newCurrTransformIdx; i <= finalDebugIdx; i++) {
                const cmd = nodesCopy[i];
                if (!cmd) continue;
                if (cmd.parent_id === null || activePath.has(String(cmd.parent_id))) {
                    if (activePath.has(String(cmd.id))) continue;
                    renderNodeIds.push(cmd.id);
                }
            }
        }
    }

    const newGraphData = { ...graphData };
    if (newGraphData.nodes) {
        newGraphData.nodes = newGraphData.nodes.map(n => {
            const stateNode = nodesCopy.find(fn => fn.id === n.id);
            if (stateNode) {
                return { ...n, node_dimmed: stateNode.node_dimmed, active_debug: stateNode.active_debug };
            }
            return n;
        });
    }

    return {
        debugIndex: finalDebugIdx,
        transformStack: newTransformStack,
        currentTransform: newCurrTransform,
        currentTransformIdx: newCurrTransformIdx,
        lineToHighlight,
        isComplete,
        graphDataWithDebugState: newGraphData,
        renderNodeIds,
        transformRootIdx: newTransformStack.length > 0 ? newCurrTransform : null
    };
}