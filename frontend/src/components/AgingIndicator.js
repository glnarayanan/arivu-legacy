import React from 'react';

/**
 * AgingIndicator Component
 *
 * Displays a visual badge showing how long ago a bookmark was last accessed.
 * Color-coded based on aging thresholds:
 * - Fresh (<7 days): Green
 * - Aging (7-30 days): Yellow
 * - Stale (30-90 days): Orange
 * - Ancient (>90 days): Red
 *
 * @param {Object} bookmark - Bookmark object with last_accessed or created_at
 * @param {string} size - Size variant: 'compact' or 'normal' (default: 'normal')
 */
const AgingIndicator = ({ bookmark, size = 'normal' }) => {
  // Calculate days since last access
  const lastAccessed = bookmark.last_accessed || bookmark.created_at;

  if (!lastAccessed) {
    return null; // Don't render if no date available
  }

  const daysSinceAccess = Math.floor(
    (Date.now() - new Date(lastAccessed)) / (1000 * 60 * 60 * 24)
  );

  const getAgingStatus = (days) => {
    if (days < 7) {
      return {
        label: 'Fresh',
        color: 'bg-green-500',
        textColor: 'text-green-700 dark:text-green-300',
        bgColor: 'bg-green-100 dark:bg-green-900/20',
        borderColor: 'border-green-200 dark:border-green-800'
      };
    }
    if (days < 30) {
      return {
        label: 'Aging',
        color: 'bg-yellow-500',
        textColor: 'text-yellow-700 dark:text-yellow-300',
        bgColor: 'bg-yellow-100 dark:bg-yellow-900/20',
        borderColor: 'border-yellow-200 dark:border-yellow-800'
      };
    }
    if (days < 90) {
      return {
        label: 'Stale',
        color: 'bg-orange-500',
        textColor: 'text-orange-700 dark:text-orange-300',
        bgColor: 'bg-orange-100 dark:bg-orange-900/20',
        borderColor: 'border-orange-200 dark:border-orange-800'
      };
    }
    return {
      label: 'Ancient',
      color: 'bg-red-500',
      textColor: 'text-red-700 dark:text-red-300',
      bgColor: 'bg-red-100 dark:bg-red-900/20',
      borderColor: 'border-red-200 dark:border-red-800'
    };
  };

  const status = getAgingStatus(daysSinceAccess);

  // Size variants
  const sizeClasses = size === 'compact' ? {
    container: 'px-1.5 py-0.5',
    dot: 'w-1 h-1',
    text: 'text-xs'
  } : {
    container: 'px-2 py-1',
    dot: 'w-1.5 h-1.5',
    text: 'text-xs'
  };

  return (
    <div
      className={`flex items-center gap-1.5 rounded-full ${status.bgColor} ${sizeClasses.container}`}
      title={`Last accessed ${daysSinceAccess} day${daysSinceAccess !== 1 ? 's' : ''} ago - ${status.label}`}
    >
      <div className={`${sizeClasses.dot} rounded-full ${status.color}`} />
      <span className={`${sizeClasses.text} font-medium ${status.textColor}`}>
        {daysSinceAccess}d
      </span>
    </div>
  );
};

export default AgingIndicator;
