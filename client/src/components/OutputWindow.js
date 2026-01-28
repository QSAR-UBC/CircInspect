// Copyright 2025 UBC Quantum Software and Algorithms Research Lab

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
    <>
      <h1 className="font-bold text-xl bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700 mb-2">
        Quantum Circuit
      </h1>
      <div  style={{width: "auto"}} className={"bg-white h-96 border-2 resize-y rounded-md text-white font-normal text-sm overflow-y-auto " + (isError ? "border-red-700" : "border-black")}> 
        <img src={imgsrc} style={{maxWidth: "none", height:"100%"}} alt={"Quantum Circuit Visualization"}/>
      </div>
    </>
  );
};

export default OutputWindow;
