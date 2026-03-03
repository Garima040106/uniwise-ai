import React, { useState, useEffect } from 'react';
import './BreakMode.css';

/**
 * BreakMode Component
 * Enforces break time when cognitive load is too high
 * 
 * Props:
 *   - suggestions: array of string suggestions for break activities
 *   - onBreakComplete: callback when timer finishes
 */
const BreakMode = ({ suggestions = [], onBreakComplete = () => {} }) => {
  const [isActive, setIsActive] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [breakDuration, setBreakDuration] = useState(0);
  const [audioReady, setAudioReady] = useState(false);

  // Icon mapping for suggestions
  const suggestionIcons = {
    walk: '🚶',
    snack: '🍎',
    water: '💧',
    stretch: '🤸',
    exercise: '💪',
    outdoors: '🌳',
    screens: '📵',
    meditation: '🧘',
    deep: '🫁',
    break: '⏸️',
    default: '✨',
  };

  const getIconForSuggestion = (suggestion) => {
    const lowerSuggestion = suggestion.toLowerCase();
    for (const [key, icon] of Object.entries(suggestionIcons)) {
      if (lowerSuggestion.includes(key)) {
        return icon;
      }
    }
    return suggestionIcons.default;
  };

  // Create and prepare audio context for bell sound
  useEffect(() => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    setAudioReady(audioContext.state !== 'suspended');
  }, []);

  // Timer interval
  useEffect(() => {
    let interval;
    if (isActive && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            setIsActive(false);
            playTimerEndSound();
            onBreakComplete();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isActive, timeRemaining, onBreakComplete]);

  // Play a pleasing bell sound when timer ends
  const playTimerEndSound = () => {
    try {
      if (!audioReady) return;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const now = audioContext.currentTime;

      // Create a pleasant bell-like sound using multiple oscillators
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();

      oscillator.connect(gain);
      gain.connect(audioContext.destination);

      // Bell-like frequency
      oscillator.frequency.setValueAtTime(880, now); // A5 note
      oscillator.frequency.exponentialRampToValueAtTime(440, now + 0.5);

      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);

      oscillator.start(now);
      oscillator.stop(now + 0.5);
    } catch (err) {
      console.warn('Could not play timer sound:', err);
    }
  };

  const startTimer = (minutes) => {
    setBreakDuration(minutes);
    setTimeRemaining(minutes * 60);
    setIsActive(true);
  };

  const pauseTimer = () => {
    setIsActive(!isActive);
  };

  const cancelTimer = () => {
    setIsActive(false);
    setTimeRemaining(0);
    setBreakDuration(0);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // If timer is active, show full-screen break mode
  if (isActive && timeRemaining > 0) {
    return (
      <div className="break-mode-overlay">
        <div className="break-mode-container">
          <div className="break-timer-display">
            <div className="break-timer-icon">☕</div>
            <div className="break-timer-text">
              <p className="break-timer-label">Time to relax</p>
              <p className="break-timer-countdown">{formatTime(timeRemaining)}</p>
            </div>
          </div>

          <div className="break-timer-instructions">
            <h3>Take a {breakDuration}-minute break</h3>
            <p>Step away from your screen and recharge!</p>
            {suggestions.length > 0 && (
              <ul className="break-suggestions-mini">
                {suggestions.slice(0, 3).map((suggestion, idx) => (
                  <li key={idx}>
                    <span className="suggestion-icon">{getIconForSuggestion(suggestion)}</span>
                    {suggestion}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="break-timer-controls">
            <button
              className="break-button break-button-pause"
              onClick={pauseTimer}
            >
              {isActive ? '⏸️ Pause' : '▶️ Resume'}
            </button>
            <button
              className="break-button break-button-cancel"
              onClick={cancelTimer}
            >
              ✕ Skip Break
            </button>
          </div>

          <div className="break-content-blocker">
            <div className="blocker-message">
              <p className="blocker-icon">🚫</p>
              <p className="blocker-text">Study features are locked during your break</p>
              <p className="blocker-subtext">We're giving your brain a rest!</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show break banner when break is needed but not active
  return (
    <div className="break-mode-banner">
      <div className="break-banner-header">
        <h3 className="break-banner-title">⚠️ Break Required</h3>
        <p className="break-banner-subtitle">
          Your brain is running low on cognitive capacity (&lt;20%). The best thing you can do right now is take a break!
        </p>
      </div>

      {suggestions.length > 0 && (
        <div className="break-suggestions">
          <h4>Suggested activities:</h4>
          <ul className="suggestions-list">
            {suggestions.map((suggestion, idx) => (
              <li key={idx} className="suggestion-item">
                <span className="suggestion-icon">{getIconForSuggestion(suggestion)}</span>
                <span className="suggestion-text">{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="break-timer-buttons">
        <button
          className="break-button break-button-5"
          onClick={() => startTimer(5)}
        >
          <span className="button-duration">⏱️ 5 Min</span>
          <span className="button-label">Quick break</span>
        </button>
        <button
          className="break-button break-button-10"
          onClick={() => startTimer(10)}
        >
          <span className="button-duration">⏱️ 10 Min</span>
          <span className="button-label">Standard break</span>
        </button>
        <button
          className="break-button break-button-20"
          onClick={() => startTimer(20)}
        >
          <span className="button-duration">⏱️ 20 Min</span>
          <span className="button-label">Deep rest</span>
        </button>
      </div>

      <p className="break-info">
        💡 Taking regular breaks significantly improves learning and retention. You'll be more productive after!
      </p>
    </div>
  );
};

export default BreakMode;
