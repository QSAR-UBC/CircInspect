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

import React, { useEffect, useRef } from "react";
import {
  ReactFlow,
  Controls,
  ControlButton,
  Background,
  useReactFlow,
} from "@xyflow/react";
import Legend from "./Legend";
import SidePanel from "./SidePanel";

const fitViewParams = {
  duration: 400,
  padding: 0.1
};

const FitViewHandler = ({ nodesLength }) => {
  const { fitView } = useReactFlow();
  const isFirstMount = useRef(true);

  useEffect(() => {
    if (nodesLength > 0) {
      if (isFirstMount.current) {
        fitView(fitViewParams.padding);
        isFirstMount.current = false;
      } else {
        fitView(fitViewParams);
      }
    }
  }, [nodesLength, fitView]);
  return null;
};

const CustomFitViewButton = () => {
  const { fitView } = useReactFlow();
  return (
    <ControlButton onClick={() => fitView(fitViewParams)} title="Fit View">
      <span style={{ fontSize: "24px", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "2px" }}>𖦏</span>
    </ControlButton>
  );
};

export default function GraphView({
  nodes,
  edges,
  onNodesChangeWrapped,
  onEdgesChangeWrapped,
  onNodeClick,
  onPaneClick,
  nodeTypes,
  overlayButtonStyle,
  sidePanelShow,
  selectedNode,
  isDebuggerActive,
  onPostSelectApply,
  postSelectSuccess,
  setSelectedNodeId
}) {
  return (
    <>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChangeWrapped}
        onEdgesChange={onEdgesChangeWrapped}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodesDraggable={false}
        nodesConnectable={false}
        nodesDeletable={false}
        edgesDeletable={false}
        deleteKeyCode={null}
        minZoom={0.1}
        nodeTypes={nodeTypes}
      >
        <Controls showInteractive={false} showFitView={false} style={{ background: "#1e1e1e", border: "1px solid #333", borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.4)", padding: "6px" }} >
          <CustomFitViewButton />
        </Controls>
        <Background color="#333" gap={16} />
        <FitViewHandler nodesLength={nodes.length} />
      </ReactFlow>
      <Legend overlayButtonStyle={overlayButtonStyle} />
      <SidePanel show={sidePanelShow} selectedNode={selectedNode} isDebuggerActive={isDebuggerActive} onPostSelectApply={onPostSelectApply} postSelectSuccess={postSelectSuccess} overlayButtonStyle={overlayButtonStyle} setSelectedNodeId={setSelectedNodeId} />
    </>
  );
}
