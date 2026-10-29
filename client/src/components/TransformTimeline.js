import React, { useRef, useState, useEffect } from "react";
import "./TransformTimeline.css";

const TransformTimeline = ({ presentTransforms, activeTransforms, onTransformSelect, isDebuggerActive }) => {
    const trackRef = useRef(null);
    const lastUpdateRef = useRef(0);
    const timeoutRef = useRef(null);

    // Derived level from props
    const propLevel = activeTransforms === null
        ? (presentTransforms?.length || 0)
        : activeTransforms.length;

    // Local level for smooth scrubbing without overwhelming the parent/graph
    const [localLevel, setLocalLevel] = useState(propLevel);

    useEffect(() => {
        setLocalLevel(propLevel);
    }, [propLevel]);

    if (!presentTransforms || presentTransforms.length === 0) return null;

    const totalSteps = presentTransforms.length;
    const percentage = (localLevel / totalSteps) * 100;

    const handleLevelChange = (newLevel) => {
        if (isDebuggerActive) return;
        const level = Math.max(0, Math.min(totalSteps, newLevel));
        if (level === localLevel) return;

        setLocalLevel(level);

        const now = Date.now();
        const timeSinceLastUpdate = now - lastUpdateRef.current;

        if (timeoutRef.current) clearTimeout(timeoutRef.current);

        const performUpdate = () => {
            onTransformSelect(presentTransforms.slice(0, level));
            lastUpdateRef.current = Date.now();
        };

        if (timeSinceLastUpdate > 50) {
            performUpdate();
        } else {
            timeoutRef.current = setTimeout(performUpdate, 50 - timeSinceLastUpdate);
        }
    };

    const handleInteraction = (e) => {
        if (isDebuggerActive || !trackRef.current) return;
        const rect = trackRef.current.getBoundingClientRect();
        const y = e.clientY - rect.top;
        const stepHeight = rect.height / totalSteps;
        const newLevel = Math.round(y / stepHeight);
        handleLevelChange(newLevel);
    };

    return (
        <div
            className={`timelineContainer ${isDebuggerActive ? 'debuggerActive' : ''}`}
            style={isDebuggerActive ? { pointerEvents: 'none', opacity: 0.8 } : {}}
        >
            <div className="timelineHeader">
                <div className="currentLevelBadge" style={isDebuggerActive ? { borderColor: '#555', color: '#888' } : {}}>
                    {isDebuggerActive && <span style={{ marginRight: '4px', fontSize: '12px' }}>🔒︎</span>}
                    {localLevel}
                </div>
            </div>

            <div
                className="trackWrapper"
                ref={trackRef}
                onClick={handleInteraction}
            >
                <div className="mainTrack"></div>
                <div className="activeTrack" style={{ height: `${percentage}%`, width: '2px' }}></div>

                <div className="stepContainer">
                    <div
                        className={`stepDot ${localLevel === 0 ? "active" : "passed"}`}
                        style={{ top: "0%" }}
                    >
                        <div className="stepLabel">Base</div>
                    </div>

                    {presentTransforms.map((transform, index) => {
                        const step = index + 1;
                        const pos = (step / totalSteps) * 100;
                        const isActive = localLevel === step;
                        const isPassed = localLevel > step;

                        return (
                            <div
                                key={step}
                                className={`stepDot ${isActive ? "active" : ""} ${isPassed ? "passed" : ""}`}
                                style={{ top: `${pos}%` }}
                            >
                                <div className="stepLabel">{transform[0]}</div>
                            </div>
                        );
                    })}
                </div>

                <div
                    className="thumb"
                    style={{ top: `${percentage}%`, left: '50%' }}
                    onMouseDown={(e) => {
                        if (isDebuggerActive) return;
                        const onMouseMove = (moveEvent) => {
                            handleInteraction(moveEvent);
                        };
                        const onMouseUp = () => {
                            document.removeEventListener("mousemove", onMouseMove);
                            document.removeEventListener("mouseup", onMouseUp);
                        };
                        document.addEventListener("mousemove", onMouseMove);
                        document.addEventListener("mouseup", onMouseUp);
                    }}
                >
                    <div className="stepLabel">
                        {localLevel === 0 ? "Base" : presentTransforms[localLevel - 1]?.[0] || ""}
                    </div>
                    <div className="thumbInner"></div>
                </div>
            </div>
        </div>
    );
};

export default TransformTimeline;