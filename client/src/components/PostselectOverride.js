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

import { memo, useState } from "react";

const PostselectOverride = ({ selectedNode, onPostSelectApply }) => {
    const [hoveredVal, setHoveredVal] = useState(null);
    const [resetHovered, setResetHovered] = useState(false);
    const targetId = selectedNode.measurement_id || selectedNode.id;

    return (
        <div style={{ marginTop: "12px", borderTop: "1px solid #444", paddingTop: "12px" }}>
            <div style={{ color: "#e066ff", fontWeight: "bold", fontSize: "12px", marginBottom: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Postselect Override
            </div>

            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                {[0, 1].map((val) => {
                    const isSelected = selectedNode.postselect_value === val;
                    const isHovered = hoveredVal === val;
                    return (
                        <button
                            key={val}
                            onClick={() => onPostSelectApply?.(targetId, val)}
                            onMouseEnter={() => setHoveredVal(val)}
                            onMouseLeave={() => setHoveredVal(null)}
                            style={{
                                flex: 1,
                                background: isSelected ? "linear-gradient(135deg, #4a1a6b, #6b21a8)" : isHovered ? "#240a35" : "#1a1a1a",
                                border: `1px solid ${isSelected ? "#e066ff" : isHovered ? "#8b3da3" : "#444"}`,
                                borderRadius: "6px",
                                padding: "8px 0",
                                color: isSelected ? "#fff" : "#888",
                                fontSize: "13px",
                                fontFamily: "'Quicksand', sans-serif",
                                fontWeight: "bold",
                                cursor: "pointer",
                                transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                                boxShadow: isSelected ? "0 0 12px rgba(224, 102, 255, 0.35)" : "none"
                            }}
                        >
                            {val}
                        </button>
                    );
                })}
                <button
                    onClick={() => onPostSelectApply?.(targetId, null)}
                    onMouseEnter={() => setResetHovered(true)}
                    onMouseLeave={() => setResetHovered(false)}
                    style={{
                        flex: 1.2,
                        background: resetHovered ? "#240a35" : "#1a1a1a",
                        border: `1px solid ${resetHovered ? "#e066ff" : "#444"}`,
                        borderRadius: "6px",
                        padding: "8px 0",
                        color: resetHovered ? "#fff" : "#999",
                        fontSize: "11px",
                        fontFamily: "'Quicksand', sans-serif",
                        fontWeight: "600",
                        cursor: "pointer",
                        transition: "all 0.2s ease",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        boxShadow: resetHovered ? "0 0 10px rgba(224, 102, 255, 0.25)" : "none"
                    }}
                >
                    Reset
                </button>
            </div>

            <div style={{ fontSize: "11px", color: "#666", marginTop: "10px", lineHeight: "1.4" }}>
                Select an outcome to force it during execution.
            </div>
        </div>
    );
};

export default memo(PostselectOverride);