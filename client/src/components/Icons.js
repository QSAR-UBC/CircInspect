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
* SVGs for the icons being used throughout the application.
*/

export const ContinueIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M2.5 2H4V2.24001L4 14L2.5 14L2.5 2ZM6 2.18094V14L15 8.06218L6 2.18094ZM12.3148 8.06218L7.50023 5L7.50023 11.1809L12.3148 8.06218Z" fill="#000"/>
</svg>
}

export const ReverseContinueIcon = () => {
return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M13.5002 2H12.0002V2.24001L12.0002 14L13.5002 14L13.5002 2ZM10.0002 2.18094V14L1.00024 8.06218L10.0002 2.18094ZM3.68547 8.06218L8.50001 5L8.50001 11.1809L3.68547 8.06218Z" fill="#000"/>
</svg>
}

export const StepOverIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M14.25 5.75V1.75H12.75V4.2916C11.605 2.93303 9.83899 2.08334 7.90914 2.08334C4.73316 2.08334 1.98941 4.39036 1.75072 7.48075L1.72992 7.75H3.231L3.25287 7.5241C3.46541 5.32932 5.45509 3.58334 7.90914 3.58334C9.6452 3.58334 11.1528 4.45925 11.9587 5.75H9.12986V7.25H13.292L14.2535 6.27493V5.75H14.25ZM7.99997 14C9.10454 14 9.99997 13.1046 9.99997 12C9.99997 10.8954 9.10454 10 7.99997 10C6.8954 10 5.99997 10.8954 5.99997 12C5.99997 13.1046 6.8954 14 7.99997 14Z" fill="#000"/>
</svg>
}

export const StepIntoIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M7.99998 9.532H8.54198L12.447 5.627L11.386 4.567L8.74898 7.177L8.74898 1H7.99998H7.25098L7.25098 7.177L4.61398 4.567L3.55298 5.627L7.45798 9.532H7.99998ZM9.95598 13.013C9.95598 14.1176 9.06055 15.013 7.95598 15.013C6.85141 15.013 5.95598 14.1176 5.95598 13.013C5.95598 11.9084 6.85141 11.013 7.95598 11.013C9.06055 11.013 9.95598 11.9084 9.95598 13.013Z" fill="#000"/>
</svg>
}

export const StepOutIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M7.99998 1H7.45798L3.55298 4.905L4.61398 5.965L7.25098 3.355V9.532H7.99998H8.74898V3.355L11.386 5.965L12.447 4.905L8.54198 1H7.99998ZM9.95598 13.013C9.95598 14.1176 9.06055 15.013 7.95598 15.013C6.85141 15.013 5.95598 14.1176 5.95598 13.013C5.95598 11.9084 6.85141 11.013 7.95598 11.013C9.06055 11.013 9.95598 11.9084 9.95598 13.013Z" fill="#000"/>
</svg>
}

export const RestartIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path fillRule="evenodd" clipRule="evenodd" d="M12.75 7.99988C12.75 10.4852 10.7353 12.4999 8.24999 12.4999C6.41795 12.4999 4.84162 11.4051 4.13953 9.83404L2.74882 10.3989C3.67446 12.5185 5.78923 13.9999 8.24999 13.9999C11.5637 13.9999 14.25 11.3136 14.25 7.99988C14.25 4.68617 11.5637 1.99988 8.24999 1.99988C6.3169 1.99988 4.59732 2.91406 3.5 4.33367V2.49988H2V6.49988L2.75 7.24988H6.25V5.74988H4.35201C5.13008 4.40482 6.58436 3.49988 8.24999 3.49988C10.7353 3.49988 12.75 5.5146 12.75 7.99988Z" fill="#000"/>
</svg>
}

export const LoadingIcon = () => {
	return <svg aria-hidden="true" className="w-8 h-8 text-gray-200 animate-spin dark:text-gray-600 fill-blue-600" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>
        <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>
    </svg>
}

export const StopIcon = () => {
	return <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4.5 2.99988L6 2.99988V12.9999H4.5V2.99988ZM11.5 2.99988V12.9999H10V2.99988L11.5 2.99988Z" fill="#000"/>
</svg>
}

export const PlusIcon = () => {
	return <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-3 h-3"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>
}

export const MinusIcon = () => {
	return <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-3 h-3"><path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" /></svg>
}
