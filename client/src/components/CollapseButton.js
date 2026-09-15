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

import { PlusIcon, MinusIcon } from "./Icons";
import { memo } from "react";

const CollapseButton = ({ data, colors }) => {
    if (!data.hasChildren) return null;
    const bottomOffset = data.line_type === "scf" ? "-38px" : "-15px";
    return (
        <button
            onClick={(e) => { e.stopPropagation(); data.onToggleCollapse(); }}
            style={{
                position: "absolute", bottom: bottomOffset, left: "50%", transform: "translateX(-50%)",
                background: "#1a1a1a", border: `2px solid ${colors.border}`, borderRadius: "50%",
                width: "38px", height: "38px", display: "flex", alignItems: "center", justifyContent: "center",
                color: colors.border, cursor: "pointer", zIndex: 20, padding: 0, boxShadow: "0 2px 6px rgba(0,0,0,0.5)",
            }}
        >
            {data.isCollapsed ? <PlusIcon style={{ width: "64px", height: "64px" }} /> : <MinusIcon style={{ width: "64px", height: "64px" }} />}
        </button>
    );
};

export default memo(CollapseButton);