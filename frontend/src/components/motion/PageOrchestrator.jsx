import { motion, useReducedMotion } from 'framer-motion';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

export const StaggerContainer = ({ children, delay = 0, className = "" }) => {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: shouldReduceMotion ? 0 : 0.08,
            delayChildren: delay,
          }
        }
      }}
    >
      {children}
    </motion.div>
  );
};

export const StaggerItem = ({ children, className = "" }) => {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { 
          opacity: 0, 
          y: shouldReduceMotion ? 0 : 40,
          scale: 0.98
        },
        visible: { 
          opacity: 1, 
          y: 0,
          scale: 1,
          transition: brutalSpring
        }
      }}
    >
      {children}
    </motion.div>
  );
};

export const HardReveal = ({ children, direction = 'up', className = "", delay = 0 }) => {
  const shouldReduceMotion = useReducedMotion();
  
  const clipPaths = {
    up: ['inset(100% 0 0 0)', 'inset(0)'],
    down: ['inset(0 0 100% 0)', 'inset(0)'],
    left: ['inset(0 100% 0 0)', 'inset(0)'],
    right: ['inset(0 0 0 100%)', 'inset(0)'],
  };
  
  if (shouldReduceMotion) {
    return <div className={className}>{children}</div>;
  }
  
  return (
    <motion.div
      className={className}
      initial={{ clipPath: clipPaths[direction][0] }}
      animate={{ clipPath: clipPaths[direction][1] }}
      transition={{ 
        duration: 0.6, 
        ease: [0.16, 1, 0.3, 1],
        delay 
      }}
    >
      {children}
    </motion.div>
  );
};

export const FadeIn = ({ children, className = "", delay = 0 }) => {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        ...brutalSpring,
        delay 
      }}
    >
      {children}
    </motion.div>
  );
};

export const SlideIn = ({ children, direction = 'left', className = "", delay = 0 }) => {
  const shouldReduceMotion = useReducedMotion();
  
  const offsets = {
    left: { x: -40, y: 0 },
    right: { x: 40, y: 0 },
    up: { x: 0, y: -40 },
    down: { x: 0, y: 40 },
  };
  
  const offset = offsets[direction];
  
  return (
    <motion.div
      className={className}
      initial={{ 
        opacity: 0, 
        x: shouldReduceMotion ? 0 : offset.x,
        y: shouldReduceMotion ? 0 : offset.y
      }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ 
        ...brutalSpring,
        delay 
      }}
    >
      {children}
    </motion.div>
  );
};

export const ScaleIn = ({ children, className = "", delay = 0 }) => {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      className={className}
      initial={{ 
        opacity: 0, 
        scale: shouldReduceMotion ? 1 : 0.9 
      }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ 
        ...brutalSpring,
        delay 
      }}
    >
      {children}
    </motion.div>
  );
};

export const PageTransition = ({ children, className = "" }) => {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      {children}
    </motion.div>
  );
};

export { motion, useReducedMotion };
