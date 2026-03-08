import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

// Design system colors
const COLORS = ['#F97316', '#3B82F6', '#0F0F0F']; // orange, blue, black

/**
 * Generate a random particle configuration.
 * Particles are SQUARES and LINES only (brutalist style).
 */
const generateParticles = (count, origin) => {
  return Array.from({ length: count }, (_, i) => {
    const isLine = i % 3 === 0; // Every third particle is a line
    const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5;
    const velocity = 150 + Math.random() * 200; // pixels to travel
    const rotation = Math.random() * 360;

    return {
      id: i,
      type: isLine ? 'line' : 'square',
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      size: isLine ? { width: 2, height: 12 + Math.random() * 8 } : 6 + Math.random() * 6,
      x: origin.x,
      y: origin.y,
      targetX: origin.x + Math.cos(angle) * velocity,
      targetY: origin.y + Math.sin(angle) * velocity + 100, // gravity pulls down
      rotation,
      targetRotation: rotation + (Math.random() - 0.5) * 720,
    };
  });
};

/**
 * Single confetti particle component.
 */
const Particle = ({ particle, onComplete, isLast }) => {
  const { type, color, size, x, y, targetX, targetY, rotation, targetRotation } = particle;

  return (
    <motion.div
      initial={{
        x,
        y,
        rotate: rotation,
        scale: 1,
        opacity: 1,
      }}
      animate={{
        x: targetX,
        y: targetY,
        rotate: targetRotation,
        scale: 0,
        opacity: [1, 1, 0],
      }}
      transition={{
        duration: 0.8,
        ease: [0.25, 0.46, 0.45, 0.94], // custom easing for gravity feel
      }}
      onAnimationComplete={isLast ? onComplete : undefined}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: type === 'line' ? size.width : size,
        height: type === 'line' ? size.height : size,
        backgroundColor: color,
        pointerEvents: 'none',
      }}
    />
  );
};

/**
 * Geometric confetti burst with brutalist style.
 * Particles are SQUARES and LINES only (no circles).
 *
 * @param {boolean} active - Whether to show confetti
 * @param {{ x: number, y: number }} origin - Origin point for burst (optional, defaults to viewport center)
 * @param {function} onComplete - Callback when animation completes
 */
export const BrutalConfetti = ({
  active = false,
  origin,
  onComplete
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [particles, setParticles] = useState([]);

  const handleComplete = useCallback(() => {
    setParticles([]);
    onComplete?.();
  }, [onComplete]);

  useEffect(() => {
    if (active && !shouldReduceMotion) {
      // Calculate origin - default to viewport center
      const defaultOrigin = {
        x: typeof window !== 'undefined' ? window.innerWidth / 2 : 500,
        y: typeof window !== 'undefined' ? window.innerHeight / 2 : 300,
      };
      const burstOrigin = origin || defaultOrigin;

      // Generate 14 particles (within 12-16 range)
      setParticles(generateParticles(14, burstOrigin));
    } else if (active && shouldReduceMotion) {
      // For reduced motion, just call onComplete immediately
      onComplete?.();
    }
  }, [active, origin, shouldReduceMotion, onComplete]);

  // Don't render anything if reduced motion is preferred
  if (shouldReduceMotion) {
    return null;
  }

  return (
    <AnimatePresence>
      {particles.length > 0 && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 9999,
            overflow: 'hidden',
          }}
          aria-hidden="true"
        >
          {particles.map((particle, index) => (
            <Particle
              key={particle.id}
              particle={particle}
              onComplete={handleComplete}
              isLast={index === particles.length - 1}
            />
          ))}
        </div>
      )}
    </AnimatePresence>
  );
};

export default BrutalConfetti;
