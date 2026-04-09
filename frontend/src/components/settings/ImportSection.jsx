import { useState, useEffect } from 'react';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Progress } from '../ui/progress';
import { toast } from 'sonner';
import {
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Upload,
  RefreshCw
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { motion } from 'framer-motion';
import { StaggerContainer, StaggerItem } from '../motion/PageOrchestrator';

const ImportSection = () => {
  const [importJobs, setImportJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);

  const fetchImportJobs = async () => {
    try {
      const response = await axiosInstance.get('/import-jobs');
      setImportJobs(response.data);
    } catch (error) {
      console.error('Error fetching import jobs:', error);
      toast.error('Failed to fetch import jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchImportJobs();

    const pollInterval = setInterval(() => {
      const hasActiveJobs = importJobs.some(job => job.status === 'processing');
      if (hasActiveJobs) {
        fetchImportJobs();
      }
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [importJobs]);

  const handleImportBookmarks = async (e) => {
    e.preventDefault();
    if (!importFile) return;

    setImporting(true);
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const response = await axiosInstance.post(
            `/bookmarks/import`,
            event.target.result,
            { headers: { 'Content-Type': 'text/plain' } }
          );

          toast.success(`Import started! Processing ${response.data.count} bookmarks...`);
          setImportFile(null);
          setImportDialogOpen(false);
          fetchImportJobs();
        } catch (_u70_error) {
          toast.error('Failed to import bookmarks');
        } finally {
          setImporting(false);
        }
      };
      reader.readAsText(importFile);
    } catch (_u77_error) {
      toast.error('Failed to read file');
      setImporting(false);
    }
  };

  const formatDate = (isoDate) => {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.round(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;

    const diffHours = Math.round(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;

    const diffDays = Math.round(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  const formatETA = (isoDate) => {
    if (!isoDate) return 'Calculating...';
    const eta = new Date(isoDate);
    const now = new Date();
    const diffMs = eta - now;

    if (diffMs <= 0) return 'Almost done...';

    const diffMins = Math.round(diffMs / 60000);
    if (diffMins < 60) return `~${diffMins} minute${diffMins > 1 ? 's' : ''}`;

    const diffHours = Math.round(diffMins / 60);
    return `~${diffHours} hour${diffHours > 1 ? 's' : ''}`;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-destructive" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusText = (job) => {
    if (job.status === 'completed') return 'Completed';
    if (job.status === 'failed') return 'Failed';

    const isPhase1Complete = job.content_fetched === job.total_bookmarks;
    if (isPhase1Complete) {
      return 'Processing AI summaries...';
    }
    return 'Fetching content...';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-2xl uppercase tracking-wide mb-2">Import Bookmarks</h2>
          <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
            Import bookmarks from other browsers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchImportJobs}
            className="rounded-none border-2 border-foreground font-mono uppercase text-xs"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all font-mono uppercase text-xs">
                <Upload className="h-4 w-4 mr-2" />
                New Import
              </Button>
            </DialogTrigger>
            <DialogContent className="rounded-none border-2 border-foreground shadow-brutal">
              <DialogHeader>
                <DialogTitle className="font-display text-xl uppercase tracking-wide">Import Bookmarks</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleImportBookmarks} className="space-y-4">
                <div>
                  <label className="block font-mono text-xs uppercase tracking-wider mb-2">
                    Select file to import
                  </label>
                  <Input
                    type="file"
                    accept=".html,.txt,.csv"
                    onChange={(e) => setImportFile(e.target.files[0])}
                    required
                    className="rounded-none border-2 border-foreground"
                  />
                  <p className="font-mono text-xs text-muted-foreground mt-2 uppercase tracking-wider">
                    Supported formats:
                  </p>
                  <ul className="font-mono text-xs text-muted-foreground mt-1 ml-4 list-disc space-y-1">
                    <li><strong>HTML:</strong> Browser bookmark exports (Chrome/Firefox/Safari)</li>
                    <li><strong>TXT:</strong> Plain text file with one URL per line</li>
                    <li><strong>CSV:</strong> Comma-separated file with URL column</li>
                  </ul>
                </div>
                <Button
                  type="submit"
                  disabled={importing || !importFile}
                  className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                >
                  {importing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      STARTING IMPORT...
                    </>
                  ) : (
                    'START IMPORT'
                  )}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Import History */}
      {importJobs.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-12 border-2 border-dashed border-muted-foreground/30"
        >
          <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="font-display text-xl uppercase tracking-wide mb-2">No imports yet</h3>
          <p className="text-muted-foreground font-mono text-sm mb-4">
            Start importing your bookmarks from other browsers
          </p>
          <Button
            onClick={() => setImportDialogOpen(true)}
            className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
          >
            <Upload className="h-4 w-4 mr-2" />
            IMPORT BOOKMARKS
          </Button>
        </motion.div>
      ) : (
        <StaggerContainer className="space-y-4">
          {importJobs.map((job) => {
            const contentProgress = Math.round((job.content_fetched / job.total_bookmarks) * 100);
            const aiProgress = Math.round((job.ai_processed / job.total_bookmarks) * 100);
            const isPhase1Complete = job.content_fetched === job.total_bookmarks;

            return (
              <StaggerItem key={job.id}>
                <div className="bg-background border-2 border-foreground p-6 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <div>
                        <h3 className="font-heading font-bold">
                          {job.total_bookmarks} bookmark{job.total_bookmarks !== 1 ? 's' : ''}
                        </h3>
                        <p className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
                          {formatDate(job.created_at)} • {getStatusText(job)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {job.status === 'processing' && job.estimated_completion_time && (
                        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground uppercase tracking-wider">
                          <Clock className="h-4 w-4" />
                          <span>ETA: {formatETA(job.estimated_completion_time)}</span>
                        </div>
                      )}
                      {job.status === 'completed' && (
                        <div className="font-mono text-xs text-green-600 font-medium uppercase tracking-wider">
                          IMPORT COMPLETE
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between font-mono text-xs uppercase tracking-wider">
                        <span className="text-muted-foreground">
                          Phase 1: Content Fetching
                          {isPhase1Complete && (
                            <CheckCircle className="inline ml-2 h-4 w-4 text-green-600" />
                          )}
                        </span>
                        <span className="text-muted-foreground">
                          {job.content_fetched} / {job.total_bookmarks}
                        </span>
                      </div>
                      <Progress value={contentProgress} className="h-2" />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between font-mono text-xs uppercase tracking-wider">
                        <span className="text-muted-foreground">
                          Phase 2: AI Processing
                          {job.status === 'completed' && (
                            <CheckCircle className="inline ml-2 h-4 w-4 text-green-600" />
                          )}
                        </span>
                        <span className="text-muted-foreground">
                          {job.ai_processed} / {job.total_bookmarks}
                        </span>
                      </div>
                      <Progress value={aiProgress} className="h-2" />
                    </div>
                  </div>

                  {(job.failed > 0 || job.status === 'completed') && (
                    <div className="mt-4 pt-4 border-t-2 border-foreground flex items-center justify-between font-mono text-xs uppercase tracking-wider">
                      <div className="flex items-center gap-4">
                        <div>
                          <span className="text-muted-foreground">Successful: </span>
                          <span className="font-medium">
                            {job.total_bookmarks - job.failed}
                          </span>
                        </div>
                        {job.failed > 0 && (
                          <div>
                            <span className="text-muted-foreground">Failed: </span>
                            <span className="font-medium text-destructive">{job.failed}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </StaggerItem>
            );
          })}
        </StaggerContainer>
      )}
    </div>
  );
};

export default ImportSection;
