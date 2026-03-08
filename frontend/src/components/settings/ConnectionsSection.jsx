import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import {
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Unplug,
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { StaggerContainer, StaggerItem } from '../motion/PageOrchestrator';

const XLogo = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const ConnectionsSection = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  const fetchStatus = async () => {
    try {
      const response = await axiosInstance.get('/auth/x/status');
      setStatus(response.data);
    } catch (error) {
      console.error('Error fetching X status:', error);
      setStatus({ connected: false });
    } finally {
      setLoading(false);
    }
  };

  // Handle OAuth callback (code + state in URL)
  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code && state) {
      const handleCallback = async () => {
        setConnecting(true);
        try {
          const response = await axiosInstance.post('/auth/x/callback', { code, state });
          toast.success(`Connected to X as @${response.data.x_username}`);
          // Clean up URL params
          setSearchParams({ section: 'connections' });
          fetchStatus();
        } catch (error) {
          const detail = error.response?.data?.detail || 'Failed to connect X account';
          toast.error(detail);
        } finally {
          setConnecting(false);
        }
      };
      handleCallback();
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, []);

  // Poll while syncing
  useEffect(() => {
    if (status?.sync_status === 'syncing') {
      const interval = setInterval(fetchStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [status?.sync_status]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const response = await axiosInstance.get('/auth/x/connect');
      window.location.href = response.data.auth_url;
    } catch (error) {
      const detail = error.response?.data?.detail || 'Failed to start X connection';
      toast.error(detail);
      setConnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const response = await axiosInstance.post('/auth/x/sync');
      setSyncResult(response.data);
      toast.success(
        `Synced: ${response.data.new_bookmarks} new, ${response.data.duplicates_skipped} skipped`
      );
      fetchStatus();
    } catch (error) {
      const detail = error.response?.data?.detail || 'Sync failed';
      toast.error(detail);
    } finally {
      setSyncing(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await axiosInstance.post('/auth/x/disconnect');
      toast.success('X account disconnected');
      setStatus({ connected: false });
      setSyncResult(null);
      setDisconnectDialogOpen(false);
    } catch (error) {
      toast.error('Failed to disconnect');
    } finally {
      setDisconnecting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <StaggerContainer className="space-y-6">
      {/* X (Twitter) Connection Card */}
      <StaggerItem>
        <div className="border-2 border-foreground bg-card p-6 shadow-brutal-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-foreground text-background">
              <XLogo className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-heading font-bold uppercase tracking-wide">X (Twitter)</h4>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Import your X bookmarks
              </p>
            </div>
          </div>

          {connecting ? (
            <div className="flex items-center gap-3 py-4">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="font-mono text-sm uppercase tracking-wider">Connecting...</span>
            </div>
          ) : status?.connected ? (
            <div className="space-y-4">
              {/* Connected Profile */}
              <div className="flex items-center gap-3 p-3 border-2 border-foreground bg-muted">
                {status.x_profile_image && (
                  <img
                    src={status.x_profile_image}
                    alt={status.x_username}
                    className="w-10 h-10 border-2 border-foreground"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                    <span className="font-heading font-bold truncate">
                      {status.x_name || status.x_username}
                    </span>
                  </div>
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    @{status.x_username}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 border-2 border-foreground bg-background">
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground block mb-1">
                    Total Synced
                  </span>
                  <span className="font-heading text-xl font-bold">{status.total_synced || 0}</span>
                </div>
                <div className="p-3 border-2 border-foreground bg-background">
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground block mb-1">
                    Last Sync
                  </span>
                  <span className="font-mono text-sm">
                    {status.last_sync_at
                      ? new Date(status.last_sync_at).toLocaleDateString()
                      : 'Never'}
                  </span>
                </div>
              </div>

              {/* Sync Result */}
              {syncResult && (
                <div className="p-3 border-2 border-foreground bg-green-50">
                  <span className="font-mono text-xs uppercase tracking-wider block mb-1">
                    Sync Complete
                  </span>
                  <div className="font-mono text-sm space-y-1">
                    <div>Fetched: {syncResult.total_fetched}</div>
                    <div>New: {syncResult.new_bookmarks}</div>
                    <div>Skipped: {syncResult.duplicates_skipped}</div>
                  </div>
                </div>
              )}

              {/* Auth Expired Warning */}
              {status.sync_status === 'auth_expired' && (
                <div className="flex items-center gap-2 p-3 border-2 border-red-500 bg-red-50">
                  <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span className="font-mono text-xs uppercase tracking-wider text-red-700">
                    Authentication expired — please reconnect
                  </span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3">
                <Button
                  onClick={handleSync}
                  disabled={syncing || status.sync_status === 'syncing'}
                  className="flex-1 rounded-none border-2 border-foreground bg-primary text-primary-foreground font-mono uppercase text-xs tracking-wider shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-transform"
                >
                  {syncing || status.sync_status === 'syncing' ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Sync Bookmarks
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setDisconnectDialogOpen(true)}
                  className="rounded-none border-2 border-foreground font-mono uppercase text-xs tracking-wider hover:bg-red-50 hover:text-red-700 hover:border-red-500"
                >
                  <Unplug className="w-4 h-4 mr-2" />
                  Disconnect
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Connect your X account to import your bookmarked tweets into Arivu.
                They'll be processed through the same AI pipeline — summaries, tags, and knowledge graph.
              </p>
              <Button
                onClick={handleConnect}
                className="rounded-none border-2 border-foreground bg-foreground text-background font-mono uppercase text-xs tracking-wider shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-transform"
              >
                <XLogo className="w-4 h-4 mr-2" />
                Connect X Account
              </Button>
            </div>
          )}
        </div>
      </StaggerItem>

      {/* Disconnect Confirmation Dialog */}
      <Dialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
        <DialogContent className="rounded-none border-2 border-foreground shadow-brutal">
          <DialogHeader>
            <DialogTitle className="font-heading font-bold uppercase tracking-wide">
              Disconnect X Account?
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground mb-4">
            This will remove the connection. Your existing X bookmarks will remain in Arivu.
          </p>
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setDisconnectDialogOpen(false)}
              className="rounded-none border-2 border-foreground font-mono uppercase text-xs tracking-wider"
            >
              Cancel
            </Button>
            <Button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="rounded-none border-2 border-red-500 bg-red-500 text-white font-mono uppercase text-xs tracking-wider hover:bg-red-600"
            >
              {disconnecting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              Disconnect
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </StaggerContainer>
  );
};

export default ConnectionsSection;
