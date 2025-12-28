import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import { Progress } from './ui/progress';
import axiosInstance from '../utils/axiosConfig';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';

const ImportProgressModal = ({ importJobId, isOpen, onClose }) => {
  const [jobData, setJobData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!importJobId || !isOpen) return;

    const fetchProgress = async () => {
      try {
        const response = await axiosInstance.get(`/import-jobs/${importJobId}`);
        setJobData(response.data);
        setError(null);

        // Stop polling if job is completed or failed
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Error fetching import progress:', err);
        setError('Failed to fetch import progress');
      }
    };

    // Initial fetch
    fetchProgress();

    // Poll every 5 seconds
    const pollInterval = setInterval(fetchProgress, 5000);

    return () => clearInterval(pollInterval);
  }, [importJobId, isOpen]);

  if (!jobData) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Import Progress</DialogTitle>
            <DialogDescription>Loading import status...</DialogDescription>
          </DialogHeader>
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const contentProgress = Math.round((jobData.content_fetched / jobData.total_bookmarks) * 100);
  const aiProgress = Math.round((jobData.ai_processed / jobData.total_bookmarks) * 100);
  const isPhase1Complete = jobData.content_fetched === jobData.total_bookmarks;

  const formatETA = (isoDate) => {
    if (!isoDate) return 'Calculating...';
    const eta = new Date(isoDate);
    const now = new Date();
    const diffMs = eta - now;

    if (diffMs <= 0) return 'Almost done...';

    const diffMins = Math.round(diffMs / 60000);
    if (diffMins < 60) return `~${diffMins} minutes`;

    const diffHours = Math.round(diffMins / 60);
    return `~${diffHours} hour${diffHours > 1 ? 's' : ''}`;
  };

  const getStatusIcon = () => {
    if (jobData.status === 'completed') {
      return <CheckCircle className="h-6 w-6 text-green-500" />;
    }
    if (jobData.status === 'failed') {
      return <XCircle className="h-6 w-6 text-red-500" />;
    }
    return <Loader2 className="h-6 w-6 animate-spin text-primary" />;
  };

  const getStatusText = () => {
    if (jobData.status === 'completed') {
      return 'Import completed successfully!';
    }
    if (jobData.status === 'failed') {
      return 'Import failed';
    }
    if (isPhase1Complete) {
      return 'Processing AI summaries...';
    }
    return 'Fetching content...';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getStatusIcon()}
            Import Progress
          </DialogTitle>
          <DialogDescription>{getStatusText()}</DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        <div className="space-y-6 py-4">
          {/* Phase 1: Content Fetching */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                Phase 1: Content Fetching
                {isPhase1Complete && <CheckCircle className="inline ml-2 h-4 w-4 text-green-500" />}
              </span>
              <span className="text-muted-foreground">
                {jobData.content_fetched} / {jobData.total_bookmarks}
              </span>
            </div>
            <Progress value={contentProgress} className="h-2" />
            <div className="text-xs text-muted-foreground text-right">
              {contentProgress}% complete
            </div>
          </div>

          {/* Phase 2: AI Processing */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                Phase 2: AI Processing
                {jobData.status === 'completed' && <CheckCircle className="inline ml-2 h-4 w-4 text-green-500" />}
              </span>
              <span className="text-muted-foreground">
                {jobData.ai_processed} / {jobData.total_bookmarks}
              </span>
            </div>
            <Progress value={aiProgress} className="h-2" />
            <div className="text-xs text-muted-foreground text-right">
              {aiProgress}% complete
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Total Bookmarks</div>
              <div className="text-2xl font-semibold">{jobData.total_bookmarks}</div>
            </div>
            {jobData.failed > 0 && (
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Failed</div>
                <div className="text-2xl font-semibold text-red-500">{jobData.failed}</div>
              </div>
            )}
          </div>

          {/* ETA */}
          {jobData.status === 'processing' && jobData.estimated_completion_time && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground pt-2 border-t">
              <Clock className="h-4 w-4" />
              <span>Estimated completion: {formatETA(jobData.estimated_completion_time)}</span>
            </div>
          )}

          {/* Completion message */}
          {jobData.status === 'completed' && (
            <div className="rounded-md bg-green-50 dark:bg-green-900/20 p-3 text-sm text-green-800 dark:text-green-200">
              Successfully imported {jobData.total_bookmarks - jobData.failed} bookmark{jobData.total_bookmarks - jobData.failed !== 1 ? 's' : ''}!
              {jobData.failed > 0 && ` (${jobData.failed} failed)`}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImportProgressModal;
