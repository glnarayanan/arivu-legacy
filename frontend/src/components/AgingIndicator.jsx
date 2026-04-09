import _u1_React from 'react';

const AgingIndicator = ({ bookmark, size = 'normal' }) => {
  const lastAccessed = bookmark.last_accessed || bookmark.created_at;

  if (!lastAccessed) {
    return null;
  }

  const daysSinceAccess = Math.floor(
    (Date.now() - new Date(lastAccessed)) / (1000 * 60 * 60 * 24)
  );

  const getAgingStatus = (days) => {
    if (days < 7) {
      return {
        label: 'Fresh',
        color: 'bg-green-500',
        textColor: 'text-green-700',
        bgColor: 'bg-green-100',
        borderColor: 'border-green-700'
      };
    }
    if (days < 30) {
      return {
        label: 'Aging',
        color: 'bg-yellow-500',
        textColor: 'text-yellow-700',
        bgColor: 'bg-yellow-100',
        borderColor: 'border-yellow-700'
      };
    }
    if (days < 90) {
      return {
        label: 'Stale',
        color: 'bg-orange-500',
        textColor: 'text-orange-700',
        bgColor: 'bg-orange-100',
        borderColor: 'border-orange-700'
      };
    }
    return {
      label: 'Ancient',
      color: 'bg-red-500',
      textColor: 'text-red-700',
      bgColor: 'bg-red-100',
      borderColor: 'border-red-700'
    };
  };

  const status = getAgingStatus(daysSinceAccess);

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
      className={`flex items-center gap-1.5 border ${status.borderColor} ${status.bgColor} ${sizeClasses.container}`}
      title={`Last accessed ${daysSinceAccess} day${daysSinceAccess !== 1 ? 's' : ''} ago - ${status.label}`}
    >
      <div className={`${sizeClasses.dot} ${status.color}`} />
      <span className={`${sizeClasses.text} font-mono font-medium uppercase tracking-wider ${status.textColor}`}>
        {daysSinceAccess}d
      </span>
    </div>
  );
};

export default AgingIndicator;
