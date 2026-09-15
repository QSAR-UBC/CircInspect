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

import { useState } from "react";

/**
 * InfoPopup
 *
 * Info button that shows CircInspect usage guidelines in a popup on hover
 * or click.
 */
const InfoPopup = () => {
  const [hovered, setHovered] = useState(false);
  const [clicked, setClicked] = useState(false);
  const showPopup = hovered || clicked;

  return (
    <div
      className="relative flex items-center"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={() => setClicked(true)}
        className="flex items-center justify-center h-10 w-10 rounded bg-green-500 hover:bg-green-700 text-white shadow transition-colors"
        aria-label="Usage rules and constraints"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 5a1.25 1.25 0 1 1 0 2.5A1.25 1.25 0 0 1 12 7Zm1.5 10.5h-3v-1.25h.75v-4h-.75V11h2.25v5.25h.75v1.25Z" />
        </svg>
      </button>

      {showPopup && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-white border border-gray-300 rounded-lg shadow-xl p-4 z-50 text-left">
          <button
            onClick={() => { setClicked(false); setHovered(false); }}
            className="absolute top-2 right-2 text-gray-400 hover:text-gray-700"
            aria-label="Close"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h3 className="font-bold text-sm mb-2 pr-6">CircInspect Usage Guidelines</h3>
          <ul className="list-disc pl-4 space-y-1 text-xs text-gray-800">
            <li>Import PennyLane using the alias <code className="bg-gray-100 px-1 rounded">qp</code></li>
            <li>Define QNodes with the <code className="bg-gray-100 px-1 rounded">@qp.qnode</code> decorator</li>
            <li>Apply transforms to QNodes using decorator syntax (e.g. <code className="bg-gray-100 px-1 rounded">@qp.transforms.cancel_inverses</code>)</li>
            <li>Execute exactly one QNode to visualize and debug it </li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default InfoPopup;
