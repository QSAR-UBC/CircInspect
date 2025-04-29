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

import React, { useState } from "react"
import axios from "axios";
import Rodal from "rodal";
import 'rodal/lib/rodal.css';

/**
* Login
*
* Renders a login / sign up page for users to provide their
* email addresses. The email addresses are sent to backend
* which sends a custom login link to the email address.
*
* Props:
* @param {boolean} failed - true if the user is sent to this page
* after their login attempt failed due to expired custom link / token.
*/
const Login = ({failed}) => {
	const [email, setEmail] = useState("")
	const [emailSent, setEmailSent] = useState(false)
	const [emailIncorrect, setEmailIncorrect] = useState(false)
	const [showDomains, setShowDomains] = useState(false);

  /**
  * Send a REST post request to the backend with user email
  * if the user accepted the data collection policy. If user
  * rejected, sendReject function is used to send the request. 
  */
	const sendAccept = () => {
		axios.post('/auth/send', 
			{
				"email": email,
        "policy_accepted": true
			}, {headers: {'Content-Type': 'application/json'}}
		).then(() => {
			setEmailSent(true)
			setEmailIncorrect(false)
		}).catch((e) => {
			if (e.response.status === 401) {
				setEmailSent(false)
				setEmailIncorrect(true)
			}
		})
	}

  /**
  * Send a post request with the user's email and the info
  * that the user rejected the data collection policy.
  */
	const sendReject = () => {
		axios.post('/auth/send', 
			{
				"email": email,
        "policy_accepted": false
			}, {headers: {'Content-Type': 'application/json'}}
		).then(() => {
			setEmailSent(true)
			setEmailIncorrect(false)
		}).catch((e) => {
			if (e.response.status === 401) {
				setEmailSent(false)
				setEmailIncorrect(true)
			}
		})
	}

  // If there is an issue, render an error card on top of the login card.
	let errorCard = <></>	
	if (emailSent) {
		errorCard = <div className="text-center self-center place-content-center content-center w-full bg-green-200 rounded overflow-hidden shadow-lg">	
		<p className="m-3 text-xl">Please check your email for your personal login link!</p>
			</div>
	} else if (emailIncorrect) {
		errorCard = <div className="text-center self-center place-content-center content-center w-full bg-white rounded overflow-hidden shadow-lg">	
		<p className="m-3 text-xl text-red-700 font-medium">Please enter an email address from an approved domain.</p>
			</div>
	} else if (failed) {
		errorCard = <div className="text-center self-center place-content-center content-center w-full bg-white rounded overflow-hidden shadow-lg">	
		<p className="m-3 text-xl text-red-700 font-medium">Your login token has expired or is incorrect. Please enter your email to get a new login link.</p>
			</div>
	}

  // Render input area for user to send their email address
  let loginCard = <>
    <p className="mt-3 text-xl">Please enter an academic email address from an <button className="text-pink-600 hover:text-amber-600" onClick={() => setShowDomains(true)}>approved domain</button>.<br/>We will send you an email with a login link.</p>
		<div className="mt-4">
		<input className="bg-gray-200 appearance-none border-2 border-gray-500 rounded w-1/2 py-2 px-4 text-gray-800 leading-tight focus:outline-none focus:bg-white focus:border-red-500" placeholder="Your email address" value={email} onChange={e => {setEmail(e.target.value.replace(/\s/g, ''))}} onKeyDown={(e) => {if (e.key === "Enter"){sendAccept()}}}/>
		<button className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={sendAccept}>Send</button>
		</div>
  </>

  // If you have a privacy policy for user to accept before login, render this. CrcInspect currently renders a data collection and privacy policy
  // card in Landing.js
  let policyCard = <>
    <p className="mt-3 mx-8 text-xl text-left">Do you accept the privacy policy?</p>
		<div className="mt-4">
		<button className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={sendAccept}>I accept</button>
		<button className="bg-purple-500 hover:bg-purple-700 text-white font-bold py-2 px-8 rounded ml-4" onClick={sendReject}>I reject</button>
		</div>
  </>

	return <div className=" flex place-content-center content-center h-screen w-screen bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500">
		<div className="text-center self-center place-content-center content-center w-9/12 h-auto">
		{errorCard}
		<div className="mt-6 text-center self-center place-content-center content-center w-full h-full bg-white rounded overflow-hidden shadow-lg">
		<h1 className="mt-16 text-6xl font-bold">Welcome to CircInspect!</h1>

    {loginCard} 


		 <img className="justify-self-center w-40 mx-auto my-16" src="/logo.png" alt="Logo"/>
		</div>
		</div>
			<Rodal customStyles={{overflow:"auto", padding:"10px", cursor:"default"}}
					 visible={showDomains}
					 onClose={() => setShowDomains(false)}
					 height={180}
					 width={400}>
							<h1 className="font-bold text-xl mx-4 my-2">Approved Domains</h1>
							<p className="mt-2 mx-4">All subdomains of <b className="font-bold">ubc.ca</b></p>
							<div className="h-8"></div>
							<p className="mx-4">Please let us know at <b className="font-bold">qsar@ece.ubc.ca</b> if you are interested in using CircInspect in your organisation!</p>
			</Rodal>
	</div>
}

export default Login;
