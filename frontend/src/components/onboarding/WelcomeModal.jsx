import { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { X, BookmarkIcon, Brain as _u3_Brain, Sparkles, Network, ArrowRight } from 'lucide-react';
import { Button } from '../ui/button';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

const WELCOME_STORAGE_KEY = 'arivu_welcome_completed';

/**
 * Welcome modal shown to first-time users after signup/login.
 * Introduces core value prop and key features without being overwhelming.
 */
export const WelcomeModal = ({ onComplete, forceShow = false }) => {
  const shouldReduceMotion = useReducedMotion();
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (forceShow) {
      setIsOpen(true);
      return;
    }

    const hasSeenWelcome = localStorage.getItem(WELCOME_STORAGE_KEY);
    if (!hasSeenWelcome) {
      // Small delay to let dashboard load first
      const timer = setTimeout(() => setIsOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, [forceShow]);

  const handleComplete = () => {
    localStorage.setItem(WELCOME_STORAGE_KEY, 'true');
    setIsOpen(false);
    onComplete?.();
  };

  const handleSkip = () => {
    localStorage.setItem(WELCOME_STORAGE_KEY, 'true');
    setIsOpen(false);
    onComplete?.();
  };

  const steps = [
    {
      icon: BookmarkIcon,
      iconBg: 'bg-primary',
      title: 'Save Anything',
      description: 'Save any webpage with one click. Arivu fetches the content and stores it forever.',
    },
    {
      icon: Sparkles,
      iconBg: 'bg-accent',
      title: 'AI Understands It',
      description: 'Our AI reads everything you save—summarizing, tagging, and extracting key insights automatically.',
    },
    {
      icon: Network,
      iconBg: 'bg-foreground',
      title: 'Discover Connections',
      description: 'Watch your knowledge connect. The Knowledge Graph reveals relationships you never knew existed.',
    },
  ];

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-foreground/80"
          onClick={handleSkip}
        />

        {/* Modal */}
        <motion.div
          initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 20, scale: 0.95 }}
          transition={brutalSpring}
          className="relative w-full max-w-md bg-card border-2 border-foreground shadow-brutal"
        >
          {/* Close button */}
          <button
            onClick={handleSkip}
            className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center hover:bg-muted transition-colors z-10"
            aria-label="Skip welcome"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Content */}
          <div className="p-8">
            {/* Step indicator */}
            <div className="flex justify-center gap-2 mb-8">
              {steps.map((_, index) => (
                <div
                  key={index}
                  className={`h-1 w-8 transition-colors ${
                    index <= currentStep ? 'bg-primary' : 'bg-muted'
                  }`}
                />
              ))}
            </div>

            {/* Icon */}
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={shouldReduceMotion ? {} : { opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={shouldReduceMotion ? {} : { opacity: 0, x: -20 }}
                transition={brutalSpring}
                className="flex flex-col items-center text-center"
              >
                <div className={`w-16 h-16 border-2 border-foreground ${currentStepData.iconBg} flex items-center justify-center mb-6 shadow-brutal`}>
                  <currentStepData.icon className={`w-8 h-8 ${currentStepData.iconBg === 'bg-foreground' ? 'text-background' : 'text-primary-foreground'}`} />
                </div>

                <h2 className="font-display text-3xl font-bold uppercase tracking-wide mb-3">
                  {currentStepData.title}
                </h2>

                <p className="text-muted-foreground font-body text-base leading-relaxed max-w-xs">
                  {currentStepData.description}
                </p>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Footer */}
          <div className="px-8 pb-8 flex items-center justify-between">
            <button
              onClick={handleSkip}
              className="font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip intro
            </button>

            <Button
              onClick={() => {
                if (isLastStep) {
                  handleComplete();
                } else {
                  setCurrentStep(prev => prev + 1);
                }
              }}
              className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
            >
              {isLastStep ? (
                <>
                  Get Started
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              ) : (
                'Next'
              )}
            </Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default WelcomeModal;
