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

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import {
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import CircInspectNode from "./CircInspectNode";
import GraphView from "./GraphView";

// Shared style for all UI overlay buttons (Legend header, Expand, Close)
const overlayButtonStyle = {
  background: "#1a1a1a",
  border: "1px solid #444",
  borderRadius: "10px",
  padding: "6px 12px",
  color: "#888",
  fontSize: "10px",
  fontFamily: "'Quicksand', sans-serif",
  fontWeight: "bold",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  cursor: "pointer",
  userSelect: "none",
};

// ─── Layout ───────────────────────────────────────────────────────────────────

// Uses dagre to compute a top-down tree layout from raw nodes and edges.
const getLayoutedElements = (nodes, edges, rootId) => {
  if (nodes.length === 0) return { nodes, edges };

  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", ranksep: 80, nodesep: 70 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((node) => {
    // Standard node dimensions for dagre planning
    const w = 100;
    const h = 100;
    g.setNode(node.id, { width: w, height: h });
  });

  edges.forEach((edge) => g.setEdge(edge.source, edge.target));
  dagre.layout(g);

  // Pin coordinates relative to the root node (or the first node) to prevent jumpiness on bounding box changes
  const rootDagrePos = rootId ? g.node(rootId) : g.node(nodes[0].id);

  return {
    nodes: nodes.map((node) => {
      const { x, y } = g.node(node.id);
      return {
        ...node,
        position: {
          x: x - rootDagrePos.x,
          y: y - rootDagrePos.y
        }
      };
    }),
    edges,
  };
};

const nodeTypes = { circInspect: CircInspectNode };

// ─── Main Component ───────────────────────────────────────────────────────────

export default function CommandTreeGraph({ graphData, onNodeSelect, isDebuggerActive, onPostSelectApply }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onNodesChangeWrapped = useCallback((changes) => {
    onNodesChange(changes.filter(c => c.type !== 'remove'));
  }, [onNodesChange]);

  const onEdgesChangeWrapped = useCallback((changes) => {
    onEdgesChange(changes.filter(c => c.type !== 'remove'));
  }, [onEdgesChange]);

  const [selectedNodeId, setSelectedNodeId] = useState(null);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    const rfNode = nodes.find((n) => n.id === selectedNodeId);
    return rfNode ? rfNode.data : null;
  }, [selectedNodeId, nodes]);

  const [fullscreen, setFullscreen] = useState(false);

  // Persistence state
  const [collapsedPathIds, setCollapsedPathIds] = useState(new Set());
  const lastRootName = useRef(null);

  // Suppress ResizeObserver error
  useEffect(() => {
    const resizeObserverErr = "ResizeObserver loop completed with undelivered notifications.";
    const observer = new MutationObserver(() => {
      const overlay = document.getElementById("webpack-dev-server-client-overlay");
      if (overlay?.contentDocument?.body?.innerText?.includes(resizeObserverErr)) overlay.style.display = "none";
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  // Escape key for fullscreen
  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === "Escape") setFullscreen(false); };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Stable path ID computation
  const pathIdMap = useMemo(() => {
    if (!graphData?.nodes) return {};
    const nodesById = Object.fromEntries(graphData.nodes.map(n => [String(n.id), n]));

    const childrenByParent = {};
    graphData.nodes.forEach(n => {
      const pId = n.parent_id === null ? "null" : String(n.parent_id);
      if (!childrenByParent[pId]) childrenByParent[pId] = [];
      childrenByParent[pId].push(n);
    });
    Object.values(childrenByParent).forEach(arr => arr.sort((a, b) => Number(a.id) - Number(b.id)));

    const memo = {};

    const getPath = (id) => {
      const sid = String(id);
      if (memo[sid]) return memo[sid];
      const node = nodesById[sid];
      if (!node) return "unknown";

      const parentId = node.parent_id === null ? null : String(node.parent_id);
      const nodeName = node.tree_node_name || "node";

      if (parentId === null || !nodesById[parentId]) {
        memo[sid] = nodeName;
        return nodeName;
      }

      const pIdStr = parentId === null ? "null" : parentId;
      const siblings = childrenByParent[pIdStr] || [];

      const sameNameSiblings = siblings.filter(s => s.tree_node_name === nodeName);
      const index = sameNameSiblings.findIndex(s => String(s.id) === sid);

      const path = getPath(parentId) + "/" + nodeName + "[" + (index >= 0 ? index : 0) + "]";
      memo[sid] = path;
      return path;
    };

    const map = {};
    graphData.nodes.forEach(n => { map[String(n.id)] = getPath(n.id); });
    return map;
  }, [graphData]);

  // Initial collapse logic
  useEffect(() => {
    if (!graphData?.nodes?.length) return;
    const rootNode = graphData.nodes.find(n => n.parent_id === null) || graphData.nodes[0];
    const newRootName = rootNode.tree_node_name;

    if (lastRootName.current !== newRootName) {
      lastRootName.current = newRootName;
      const initialCollapsed = new Set();
      graphData.nodes.forEach(n => {
        if (n.children && n.children.length > 0) initialCollapsed.add(pathIdMap[String(n.id)]);
      });
      setCollapsedPathIds(initialCollapsed);
    }
  }, [graphData, pathIdMap]);

  // Transform graphData to visible ReactFlow elements
  useEffect(() => {
    if (!graphData?.nodes?.length) return;

    const nodesById = Object.fromEntries(graphData.nodes.map(n => [String(n.id), n]));

    const hiddenNodes = new Set();
    const findDescendants = (nodeId) => {
      const node = nodesById[String(nodeId)];
      if (node?.children) {
        node.children.forEach(childId => {
          hiddenNodes.add(String(childId));
          findDescendants(childId);
        });
      }
    };

    graphData.nodes.forEach(n => {
      const pId = pathIdMap[String(n.id)];
      if (collapsedPathIds.has(pId)) findDescendants(n.id);
    });

    const visibleNodes = graphData.nodes.filter(n => !hiddenNodes.has(String(n.id)));
    const visibleEdges = graphData.edges.filter(e => !hiddenNodes.has(String(e.source)) && !hiddenNodes.has(String(e.target)));

    const rawNodes = visibleNodes.map((n) => ({
      id: String(n.id),
      type: "circInspect",
      data: {
        label: n.tree_node_name || String(n.id), ...n,
        isCollapsed: collapsedPathIds.has(pathIdMap[String(n.id)]),
        onToggleCollapse: () => {
          const pId = pathIdMap[String(n.id)];
          setCollapsedPathIds(prev => {
            const next = new Set(prev);
            if (next.has(pId)) next.delete(pId); else next.add(pId);
            return next;
          });
        },
        hasChildren: n.children && n.children.length > 0
      },
    }));

    const rawEdges = visibleEdges.map((e, i) => ({
      id: `e${i}`, source: String(e.source), target: String(e.target),
      animated: true, style: { stroke: "#555" },
    }));

    const rootNode = graphData.nodes.find(n => n.parent_id === null) || graphData.nodes[0];
    const { nodes: laid, edges: laidEdges } = getLayoutedElements(rawNodes, rawEdges, String(rootNode.id));
    setNodes(laid);
    setEdges(laidEdges);
  }, [graphData, collapsedPathIds, pathIdMap, setNodes, setEdges]);

  const onPaneClick = useCallback(() => setSelectedNodeId(null), []);
  const onNodeClick = useCallback((_, node) => {
    setSelectedNodeId(node.id);
    // Don't update circuit image for mid-measurement nodes — parent image shows all branches
    if (onNodeSelect && node.data.subtree_circuit_img && !node.data.is_mid_measure) onNodeSelect(node.data.subtree_circuit_img);
  }, [onNodeSelect]);

  const expandAll = () => setCollapsedPathIds(new Set());
  const collapseAll = () => {
    const all = new Set();
    graphData.nodes.forEach(n => { if (n.children?.length > 0) all.add(pathIdMap[String(n.id)]); });
    setCollapsedPathIds(all);
  };

  const [postSelectInput, setPostSelectInput] = useState("");
  const [postSelectError, setPostSelectError] = useState("");
  const [postSelectSuccess, setPostSelectSuccess] = useState(false);

  // Reset postselect input when a different node is selected or if existing value changes
  useEffect(() => {
    if (selectedNode) {
      const existingVal = selectedNode.postselect_value;
      setPostSelectInput(existingVal !== null && existingVal !== undefined ? String(existingVal) : "");
      setPostSelectError("");
      setPostSelectSuccess(false);
    }
  }, [selectedNodeId, selectedNode?.postselect_value]);

  if (!graphData?.nodes?.length) return <div style={{ color: "#666", padding: "16px" }}>No graph data</div>;

  return (
    <ReactFlowProvider>
      <div style={{ width: "100%", height: "100%", background: "#1d1f21", borderRadius: "12px", position: "relative" }}>
        <div style={{ position: "absolute", top: 16, right: 16, zIndex: 10, display: "flex", gap: "8px" }}>
          <button onClick={expandAll} style={overlayButtonStyle}>Expand All</button>
          <button onClick={collapseAll} style={overlayButtonStyle}>Collapse All</button>
          <button onClick={() => setFullscreen(true)} style={overlayButtonStyle}>⛶ Fullscreen</button>
        </div>
        <GraphView
          nodes={nodes}
          edges={edges}
          onNodesChangeWrapped={onNodesChangeWrapped}
          onEdgesChangeWrapped={onEdgesChangeWrapped}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          overlayButtonStyle={overlayButtonStyle}
          sidePanelShow={fullscreen}
          selectedNode={selectedNode}
          isDebuggerActive={isDebuggerActive}
          onPostSelectApply={onPostSelectApply}
          postSelectSuccess={postSelectSuccess}
          setSelectedNodeId={setSelectedNodeId}
        />
      </div>
      {fullscreen && (
        <ReactFlowProvider>
          <div style={{ position: "fixed", inset: 5, background: "transparent", zIndex: 9999, display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", background: "#1d1f21", borderBottom: "1px solid #333", borderRadius: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <span style={{ color: "#eee", fontWeight: "bold", fontSize: "14px" }}>Command Tree</span>
                <button onClick={expandAll} style={overlayButtonStyle}>Expand All</button>
                <button onClick={collapseAll} style={overlayButtonStyle}>Collapse All</button>
              </div>
              <button onClick={() => setFullscreen(false)} style={overlayButtonStyle}>✕ Close</button>
            </div>
            <div style={{ flex: 1, position: "relative", background: "#1d1f21", borderRadius: "12px" }}>
              <GraphView
                nodes={nodes}
                edges={edges}
                onNodesChangeWrapped={onNodesChangeWrapped}
                onEdgesChangeWrapped={onEdgesChangeWrapped}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                overlayButtonStyle={overlayButtonStyle}
                sidePanelShow={true}
                selectedNode={selectedNode}
                isDebuggerActive={isDebuggerActive}
                onPostSelectApply={onPostSelectApply}
                postSelectSuccess={postSelectSuccess}
                setSelectedNodeId={setSelectedNodeId}
              />
            </div>
          </div>
        </ReactFlowProvider>
      )}
    </ReactFlowProvider>
  );
}