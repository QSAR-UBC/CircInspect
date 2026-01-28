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

import React, { useState, useEffect } from "react";
import axios from "axios";
import "./App.css";
import Landing from "./components/Landing";
import Login from "./components/Login";

function App() {
  const noAuth = true

	const [auth, setAuth] = useState(false);
	const [authToken, setAuthToken] = useState(null);
	const [failedAuth, setFailedAuth] = useState(false);
	const [userEmail, setUserEmail] = useState("");
	const [pennylaneVersion, setPennylaneVersion] = useState("unknown");

	useEffect(() => {
    if (noAuth) {
      setAuthToken("NOAUTH")
      setUserEmail("NOAUTH")
			setPennylaneVersion("0.41.0");
			setAuth(true);
      return;
    }

		// check if a new token is given by query string
		let token = window.location.search.substring(1)
		// if no new token, check if cookies include an old token
		if (token === "") {
			token = document.cookie.split("; ")
				.find((row) => row.startsWith("token="))
				?.split("=")[1];
			if (token == undefined || token == null) token = "";
		}
		if (token !== "") {	
			axios.post('/auth/verify',
				{
					"token": token
				}, {headers: {'Content-Type': 'application/json'}}
			).then(res => {
				if (res.status === 200) {
					setUserEmail(res.data.email);
					setPennylaneVersion(res.data.pennylane);
					setAuth(true);
					setAuthToken(token);
					document.cookie = ("token=" + token);
				} else {
					setFailedAuth(true);
					document.cookie = "token=";
				}
			}).catch(err => {
				setFailedAuth(true);
				document.cookie = "token=";
			});
		}
	}, []);	

  if (noAuth) {
    return <Landing authToken={authToken} userEmail={userEmail} pennylaneVersion={pennylaneVersion}/>
  }


	return (auth ? <Landing authToken={authToken} userEmail={userEmail} pennylaneVersion={pennylaneVersion}/> : <Login failed={failedAuth}/>);
}

export default App;
