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

import React, { useState } from "react";
import axios from "axios";
import Rodal from "rodal";
import 'rodal/lib/rodal.css';

/**
* ReportBugForm
*
* A survey form for users to report bugs without leaving the application.
*
* @param {string} authToken - token associated with user for auth purposes, users cannot send responses without valid tokens unless auth is disabled.
* @param {string} userEmail - user's email address if auth is enabled.
* @param {string} sessionID - generated session ID for the current user session.
*/
const ReportBugForm = ({authToken, userEmail, sessionID}) => {
	const [showForm, setShowForm] = useState(false);
	const [success, setSuccess] = useState(false);
	const [description, setDescription] = useState("");
	const [descError, setDescError] = useState(false);

  /**
  * Send the response to the backend if the report is non-empty.
  */
	const submit = () => {
		if (description.replace(/\s/g, '').length === 0) {
			setDescError(true);
		} else {
			axios.post('/bugreport',
				{
					"token": authToken,
					"session_id": sessionID,
					"timestamp": new Date().getTime(),
					"user_email": userEmail,
					"description": description
				}, {headers: {'Content-Type': 'application/json'}}
			)
			setSuccess(true);
			setDescError(false);
		}
	}

  /**
  * Clear the form and exit.
  */
	const exit = () => {
		setShowForm(false);
		setSuccess(false);
		setDescError(false);
		setDescription("");
	}

	return <div className="self-end">
		<button className="bg-pink-500 hover:bg-pink-700 text-white font-bold py-2.5 px-8 text-xs rounded border border-pink-500 transition-colors duration-150" onClick={() => setShowForm(true)}>Report Bug</button>
		<Rodal customStyles={{overflow:"auto", padding:"10px", cursor:"default"}}
					 visible={showForm}
					 onClose={exit}
					 height={600}
					 width={560}>
			<div className="w-full grid justify-items-center">
				<h1 className="font-bold text-xl mx-4 mt-2">Report a Bug</h1>
			</div>
			{//<hr className={"mx-4 " + (success ? "border-green-600":"border-pink-500")}/>
			}
			<p className="mt-2 mx-4"><b className="font-bold">User:</b> {userEmail}</p>
			<p className=" mx-4"><b className="font-bold">Session ID:</b> {sessionID}</p>
		<textarea value={description} onChange={e => {setDescription(e.target.value); setDescError(false)}} className={"resize-none border rounded mt-2 mx-4 p-1 "+(success ? "border-green-600":"border-gray-200")} rows={19} cols={60} placeholder="Please provide description..." readOnly={success}/>
			{success ?
				<button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={exit}>Successfully Submitted!</button>
			:
				<button className="bg-pink-500 hover:bg-pink-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={submit}>Submit</button>
			}
			{descError ? <p className="font-bold text-red-700 mx-4">Not submitted. Please provide description before submitting a report.</p>: <></>}
		</Rodal>
	</div>
}

export default ReportBugForm;
