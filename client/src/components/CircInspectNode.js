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

import { Handle, Position } from "@xyflow/react";
import { useState, memo } from "react";
import CollapseButton from "./CollapseButton";
import MeasurementBadge from "./MeasurementBadge";
import "./CircInspectNode.css";

const NODE_STYLES = {
    active_debug: {
        normal: { border: "#ff4a4a", bg: "linear-gradient(135deg, #5f1e1e, #280a0a)", shadow: "255, 74, 74" },
    },
    mid_measure: {
        normal: { border: "#e066ff", bg: "linear-gradient(135deg, #4a1a6b, #1a0828)", shadow: "180, 80, 220" },
        dimmed: { border: "#5a2080", bg: "linear-gradient(135deg, #1a0828, #0a0410)", shadow: "90, 40, 110" },
    },
    call: {
        normal: { border: "#f5ec50", bg: "linear-gradient(135deg, #6b6200, #2a2600)", shadow: "240, 228, 66" },
        dimmed: { border: "#4a4400", bg: "linear-gradient(135deg, #1a1800, #0a0900)", shadow: "90, 85, 0" },
    },
    scf: {
        normal: { border: "#0099ee", bg: "linear-gradient(135deg, #003a6e, #001428)", shadow: "0, 114, 178" },
        dimmed: { border: "#00365a", bg: "linear-gradient(135deg, #001422, #00080f)", shadow: "0, 54, 90" },
    },
    quantum: {
        normal: { border: "#00cc94", bg: "linear-gradient(135deg, #004d38, #001a12)", shadow: "0, 158, 115" },
        dimmed: { border: "#004a35", bg: "linear-gradient(135deg, #001a12, #000a07)", shadow: "0, 74, 53" },
    },
    default: {
        normal: { border: "#666", bg: "linear-gradient(135deg, #2a2a2a, #111)", shadow: "150, 150, 150" },
        dimmed: { border: "#333", bg: "linear-gradient(135deg, #111, #060606)", shadow: "60, 60, 60" },
    },
};

const getNodeColors = (data) => {
    let type = "default";

    if (data.active_debug === true && data.line_type !== "transform") type = "active_debug";
    else if (data.is_mid_measure) type = "mid_measure";
    else if (data.line_type === "call" || data.line_type === "transform") type = "call";
    else if (data.line_type === "scf") type = "scf";
    else if (data.quantum_or_classical === "quantum") type = "quantum";

    const state = data.node_dimmed ? "dimmed" : "normal";
    return NODE_STYLES[type][state] || NODE_STYLES[type].normal;
};

const getShapeStyles = (data, active) => {
    if (data.line_type === "call" || data.line_type === "transform") return { borderRadius: "50%", width: "120px", height: "120px" };
    if (data.line_type === "scf") return { borderRadius: "8px", transform: active ? "rotate(45deg) scale(1.08)" : "rotate(45deg) scale(1)", width: "100px", height: "100px" };
    return { borderRadius: "12px", width: "100px", height: "100px" };
};

const CircInspectNode = ({ data, selected }) => {
    const [hovered, setHovered] = useState(false);
    const colors = getNodeColors(data);
    const active = selected || hovered;
    const label = data.label || "";
    const fontSize = label.length > 8 ? `${Math.max(10, 180 / label.length)}px` : "23px";
    const fontColour = data.node_dimmed && !data.active_debug ? "#555555" : "#fff";

    if (data.active_debug && data.line_type !== "transform") {
        return (
            <>
                <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
                <div className="circ-debug-wrapper">
                    <div
                        className={`circ-debug-shape ${active ? "active" : ""}`}
                        title={label}
                        onMouseEnter={() => setHovered(true)}
                        onMouseLeave={() => setHovered(false)}
                    >
                        <div className="circ-debug-shape-bg" />
                        <div className="circ-debug-shape-inner" />
                        <div className={`circ-debug-label-wrapper ${active ? "active" : ""}`}>
                            <span className="circ-debug-label" style={{ fontSize }}>{label}</span>
                        </div>
                    </div>
                    <CollapseButton data={data} colors={colors} />
                </div>
                <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
            </>
        );
    }

    const shapeStyles = getShapeStyles(data, active);

    return (
        <>
            <Handle type="target" position={Position.Top} style={{ top: data.line_type === "scf" ? "-21px" : "0px", opacity: 0 }} />
            <div className="circ-node-wrapper" style={{ width: shapeStyles.width, height: shapeStyles.height }}>
                <MeasurementBadge data={data} />
                <div
                    className="circ-node-shape"
                    title={data.output ? `${label}\noutput: ${data.output}` : label}
                    onMouseEnter={() => setHovered(true)}
                    onMouseLeave={() => setHovered(false)}
                    style={{
                        fontSize,
                        border: `3px solid ${colors.border}`,
                        color: fontColour,
                        background: colors.bg,
                        boxShadow: active ? `0 0 20px 4px rgba(${colors.shadow}, 0.85)` : `0 0 12px rgba(${colors.shadow}, 0.4)`,
                        transform: shapeStyles.transform || (active ? "scale(1.08)" : "scale(1)"),
                        ...shapeStyles,
                    }}
                >
                    <div className="circ-node-label-container" style={{ overflow: data.line_type === "scf" ? "visible" : "hidden" }}>
                        <span className={`circ-node-label ${data.line_type === "scf" ? "scf" : ""}`}>{label}</span>
                    </div>
                </div>
                <CollapseButton data={data} colors={colors} />
            </div>
            <Handle type="source" position={Position.Bottom} style={{ bottom: data.line_type === "scf" ? "-21px" : "0px", opacity: 0 }} />
        </>
    );
};

export default memo(CircInspectNode);