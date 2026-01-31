import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';

/**
 * ErrorMessage component for displaying errors with optional retry
 *
 * @param {Object} props
 * @param {string} props.title - Error title (e.g., "Failed to load bookmarks")
 * @param {string} [props.message] - Optional detailed error message
 * @param {Function} [props.onRetry] - Optional retry callback
 * @param {boolean} [props.retrying] - Whether retry is in progress
 * @param {string} [props.className] - Additional CSS classes
 */
const ErrorMessage = ({
  title,
  message,
  onRetry,
  retrying = false,
  className = ''
}) => {
  return (
    <div className={`text-center py-12 px-6 border-2 border-destructive/30 bg-destructive/5 ${className}`}>
      <AlertCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
      <h3 className="font-heading font-bold text-lg uppercase tracking-wide mb-2">
        {title}
      </h3>
      {message && (
        <p className="text-muted-foreground font-mono text-sm mb-4 max-w-md mx-auto">
          {message}
        </p>
      )}
      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          disabled={retrying}
          className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase tracking-wider"
        >
          {retrying ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Retrying...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </>
          )}
        </Button>
      )}
    </div>
  );
};

export default ErrorMessage;
