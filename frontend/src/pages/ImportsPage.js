import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Upload,
  RefreshCw
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';

const ImportsPage = () => {
  const navigate = useNavigate();
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

    // Poll for updates every 5 seconds if there are active jobs
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
          fetchImportJobs(); // Refresh the list
        } catch (error) {
          toast.error('Failed to import bookmarks');
        } finally {
          setImporting(false);
        }
      };
      reader.readAsText(importFile);
    } catch (error) {
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
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/dashboard')}
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div>
                <h1 className="text-2xl font-bold">Import History</h1>
                <p className="text-sm text-muted-foreground">
                  Track your bookmark imports and their progress
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchImportJobs}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Upload className="h-4 w-4 mr-2" />
                    New Import
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Import Bookmarks</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleImportBookmarks} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Select file to import
                      </label>
                      <Input
                        type="file"
                        accept=".html,.txt,.csv"
                        onChange={(e) => setImportFile(e.target.files[0])}
                        required
                      />
                      <p className="text-xs text-muted-foreground mt-2">
                        Supported formats:
                      </p>
                      <ul className="text-xs text-muted-foreground mt-1 ml-4 list-disc space-y-1">
                        <li><strong>HTML:</strong> Browser bookmark exports (Chrome/Firefox/Safari)</li>
                        <li><strong>TXT:</strong> Plain text file with one URL per line</li>
                        <li><strong>CSV:</strong> Comma-separated file with URL column (optional title column)</li>
                      </ul>
                    </div>
                    <Button type="submit" disabled={importing || !importFile} className="w-full">
                      {importing ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Starting Import...
                        </>
                      ) : (
                        'Start Import'
                      )}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </div>

      {/* Import Jobs List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {importJobs.length === 0 ? (
          <div className="text-center py-12">
            <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No imports yet</h3>
            <p className="text-muted-foreground mb-4">
              Start importing your bookmarks from other browsers
            </p>
            <Button onClick={() => setImportDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Import Bookmarks
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {importJobs.map((job) => {
              const contentProgress = Math.round((job.content_fetched / job.total_bookmarks) * 100);
              const aiProgress = Math.round((job.ai_processed / job.total_bookmarks) * 100);
              const isPhase1Complete = job.content_fetched === job.total_bookmarks;

              return (
                <div
                  key={job.id}
                  className="bg-card border rounded-lg p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <div>
                        <h3 className="font-semibold">
                          {job.total_bookmarks} bookmark{job.total_bookmarks !== 1 ? 's' : ''}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(job.created_at)} • {getStatusText(job)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {job.status === 'processing' && job.estimated_completion_time && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          <span>ETA: {formatETA(job.estimated_completion_time)}</span>
                        </div>
                      )}
                      {job.status === 'completed' && (
                        <div className="text-sm text-green-600 dark:text-green-400 font-medium">
                          ✓ Import Complete
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Progress Bars */}
                  <div className="space-y-4">
                    {/* Phase 1: Content Fetching */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-muted-foreground">
                          Phase 1: Content Fetching
                          {isPhase1Complete && (
                            <CheckCircle className="inline ml-2 h-4 w-4 text-green-500" />
                          )}
                        </span>
                        <span className="text-muted-foreground">
                          {job.content_fetched} / {job.total_bookmarks}
                        </span>
                      </div>
                      <Progress value={contentProgress} className="h-2" />
                    </div>

                    {/* Phase 2: AI Processing */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-muted-foreground">
                          Phase 2: AI Processing
                          {job.status === 'completed' && (
                            <CheckCircle className="inline ml-2 h-4 w-4 text-green-500" />
                          )}
                        </span>
                        <span className="text-muted-foreground">
                          {job.ai_processed} / {job.total_bookmarks}
                        </span>
                      </div>
                      <Progress value={aiProgress} className="h-2" />
                    </div>
                  </div>

                  {/* Stats Footer */}
                  {(job.failed > 0 || job.status === 'completed') && (
                    <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
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
                            <span className="font-medium text-red-500">{job.failed}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ImportsPage;
