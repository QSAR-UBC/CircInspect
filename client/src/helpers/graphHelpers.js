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

/**
 * Filters a {nodes, edges} graph down to only the nodes marked `visible` by the
 * backend, pruning each surviving node's `children` array and the edge list to
 * match. Invisible commands (e.g. classical lines) still exist in the full tree
 * for the debugger to step through, but should never be rendered in the command
 * tree visualization.
 *
 * @param {Object} graph - Graph object with `nodes` (array) and `edges` (array).
 * @returns {Object} Filtered {nodes, edges} containing only visible nodes.
 */
export const filterVisibleNodes = (graph) => {
  if (!graph?.nodes?.length) return graph;

  const visibleIds = new Set(graph.nodes.filter(n => n.visible).map(n => n.id));

  const nodes = graph.nodes
    .filter(n => visibleIds.has(n.id))
    .map(n => ({ ...n, children: (n.children || []).filter(id => visibleIds.has(id)) }));

  const edges = graph.edges.filter(
    e => visibleIds.has(e.source) && visibleIds.has(e.target)
  );

  return { nodes, edges };
};

/**
 * Given the full unified graph data (all transform levels) and a transform level index,
 * returns a filtered graph containing only the subtree for that level.
 *
 * The unified tree has the shape:
 *   root (parent_id=null)
 *     ── base_qnode   (index 0 - no transforms)
 *     ── transform_1  (index 1 - first transform applied)
 *     ── transform_2  (index 2 - both transforms applied)
 *
 * @param {Object} fullGraph - Full graph_data from the backend {nodes, edges}
 * @param {number} level     - 0 = base qnode, N = Nth transform branch
 * @returns {Object} Filtered {nodes, edges} for just that branch
 */
export const getSubtreeForLevel = (fullGraph, level) => {
  if (!fullGraph?.nodes?.length) return filterVisibleNodes(fullGraph);

  // Build adjacency maps from edges (parent_id is unreliable — use edges directly)
  const childrenMap = {}; // parent id -> [child ids]
  const parentSet = new Set(); // ids that appear as edge targets (have a parent)
  fullGraph.edges.forEach(e => {
    const src = String(e.source);
    const tgt = String(e.target);
    if (!childrenMap[src]) childrenMap[src] = [];
    childrenMap[src].push(tgt);
    parentSet.add(tgt);
  });

  // Find root: the node whose id is NOT a target of any edge
  const rootId = String(
    fullGraph.nodes.find(n => !parentSet.has(String(n.id)))?.id
  );
  if (!rootId) return filterVisibleNodes(fullGraph);

  // Get root's direct children sorted by id (ascending = original insertion order)
  const rootChildren = (childrenMap[rootId] || []).sort((a, b) => Number(a) - Number(b));
  if (!rootChildren.length) return filterVisibleNodes(fullGraph);

  // Select the child at `level`, clamped to valid range
  const targetId = rootChildren[Math.min(level, rootChildren.length - 1)];

  // BFS from targetId to collect all descendants
  const included = new Set();
  const queue = [targetId];
  while (queue.length) {
    const id = queue.shift();
    if (included.has(id)) continue;
    included.add(id);
    (childrenMap[id] || []).forEach(cid => queue.push(cid));
  }

  // Filter nodes and edges; mark the target node as new root (parent_id = null)
  const nodeById = Object.fromEntries(fullGraph.nodes.map(n => [String(n.id), n]));
  const filteredNodes = [...included].map(id => {
    const n = nodeById[id];
    return id === targetId ? { ...n, parent_id: null } : n;
  });

  const filteredEdges = fullGraph.edges.filter(
    e => included.has(String(e.source)) && included.has(String(e.target))
  );

  return filterVisibleNodes({ nodes: filteredNodes, edges: filteredEdges });
};
