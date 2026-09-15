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

import React from "react";
import { useState } from "react";

const Legend = ({ overlayButtonStyle }) => {
    const [collapsed, setCollapsed] = useState(false);
    const items = [
        { label: "Function Call", shape: "circle", border: "#f5ec50", bg: "linear-gradient(135deg, #6b6200, #2a2600)" },
        { label: "Control Flow", shape: "diamond", border: "#0099ee", bg: "linear-gradient(135deg, #003a6e, #001428)" },
        { label: "Quantum Op", shape: "rounded", border: "#00cc94", bg: "linear-gradient(135deg, #004d38, #001a12)" },
        { label: "Mid Measure", shape: "rounded", border: "#e066ff", bg: "linear-gradient(135deg, #4a1a6b, #1a0828)" },
        { label: "Active Debug", shape: "hexagon", border: "#ff4a4a", bg: "linear-gradient(135deg, #5f1e1e, #280a0a)" },
    ];

    const getShapeStyle = (shape, border, bg) => {
        const base = { width: "20px", height: "20px", background: bg, border: `2px solid ${border}`, flexShrink: 0, boxSizing: "border-box" };
        if (shape === "circle") return { ...base, borderRadius: "50%" };
        if (shape === "diamond") return { ...base, borderRadius: "2px", transform: "rotate(45deg)", width: "16px", height: "16px" };
        if (shape === "hexagon") return { ...base, border: "none", background: "none", width: "20px", height: "20px", position: "relative" };
        return { ...base, borderRadius: "5px" };
    };

    return (
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 10, display: "flex", flexDirection: "column", gap: collapsed ? 0 : "7px" }}>
            <div onClick={() => setCollapsed((c) => !c)} style={{ ...overlayButtonStyle, display: "flex", alignItems: "center", gap: "18px", marginBottom: collapsed ? 0 : "2px" }}>
                <span>Legend</span>
                <span style={{ lineHeight: 1, display: "inline-block", transition: "transform 0.2s ease", transform: collapsed ? "rotate(180deg)" : "rotate(0deg)" }}>▲</span>
            </div>
            {!collapsed && (
                <div style={{ background: "#1a1a1a", border: "1px solid #444", borderRadius: "10px", padding: "8px 14px", fontSize: "11px", color: "#ccc", display: "flex", flexDirection: "column", gap: "7px" }}>
                    {items.map(({ label, shape, border, bg }) => (
                        <div key={label} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                            <div style={{ width: "22px", height: "22px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                                {shape === "hexagon" ? (
                                    <svg width="22" height="22" viewBox="0 0 22 22" style={{ flexShrink: 0 }}>
                                        <polygon points="11,1 20,6.2 20,15.8 11,21 2,15.8 2,6.2" fill="url(#hexgrad)" stroke="#ff4a4a" strokeWidth="1.5" />
                                        <defs><linearGradient id="hexgrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#5f1e1e" /><stop offset="100%" stopColor="#280a0a" /></linearGradient></defs>
                                    </svg>
                                ) : <div style={getShapeStyle(shape, border, bg)} />}
                            </div>
                            <span style={{ paddingTop: "1px" }}>{label}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Legend;