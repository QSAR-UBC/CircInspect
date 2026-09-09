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

import { memo } from "react";

const Header = () => {
    return (
        <header className="shrink-0 h-16 flex items-center px-6 bg-[#22241d] border-b-2 border-green-700 shadow-md shadow-green-500/30">
            <img
                src="/group-logo-dark-horizontal.png"
                alt="QSAR Labs logo"
                className="h-28 w-64 object-contain mr-4 mt-2" 
            />
            <h1 className="text-5xl font-bold text-white tracking-wide">
                CircInspect
            </h1>
        </header>
    );
};

export default memo(Header);