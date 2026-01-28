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
import Select from "react-select";
import { ModeOptions } from "../constants/ModeOptions";

/**
* ModeDropdown
*
* Dropdown for user to choose between Debugger and Real-Time
*
* @param {method} onSelectChange - method to call when user changes mode on the dropdown menu.
*/
const ModeDropdown = ({ onSelectChange }) => {
  return (
    <Select
    className="text-xs"
      placeholder={`Filter By Category`}
      options={ModeOptions}
      defaultValue={ModeOptions[0]}
      onChange={(selectedOption) => onSelectChange(selectedOption)}
    />
  );
};

export default ModeDropdown;
