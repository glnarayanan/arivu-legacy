import { useState, useEffect } from 'react';
import { useReducedMotion } from 'framer-motion';

/**
 * Cycles through an array of loading messages with brutalist styling.
 * Respects prefers-reduced-motion by showing only the first message.
 *
 * @param {string[]} messages - Array of messages to cycle through
 * @param {number} interval - Time in ms between message changes (default: 2000)
 * @param {string} className - Additional CSS classes
 */
export const LoadingMessages = ({
  messages = ['Loading...'],
  interval = 2000,
  className = ''
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // Don't cycle if reduced motion is preferred or only one message
    if (shouldReduceMotion || messages.length <= 1) {
      return;
    }

    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % messages.length);
    }, interval);

    return () => clearInterval(timer);
  }, [messages.length, interval, shouldReduceMotion]);

  return (
    <span
      className={`font-mono text-xs uppercase tracking-wider ${className}`}
      aria-live="polite"
      aria-atomic="true"
    >
      {messages[currentIndex]}
    </span>
  );
};

export default LoadingMessages;
