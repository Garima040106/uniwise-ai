import React, { useMemo } from 'react';
import './CognitiveMeter.css';

/**
 * CognitiveMeter Component
 * Displays cognitive load as a circular progress ring with status indicator
 * 
 * Props:
 *   - load: number (0-1) representing cognitive load
 *   - capacity: number (0-100) representing remaining capacity percentage
 */
const CognitiveMeter = ({ load = 0.5, capacity = 50 }) => {
  // SVG circle dimensions
  const SVG_SIZE = 200;
  const CENTER = SVG_SIZE / 2;
  const RADIUS = 80;
  const STROKE_WIDTH = 8;

  // Determine color based on load level
  const getColor = (loadValue) => {
    if (loadValue < 0.3) return '#43e97b'; // Green - Excellent
    if (loadValue < 0.6) return '#f9a825'; // Yellow - Good
    if (loadValue < 0.8) return '#ff9800'; // Orange - Tired
    return '#ff6584'; // Red - Exhausted
  };

  // Determine status text based on load level
  const getStatus = (loadValue) => {
    if (loadValue < 0.3) return 'Excellent';
    if (loadValue < 0.6) return 'Good';
    if (loadValue < 0.8) return 'Tired';
    return 'Exhausted';
  };

  // Calculate progress arc path
  const calculateArcPath = (percentage) => {
    const angle = (percentage / 100) * 360;
    const radians = (angle * Math.PI) / 180;
    const x = CENTER + RADIUS * Math.cos(radians - Math.PI / 2);
    const y = CENTER + RADIUS * Math.sin(radians - Math.PI / 2);

    const largeArc = angle > 180 ? 1 : 0;

    return `M ${CENTER} ${CENTER - RADIUS} A ${RADIUS} ${RADIUS} 0 ${largeArc} 1 ${x} ${y}`;
  };

  // Clamp values to valid ranges
  const clampedLoad = Math.max(0, Math.min(1, load));
  const clampedCapacity = Math.max(0, Math.min(100, capacity));

  const color = useMemo(() => getColor(clampedLoad), [clampedLoad]);
  const status = useMemo(() => getStatus(clampedLoad), [clampedLoad]);

  // Convert load to display percentage (0-100)
  const loadPercentage = Math.round(clampedLoad * 100);

  return (
    <div className="cognitive-meter-container">
      <div className="meter-wrapper">
        <svg
          width={SVG_SIZE}
          height={SVG_SIZE}
          viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
          className="meter-svg"
        >
          {/* Background circle */}
          <circle
            cx={CENTER}
            cy={CENTER}
            r={RADIUS}
            className="meter-background"
            fill="none"
            stroke="#2a2a4a"
            strokeWidth={STROKE_WIDTH}
          />

          {/* Progress arc */}
          <path
            d={calculateArcPath(loadPercentage)}
            fill="none"
            stroke={color}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            className="meter-progress"
            style={{
              filter: `drop-shadow(0 0 8px ${color}90)`,
            }}
          />

          {/* Center text */}
          <text
            x={CENTER}
            y={CENTER - 10}
            textAnchor="middle"
            dominantBaseline="middle"
            className="meter-percentage"
            fill={color}
          >
            {loadPercentage}%
          </text>

          <text
            x={CENTER}
            y={CENTER + 20}
            textAnchor="middle"
            dominantBaseline="middle"
            className="meter-label"
            fill="#a0a0b0"
          >
            Load
          </text>
        </svg>
      </div>

      {/* Status section */}
      <div className="meter-status">
        <div className="status-indicator" style={{ backgroundColor: color }}></div>
        <div className="status-text">
          <div className="status-title">{status}</div>
          <div className="status-subtext">{clampedCapacity}% capacity</div>
        </div>
      </div>

      {/* Capacity bar */}
      <div className="capacity-bar-wrapper">
        <div className="capacity-bar-background">
          <div
            className="capacity-bar-fill"
            style={{
              width: `${clampedCapacity}%`,
              backgroundColor: color,
            }}
          ></div>
        </div>
      </div>
    </div>
  );
};

export default CognitiveMeter;
