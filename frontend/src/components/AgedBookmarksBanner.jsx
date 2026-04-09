import _u1_React from 'react';
import { Archive, Clock } from 'lucide-react';
import { Button } from './ui/button';

const AgedBookmarksBanner = ({ agedCount, onViewAged }) => {
  if (agedCount === 0) {
    return null;
  }

  return (
    <div className="bg-amber-50 border-2 border-foreground p-4 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-100 border-2 border-foreground flex-shrink-0">
            <Archive className="w-4 h-4 text-amber-700" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-amber-900 uppercase">
              {agedCount} bookmark{agedCount > 1 ? 's' : ''} collecting dust
            </h3>
            <p className="font-mono text-xs text-amber-700 flex items-center gap-1 uppercase tracking-wider">
              <Clock className="w-3 h-3" />
              Haven't been opened in over 30 days
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onViewAged}
          className="border-2 border-amber-700 text-amber-700 hover:bg-amber-100 flex-shrink-0"
        >
          REVIEW NOW
        </Button>
      </div>
    </div>
  );
};

export default AgedBookmarksBanner;
