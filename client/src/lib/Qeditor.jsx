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

import React, { useState, useRef, useEffect } from "react";
import './Qeditor.css';
import Editor, { useMonaco } from '@monaco-editor/react';

/**
* Qeditor
*
* A wrapper around the Monaco editor that adds breakpoint and highlight support
* through props.
*/
function Qeditor(props) {
	let [value, setValue] = useState([]);
	let [breaks, setBreaks] = useState([]);

	if ((props.breaks !== null) && (props.setbreaks !== null)) {
		breaks = props.breaks;
		setBreaks = props.setbreaks;
	}

	if ((props.value !== null) && (props.setvalue !== null)) {
		value = props.value;
		setValue = props.setvalue;
	}

	const editorRef = useRef(null);
	const decorsRef = useRef(null);
	const highlightRef = useRef(null);
	const monaco = useMonaco();


	useEffect(() => {
		addBreakpointDecors()
	}, [breaks]);

	useEffect(() => {
		addHighlightDecors();
		if (props.focuson && editorRef.current && props.highlightline) {
			editorRef.current.revealLineInCenterIfOutsideViewport(Number(props.highlightline));	
		}
	}, [props.highlightline])	

  /**
  * Tell the Monaco editor to render the breakpoints according to list of breakpoints set by the user.
  */
	function addBreakpointDecors() {
		if (monaco) {
			if (decorsRef.current) decorsRef.current.clear();
			var decorList = breaks.map(b => ({	
					range: new monaco.Range(b, 1, b, 1),
					options: {isWholeLine: true, linesDecorationsClassName: "breakSide"}
				}
			));
			decorsRef.current = editorRef.current.createDecorationsCollection(decorList);
		}
	}

  /**
  * Tell the Monaco editor to render a line highlight if highlightline is set to a positive integer (representing line number).
  */
	function addHighlightDecors() {
		if (monaco) {
			if (highlightRef.current) highlightRef.current.clear();
			if (props.highlightline && props.highlightline >= 0 ) {
			highlightRef.current = editorRef.current.createDecorationsCollection([{
				range: new monaco.Range(Number(props.highlightline), 1, Number(props.highlightline), 1),
				options: {isWholeLine: true, className: "highlightLine"}
			}]);
			}
		}
	}

  /**
  * Setup method that runs before the page is available to user to complete all desired
  * setup actions such as setting callback functions for the editor's user interaction triggers.
  */
	function handleEditorDidMount(editor, monaco) {
		// A function called when user clicks on the editor, sets breakpoints if the specific location on the editor is clicked.
		editor.onMouseDown((e) => {
			if (e.target.type === 3) {
				let ln = e.target.position.lineNumber;
				setBreaks(breaks => (breaks.includes(ln)) ? breaks.filter(b => b !== ln) : [...breaks, ln].sort((a,b)=>a-b));
			}
		})
		// keep the ref to get data from the editor later on
		editorRef.current = editor;
	}

  /**
  * Runs when the code is changed by the user.
  */
	function handleEditorChange(value, event) {
		let max = value.split("\n").length;
		setBreaks(breaks => breaks.filter(b => b <= max));
		addHighlightDecors();
		setValue(value);
		if (props.onChange !== null) props.onChange("code", value);
	}

	return <Editor 
		options={{readOnly: (props.readOnly) ? props.readOnly : false,
							selectOnLineNumbers: false}}
		height={(props.height) ? props.height : "80vh"}
		width={(props.width) ? props.width : "100%"}
		defaultLanguage={"python"}
		language={(props.language) ? props.language : "python"}
		defaultValue={(props.defaultValue) ? props.defaultValue : "# Hello world"}
		theme={(props.theme) ? props.theme : "vs-dark"}
		onMount={handleEditorDidMount}
		onChange={handleEditorChange}
		/>;
}

export default Qeditor;
