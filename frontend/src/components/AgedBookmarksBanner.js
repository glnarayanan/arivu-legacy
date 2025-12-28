import React from 'react';
import { Archive, Clock } from 'lucide-react';
import { Button } from './ui/button';

/**
 * AgedBookmarksBanner Component
 *
 * Displays a warning banner when user has bookmarks that haven't been
 * accessed in over 30 days. Encourages users to review and clean up
 * their stale bookmarks.
 *
 * @param {number} agedCount - Number of aged bookmarks (>30 days)
 * @param {function} onViewAged - Callback to filter/view aged bookmarks
 */
const AgedBookmarksBanner = ({ agedCount, onViewAged }) => {
  // Don't render if no aged bookmarks
  if (agedCount === 0) {
    return null;
  }

  return (
    <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Icon */}
          <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-full flex-shrink-0">
            <Archive className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>

          {/* Content */}
          <div>
            <h3 className="font-semibold text-amber-900 dark:text-amber-100">
              {agedCount} bookmark{agedCount > 1 ? 's' : ''} collecting dust
            </h3>
            <p className="text-sm text-amber-700 dark:text-amber-300 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Haven't been opened in over 30 days
            </p>
          </div>
        </div>

        {/* Action Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onViewAged}
          className="border-amber-300 hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900/30 flex-shrink-0"
        >
          Review Now
        </Button>
      </div>
    </div>
  );
};

export default AgedBookmarksBanner;
