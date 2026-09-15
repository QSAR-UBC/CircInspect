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
// PropertyList.js

import { memo } from "react";

const HIDDEN_KEYS = ["label", "subtree_circuit_img", "tree_node_name", "children", "node_dimmed", "active_debug", "line_type", "quantum_or_classical", "id", "parent_id", "isCollapsed", "onToggleCollapse", "hasChildren", "is_mid_measure", "mid_measurement_index", "measurement_id", "postselect_value", "visible"];
const KEY_ORDER = ["code_line", "line_number", "parent_function", "condition_context", "arguments", "output"];

export const getSortedEntries = (node) => {
    return Object.entries(node)
        .filter(([k]) => !HIDDEN_KEYS.includes(k))
        .filter(([k, v]) => {
            if (v === null || v === undefined || v === "None") return false;
            if (typeof v === "object" && !Array.isArray(v) && Object.keys(v).length === 0) return false;
            if (Array.isArray(v) && v.length === 0) return false;
            return true;
        })
        .sort(([a], [b]) => {
            const ai = KEY_ORDER.indexOf(a), bi = KEY_ORDER.indexOf(b);
            if (ai === -1 && bi === -1) return 0; if (ai === -1) return 1; if (bi === -1) return -1;
            return ai - bi;
        });
};

const PropertyList = ({ node }) => {
    const entries = getSortedEntries(node);
    return (
        <>
            {entries.map(([k, v]) => (
                <div key={k} style={{ marginBottom: "6px" }}>
                    <span style={{ color: "#888" }}>{k}: </span>
                    {k === "arguments" && v && typeof v === "object" && !Array.isArray(v) ? (
                        <div style={{ paddingLeft: "12px" }}>
                            {Object.entries(v).map(([argKey, argVal]) => (
                                <div key={argKey} style={{ marginBottom: "4px" }}>
                                    <span style={{ color: "#aaa" }}>{argKey}: </span>
                                    <span>{Array.isArray(argVal) ? argVal.join(", ") || "—" : String(argVal ?? "—")}</span>
                                </div>
                            ))}
                        </div>
                    ) : <span>{Array.isArray(v) ? v.join(", ") || "—" : String(v ?? "—")}</span>}
                </div>
            ))}
        </>
    );
};

export default memo(PropertyList);