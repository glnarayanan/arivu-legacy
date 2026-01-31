/**
 * Milestone tracking utilities for Arivu
 * Tracks user achievements and progress to create celebratory moments
 */

// Milestone localStorage keys
const MILESTONE_KEYS = {
  bookmark_10: 'arivu_milestone_bookmark_10',
  bookmark_50: 'arivu_milestone_bookmark_50',
  bookmark_100: 'arivu_milestone_bookmark_100',
  first_resurfacing: 'arivu_milestone_first_resurfacing',
  first_graph: 'arivu_milestone_first_graph',
};

// Milestone messages
const MILESTONE_MESSAGES = {
  bookmark_10: {
    title: 'Building Momentum',
    description: '10 bookmarks saved. Your collection grows.',
  },
  bookmark_50: {
    title: 'Knowledge Collector',
    description: "50 bookmarks. You're building something valuable.",
  },
  bookmark_100: {
    title: 'Knowledge Architect',
    description: '100 bookmarks. Your second brain is thriving.',
  },
  first_resurfacing: {
    title: 'First Rediscovery',
    description: 'You remembered something worth revisiting.',
  },
  first_graph: {
    title: 'Connected Thinking',
    description: 'Explore how your knowledge connects.',
  },
};

// Major milestones that get confetti
export const MAJOR_MILESTONES = ['bookmark_50', 'bookmark_100'];

/**
 * Check if a milestone has been reached
 * @param {string} name - The milestone name (e.g., 'bookmark_10', 'first_resurfacing')
 * @returns {{ reached: boolean, count?: number }} - Whether the milestone was reached and optional count
 */
export const checkMilestone = (name) => {
  const key = MILESTONE_KEYS[name];
  if (!key) {
    console.warn(`Unknown milestone: ${name}`);
    return { reached: false };
  }

  const value = localStorage.getItem(key);
  if (value) {
    // Milestone already reached
    return { reached: true, count: parseInt(value, 10) || undefined };
  }

  return { reached: false };
};

/**
 * Mark a milestone as reached
 * @param {string} name - The milestone name
 * @param {number} [count] - Optional count value to store
 */
export const markMilestoneReached = (name, count) => {
  const key = MILESTONE_KEYS[name];
  if (!key) {
    console.warn(`Unknown milestone: ${name}`);
    return;
  }

  localStorage.setItem(key, count !== undefined ? count.toString() : 'true');
};

/**
 * Get the message for a milestone
 * @param {string} name - The milestone name
 * @returns {{ title: string, description: string } | null} - The milestone message or null if not found
 */
export const getMilestoneMessage = (name) => {
  return MILESTONE_MESSAGES[name] || null;
};

/**
 * Check if a milestone is a major one (gets confetti)
 * @param {string} name - The milestone name
 * @returns {boolean}
 */
export const isMajorMilestone = (name) => {
  return MAJOR_MILESTONES.includes(name);
};

/**
 * Check bookmark count milestones
 * Returns the highest unclaimed milestone that should be triggered
 * @param {number} count - Current bookmark count
 * @returns {string | null} - The milestone name to trigger, or null
 */
export const checkBookmarkCountMilestones = (count) => {
  // Check from highest to lowest so we only trigger the highest applicable milestone
  const milestones = [
    { name: 'bookmark_100', threshold: 100 },
    { name: 'bookmark_50', threshold: 50 },
    { name: 'bookmark_10', threshold: 10 },
  ];

  for (const milestone of milestones) {
    if (count >= milestone.threshold) {
      const { reached } = checkMilestone(milestone.name);
      if (!reached) {
        return milestone.name;
      }
    }
  }

  return null;
};
