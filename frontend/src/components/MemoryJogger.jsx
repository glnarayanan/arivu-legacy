import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Sparkles, ExternalLink, X, Link2 } from 'lucide-react';
import { Button } from './ui/button';

const brutalSpring = {
  type: "spring",
  stiffness: 400,
  damping: 25,
  mass: 0.8
};

const MemoryJogger = ({
  data,
  onRevisit,
  onDismiss
}) => {
  const shouldReduceMotion = useReducedMotion();
  
  if (!data?.has_memory || !data?.bookmark) {
    return null;
  }

  const { bookmark, context } = data;
  const {
    id,
    title,
    url,
    domain,
    favicon,
    thumbnail,
    ai_summary
  } = bookmark;

  const {
    days_since_saved,
    connection_count,
    connected_topics,
    reason
  } = context || {};

  const handleRevisit = (e) => {
    e?.stopPropagation();
    window.open(url, '_blank');
    if (onRevisit) onRevisit(id);
  };

  const handleDismiss = (e) => {
    e.stopPropagation();
    if (onDismiss) onDismiss(id);
  };

  const contextText = [
    days_since_saved ? `${days_since_saved} days ago` : null,
    connection_count ? `Connects to ${connection_count} recent saves` : null
  ].filter(Boolean).join(' • ');

  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={brutalSpring}
      onClick={handleRevisit}
      className="w-full bg-background border-2 border-foreground p-4 mb-6 shadow-brutal cursor-pointer hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150"
    >
      {/* Header Label */}
      <div className="flex items-center gap-2 mb-3">
        <div className="p-1.5 bg-accent border-2 border-foreground">
          <Sparkles className="w-4 h-4 text-accent-foreground" />
        </div>
        <span className="font-mono text-xs uppercase tracking-wider text-accent font-medium">
          Memory of the Day
        </span>
      </div>

      {/* Main Content */}
      <div className="flex items-start gap-4">
        {/* Left: Thumbnail/Favicon + Content */}
        <div className="flex gap-4 flex-1 min-w-0">
          {/* Thumbnail */}
          <div className="flex-shrink-0 w-16 h-16 bg-muted border-2 border-foreground overflow-hidden">
            {thumbnail ? (
              <img
                src={thumbnail}
                alt=""
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-accent/10">
                {favicon ? (
                  <img src={favicon} alt="" className="w-8 h-8" />
                ) : (
                  <Sparkles className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
            )}
          </div>

          {/* Title + Summary */}
          <div className="flex-1 min-w-0">
            <h4 className="font-heading font-bold text-base leading-tight line-clamp-1 mb-1">
              {title || 'Untitled'}
            </h4>
            
            {/* Domain */}
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1 truncate">
              {domain}
            </p>

            {/* One-sentence summary */}
            {ai_summary?.one_sentence && (
              <p className="text-sm text-muted-foreground line-clamp-1">
                {ai_summary.one_sentence}
              </p>
            )}

            {/* Reason for resurfacing */}
            {reason && (
              <p className="text-xs text-accent font-mono uppercase tracking-wider mt-1">
                {reason}
              </p>
            )}
          </div>
        </div>

        {/* Right: Context + Actions */}
        <div className="flex-shrink-0 flex flex-col items-end gap-2">
          {/* Context info */}
          {contextText && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground font-mono uppercase tracking-wider">
              <Link2 className="w-3 h-3" />
              <span>{contextText}</span>
            </div>
          )}

          {/* Connected topics */}
          {connected_topics && connected_topics.length > 0 && (
            <div className="flex gap-1 flex-wrap justify-end">
              {connected_topics.slice(0, 2).map((topic, i) => (
                <span 
                  key={i}
                  className="px-2 py-0.5 bg-muted border border-foreground font-mono text-xs uppercase tracking-wider"
                >
                  {topic}
                </span>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 mt-1">
            <Button
              variant="accent"
              size="sm"
              onClick={handleRevisit}
              className="bg-primary text-primary-foreground border-primary"
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              REVISIT
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDismiss}
              title="Not today"
            >
              <X className="w-3 h-3 mr-1" />
              NOT TODAY
            </Button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default MemoryJogger;
