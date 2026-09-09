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

/**
* OutputWindow
*
* Render circuit visualizations in a box with title.
*
* @param {string} imgsrc - image source for the circuit visualization.
* @param {boolean} isError - true if an error occured.
*/
const OutputWindow = ({ imgsrc, isError }) => {
  return (
    <div className="flex flex-col h-full">
      <div className={"bg-white h-full border-2 rounded-md overflow-hidden " + (isError ? "border-red-700" : "border-black")}>
        <img src={imgsrc} className="w-full h-full object-contain" alt={"Quantum Circuit Visualization"} />
      </div>
    </div>
  );
};

export default OutputWindow;
