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

import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";
import Landing from "./components/Landing";


function App() {
	const [pennylaneVersion, setPennylaneVersion] = useState("unknown");

	useEffect(() => {
		axios.get("/library_version").then(res => {
			setPennylaneVersion(res.data.pennylane);
		});
	}, []);

	return <Landing pennylaneVersion={pennylaneVersion} />;
}

export default App;
