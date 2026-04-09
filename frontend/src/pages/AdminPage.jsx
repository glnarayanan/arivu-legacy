import { useState, useEffect, useCallback, useRef as _u1_useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Progress as _u7_Progress } from '../components/ui/progress';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '../components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { toast } from 'sonner';
import { StaggerContainer, StaggerItem, HardReveal } from '../components/motion/PageOrchestrator';
import {
  BookmarkIcon, Users, Database, Cpu, Activity, RefreshCw, ArrowLeft,
  Shield, ShieldOff, KeyRound, Trash2, UserPlus, Zap, HardDrive,
  Clock, TrendingUp, Globe, BarChart3, Server,
} from 'lucide-react';

const timeAgo = (dateStr) => {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
};

const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const formatUptime = (seconds) => {
  if (!seconds) return 'N/A';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
};

const formatNumber = (n) => {
  if (n == null) return '0';
  return Number(n).toLocaleString();
};

const StatCard = ({ icon: Icon, label, value, sublabel, accent }) => (
  <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
    <div className="flex items-center gap-3 mb-3">
      <div className={`p-2 border-2 border-foreground ${accent ? 'bg-accent/10' : 'bg-primary/10'}`}>
        <Icon className={`w-5 h-5 ${accent ? 'text-accent' : 'text-primary'}`} />
      </div>
      <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
    </div>
    <div className="font-display text-3xl font-bold">{value}</div>
    {sublabel && (
      <div className="text-xs text-muted-foreground mt-1 font-mono uppercase tracking-wider">
        {sublabel}
      </div>
    )}
  </div>
);

const UsageBar = ({ label, current, max, unit = '' }) => {
  const pct = max > 0 ? Math.min((current / max) * 100, 100) : 0;
  const color = pct > 90 ? 'bg-destructive' : pct > 70 ? 'bg-primary' : 'bg-accent';
  return (
    <div className="bg-card border-2 border-foreground p-4 shadow-brutal">
      <div className="flex justify-between items-center mb-2">
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
        <span className="font-mono text-xs font-bold">{pct.toFixed(1)}%</span>
      </div>
      <div className="w-full h-3 bg-muted border border-foreground">
        <div className={`h-full ${color} transition-all duration-300`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex justify-between mt-1">
        <span className="font-mono text-xs text-muted-foreground">{formatNumber(current)}{unit}</span>
        <span className="font-mono text-xs text-muted-foreground">{formatNumber(max)}{unit}</span>
      </div>
    </div>
  );
};

const SectionHeader = ({ icon: Icon, title, onRefresh, loading }) => (
  <div className="flex items-center justify-between mb-6">
    <div className="flex items-center gap-3">
      <div className="p-2 border-2 border-foreground bg-foreground text-background">
        <Icon className="w-5 h-5" />
      </div>
      <h2 className="font-display text-2xl uppercase tracking-wide">{title}</h2>
    </div>
    {onRefresh && (
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={loading}
        className="border-2 border-foreground shadow-brutal brutal-hover font-mono text-xs uppercase tracking-wider"
      >
        <RefreshCw className={`w-3 h-3 mr-2 ${loading ? 'animate-spin' : ''}`} />
        Refresh
      </Button>
    )}
  </div>
);

// ── Overview Panel ──
const OverviewPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosInstance.get('/admin/overview');
      setData(res.data);
    } catch (_u134_err) {
      toast.error('Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const iv = setInterval(fetch, 30000);
    return () => clearInterval(iv);
  }, [fetch]);

  if (!data && loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="bg-card border-2 border-foreground p-5 shadow-brutal animate-pulse h-28" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div>
      <SectionHeader icon={BarChart3} title="Platform Overview" onRefresh={fetch} loading={loading} />
      <StaggerContainer className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StaggerItem>
          <StatCard icon={Users} label="Total Users" value={formatNumber(data.users?.total)} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={BookmarkIcon} label="Total Bookmarks" value={formatNumber(data.bookmarks?.total)} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={Database} label="Collections" value={formatNumber(data.collections?.total)} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={Zap} label="AI Summaries" value={formatNumber(data.ai_summaries?.total)} accent />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={TrendingUp} label="Bookmarks Today" value={formatNumber(data.bookmarks?.today)} sublabel={`Week: ${formatNumber(data.bookmarks?.this_week)} · Month: ${formatNumber(data.bookmarks?.this_month)}`} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={UserPlus} label="New Users Today" value={formatNumber(data.users?.today)} sublabel={`Week: ${formatNumber(data.users?.this_week)} · Month: ${formatNumber(data.users?.this_month)}`} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={BookmarkIcon} label="Avg Per User" value={data.bookmarks?.avg_per_user?.toFixed(1) || '0'} />
        </StaggerItem>
        <StaggerItem>
          <StatCard icon={Clock} label="Server Uptime" value={formatUptime(data.server?.uptime_seconds)} />
        </StaggerItem>
      </StaggerContainer>

      {data.mongodb && (
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={HardDrive} label="DB Data Size" value={formatBytes(data.mongodb.data_size)} />
          <StatCard icon={HardDrive} label="Storage Size" value={formatBytes(data.mongodb.storage_size)} />
          <StatCard icon={HardDrive} label="Index Size" value={formatBytes(data.mongodb.index_size)} />
          <StatCard icon={Database} label="DB Collections" value={formatNumber(data.mongodb.collections)} sublabel={`${formatNumber(data.mongodb.objects)} objects`} />
        </div>
      )}
    </div>
  );
};

// ── API Usage Panel ──
const ApiUsagePanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosInstance.get('/admin/api-usage');
      setData(res.data);
    } catch (_u211_err) {
      toast.error('Failed to load API usage');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const iv = setInterval(fetch, 10000);
    return () => clearInterval(iv);
  }, [fetch]);

  if (!data && loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-card border-2 border-foreground p-5 shadow-brutal animate-pulse h-32" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div>
      <SectionHeader icon={Zap} title="Gemini API Usage" onRefresh={fetch} loading={loading} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Activity} label="Requests Today" value={formatNumber(data.requests_today)} sublabel={`Max: ${formatNumber(data.limits?.max_daily)}`} accent />
        <StatCard icon={Activity} label="Tokens Today" value={formatNumber(data.tokens_today)} accent />
        <StatCard icon={Cpu} label="Current RPM" value={formatNumber(data.current_rpm)} sublabel={`Max: ${formatNumber(data.limits?.max_rpm)}`} />
        <StatCard icon={Cpu} label="Current TPM" value={formatNumber(data.current_tpm)} sublabel={`Max: ${formatNumber(data.limits?.max_tpm)}`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <UsageBar label="RPM Utilization" current={data.current_rpm} max={data.limits?.max_rpm} />
        <UsageBar label="TPM Utilization" current={data.current_tpm} max={data.limits?.max_tpm} />
        <UsageBar label="Daily Requests" current={data.requests_today} max={data.limits?.max_daily} />
      </div>

      <div className="mt-4 text-xs font-mono uppercase tracking-wider text-muted-foreground">
        Tracking Date: {data.current_date || 'N/A'}
      </div>
    </div>
  );
};

// ── User Management Panel ──
const UserManagementPanel = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', name: '' });
  const [inviting, setInviting] = useState(false);

  const [resetOpen, setResetOpen] = useState(false);
  const [resetUser, setResetUser] = useState(null);
  const [resetPassword, setResetPassword] = useState('');
  const [resetting, setResetting] = useState(false);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteUser, setDeleteUser] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const [banOpen, setBanOpen] = useState(false);
  const [banUser, setBanUser] = useState(null);
  const [banning, setBanning] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosInstance.get(`/admin/users?sort=${sortBy}&order=${sortOrder}`);
      setUsers(res.data);
    } catch (_u289_err) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortOrder]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const SortHeader = ({ field, children }) => (
    <th
      className="text-left font-mono text-xs uppercase tracking-wider p-3 cursor-pointer hover:bg-muted transition-colors border-b-2 border-foreground"
      onClick={() => handleSort(field)}
    >
      {children} {sortBy === field ? (sortOrder === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  const handleInvite = async () => {
    setInviting(true);
    try {
      await axiosInstance.post('/admin/users/invite', inviteForm);
      toast.success('Invite email sent successfully');
      setInviteOpen(false);
      setInviteForm({ email: '', name: '' });
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to invite user');
    } finally {
      setInviting(false);
    }
  };

  const handleBan = async () => {
    if (!banUser) return;
    setBanning(true);
    try {
      const action = banUser.banned ? 'unban' : 'ban';
      await axiosInstance.post(`/admin/users/${banUser.id}/${action}`);
      toast.success(`User ${action === 'ban' ? 'banned' : 'unbanned'}`);
      setBanOpen(false);
      setBanUser(null);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Action failed');
    } finally {
      setBanning(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resetUser || !resetPassword) return;
    setResetting(true);
    try {
      await axiosInstance.post(`/admin/users/${resetUser.id}/reset-password`, { new_password: resetPassword });
      toast.success('Password reset successfully');
      setResetOpen(false);
      setResetUser(null);
      setResetPassword('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password');
    } finally {
      setResetting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteUser) return;
    setDeleting(true);
    try {
      const res = await axiosInstance.delete(`/admin/users/${deleteUser.id}`);
      toast.success(`Deleted user and ${res.data.deleted_bookmarks} bookmarks`);
      setDeleteOpen(false);
      setDeleteUser(null);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete user');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <SectionHeader icon={Users} title="User Management" onRefresh={fetchUsers} loading={loading} />

      <div className="mb-4">
        <Button
          onClick={() => setInviteOpen(true)}
          className="border-2 border-foreground shadow-brutal brutal-hover font-mono text-xs uppercase tracking-wider"
        >
          <UserPlus className="w-4 h-4 mr-2" /> Invite User
        </Button>
      </div>

      <div className="border-2 border-foreground shadow-brutal overflow-x-auto">
        <table className="w-full">
          <thead className="bg-foreground text-background">
            <tr>
              <SortHeader field="name">Name</SortHeader>
              <SortHeader field="email">Email</SortHeader>
              <SortHeader field="bookmarks">Bookmarks</SortHeader>
              <th className="text-left font-mono text-xs uppercase tracking-wider p-3 border-b-2 border-foreground">Collections</th>
              <SortHeader field="created_at">Joined</SortHeader>
              <th className="text-left font-mono text-xs uppercase tracking-wider p-3 border-b-2 border-foreground">Last Active</th>
              <th className="text-left font-mono text-xs uppercase tracking-wider p-3 border-b-2 border-foreground">Status</th>
              <th className="text-left font-mono text-xs uppercase tracking-wider p-3 border-b-2 border-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-foreground/20 hover:bg-muted/50 transition-colors">
                <td className="p-3 font-medium">{user.name}</td>
                <td className="p-3 font-mono text-xs">{user.email}</td>
                <td className="p-3 font-mono text-sm font-bold">{formatNumber(user.bookmark_count)}</td>
                <td className="p-3 font-mono text-sm">{formatNumber(user.collection_count)}</td>
                <td className="p-3 font-mono text-xs text-muted-foreground">{timeAgo(user.created_at)}</td>
                <td className="p-3 font-mono text-xs text-muted-foreground">{timeAgo(user.last_bookmark_at)}</td>
                <td className="p-3">
                  <div className="flex gap-1 flex-wrap">
                    {user.is_admin && <Badge variant="ai">Admin</Badge>}
                    {user.invite_pending ? (
                      <Badge variant="outline" className="border-amber-500 text-amber-600">Invited</Badge>
                    ) : user.banned ? (
                      <Badge variant="destructive">Banned</Badge>
                    ) : (
                      <Badge variant="success">Active</Badge>
                    )}
                  </div>
                </td>
                <td className="p-3">
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      className="border border-foreground h-7 px-2"
                      onClick={() => { setBanUser(user); setBanOpen(true); }}
                    >
                      {user.banned ? <ShieldOff className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border border-foreground h-7 px-2"
                      onClick={() => { setResetUser(user); setResetOpen(true); }}
                    >
                      <KeyRound className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border border-foreground h-7 px-2 hover:bg-destructive hover:text-white"
                      onClick={() => { setDeleteUser(user); setDeleteOpen(true); }}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && !loading && (
          <div className="p-8 text-center font-mono text-sm text-muted-foreground uppercase tracking-wider">
            No users found
          </div>
        )}
      </div>

      {/* Invite Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="border-2 border-foreground shadow-brutal">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase tracking-wide">Invite User</DialogTitle>
            <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Send an invite email. The user will set their own password.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1 block">Email</label>
              <Input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm(f => ({ ...f, email: e.target.value }))}
                className="border-2 border-foreground"
                placeholder="user@example.com"
              />
            </div>
            <div>
              <label className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1 block">Name</label>
              <Input
                value={inviteForm.name}
                onChange={(e) => setInviteForm(f => ({ ...f, name: e.target.value }))}
                className="border-2 border-foreground"
                placeholder="Full name"
              />
            </div>

          </div>
          <DialogFooter>
            <Button
              onClick={handleInvite}
              disabled={inviting || !inviteForm.email || !inviteForm.name}
              className="border-2 border-foreground shadow-brutal brutal-hover font-mono text-xs uppercase tracking-wider"
            >
              {inviting ? 'Sending...' : 'Send Invite'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Ban/Unban Confirmation */}
      <AlertDialog open={banOpen} onOpenChange={setBanOpen}>
        <AlertDialogContent className="border-2 border-foreground shadow-brutal">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-xl uppercase tracking-wide">
              {banUser?.banned ? 'Unban User' : 'Ban User'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {banUser?.banned
                ? `Restore access for ${banUser?.name} (${banUser?.email})?`
                : `Suspend ${banUser?.name} (${banUser?.email})? They will be unable to log in.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-2 border-foreground font-mono text-xs uppercase tracking-wider">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBan}
              disabled={banning}
              className={`border-2 border-foreground font-mono text-xs uppercase tracking-wider ${banUser?.banned ? '' : 'bg-destructive text-white hover:bg-destructive/90'}`}
            >
              {banning ? 'Processing...' : banUser?.banned ? 'Unban' : 'Ban User'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent className="border-2 border-foreground shadow-brutal">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase tracking-wide">Reset Password</DialogTitle>
            <DialogDescription className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Set a new password for {resetUser?.name} ({resetUser?.email}).
            </DialogDescription>
          </DialogHeader>
          <div>
            <label className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1 block">New Password</label>
            <Input
              type="password"
              value={resetPassword}
              onChange={(e) => setResetPassword(e.target.value)}
              className="border-2 border-foreground"
              placeholder="Min 8 characters"
            />
          </div>
          <DialogFooter>
            <Button
              onClick={handleResetPassword}
              disabled={resetting || !resetPassword}
              className="border-2 border-foreground shadow-brutal brutal-hover font-mono text-xs uppercase tracking-wider"
            >
              {resetting ? 'Resetting...' : 'Reset Password'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent className="border-2 border-foreground shadow-brutal">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-xl uppercase tracking-wide">Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Permanently delete {deleteUser?.name} ({deleteUser?.email}) and ALL their data?
              This includes {formatNumber(deleteUser?.bookmark_count)} bookmarks, collections, and AI summaries. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-2 border-foreground font-mono text-xs uppercase tracking-wider">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="border-2 border-foreground bg-destructive text-white hover:bg-destructive/90 font-mono text-xs uppercase tracking-wider"
            >
              {deleting ? 'Deleting...' : 'Delete Forever'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

// ── System Health Panel ──
const SystemHealthPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosInstance.get('/admin/system');
      setData(res.data);
    } catch (_u603_err) {
      toast.error('Failed to load system info');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const iv = setInterval(fetch, 30000);
    return () => clearInterval(iv);
  }, [fetch]);

  if (!data && loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card border-2 border-foreground p-5 shadow-brutal animate-pulse h-28" />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const InfoRow = ({ label, value }) => (
    <div className="flex justify-between items-center py-2 border-b border-foreground/10">
      <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className="font-mono text-sm font-bold">{value}</span>
    </div>
  );

  return (
    <div>
      <SectionHeader icon={Server} title="System Health" onRefresh={fetch} loading={loading} />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* MongoDB */}
        <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
          <h3 className="font-display text-lg uppercase tracking-wide mb-4 flex items-center gap-2">
            <Database className="w-4 h-4" /> MongoDB
          </h3>
          {data.mongodb ? (
            <div>
              <InfoRow label="Connections" value={`${data.mongodb.connections_current || 0} / ${data.mongodb.connections_available || 0}`} />
              <InfoRow label="Uptime" value={formatUptime(data.mongodb.uptime_seconds)} />
              {data.mongodb.opcounters && (
                <>
                  <InfoRow label="Inserts" value={formatNumber(data.mongodb.opcounters.insert)} />
                  <InfoRow label="Queries" value={formatNumber(data.mongodb.opcounters.query)} />
                  <InfoRow label="Updates" value={formatNumber(data.mongodb.opcounters.update)} />
                  <InfoRow label="Deletes" value={formatNumber(data.mongodb.opcounters.delete)} />
                </>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Unavailable</p>
          )}
        </div>

        {/* Redis */}
        <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
          <h3 className="font-display text-lg uppercase tracking-wide mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4" /> Redis
          </h3>
          {data.redis ? (
            <div>
              <InfoRow label="Memory" value={data.redis.used_memory_human || 'N/A'} />
              <InfoRow label="Clients" value={data.redis.connected_clients || 0} />
              <InfoRow label="Uptime" value={formatUptime(data.redis.uptime_in_seconds)} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Unavailable</p>
          )}
        </div>

        {/* Environment */}
        <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
          <h3 className="font-display text-lg uppercase tracking-wide mb-4 flex items-center gap-2">
            <Globe className="w-4 h-4" /> Environment
          </h3>
          <InfoRow label="Mode" value={data.environment || 'Unknown'} />
          <InfoRow label="Python" value={data.python_version || 'Unknown'} />
          {data.db_stats && (
            <>
              <InfoRow label="Data Size" value={formatBytes(data.db_stats.dataSize)} />
              <InfoRow label="Storage" value={formatBytes(data.db_stats.storageSize)} />
              <InfoRow label="Indexes" value={formatBytes(data.db_stats.indexSize)} />
            </>
          )}
        </div>

        {/* System Resources */}
        {data.system && (
          <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
            <h3 className="font-display text-lg uppercase tracking-wide mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4" /> System Resources
            </h3>
            <InfoRow label="CPU" value={`${data.system.cpu_percent?.toFixed(1) || 0}%`} />
            <InfoRow label="Memory" value={`${data.system.memory_percent?.toFixed(1) || 0}%`} />
            <InfoRow label="Memory Total" value={formatBytes(data.system.memory_total)} />
            <InfoRow label="Memory Available" value={formatBytes(data.system.memory_available)} />
            <InfoRow label="Process RSS" value={formatBytes(data.system.process_rss)} />
          </div>
        )}
      </div>

      {/* Collection Stats */}
      {data.collections && Object.keys(data.collections).length > 0 && (
        <div className="mt-6">
          <h3 className="font-display text-lg uppercase tracking-wide mb-4">Collection Breakdown</h3>
          <div className="border-2 border-foreground shadow-brutal overflow-x-auto">
            <table className="w-full">
              <thead className="bg-foreground text-background">
                <tr>
                  <th className="text-left font-mono text-xs uppercase tracking-wider p-3">Collection</th>
                  <th className="text-left font-mono text-xs uppercase tracking-wider p-3">Documents</th>
                  <th className="text-left font-mono text-xs uppercase tracking-wider p-3">Storage</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.collections).map(([name, col]) => (
                  <tr key={name} className="border-b border-foreground/20">
                    <td className="p-3 font-mono text-sm">{name}</td>
                    <td className="p-3 font-mono text-sm font-bold">{formatNumber(col.count)}</td>
                    <td className="p-3 font-mono text-sm">{formatBytes(col.size)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};



// ── Main Admin Page ──
const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'api', label: 'API Usage', icon: Zap },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'system', label: 'System', icon: Server },

];

const AdminPage = ({ _u751_onLogout }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [authorized, setAuthorized] = useState(null);

  useEffect(() => {
    const checkAdmin = async () => {
      try {
        await axiosInstance.get('/admin/overview');
        setAuthorized(true);
      } catch (err) {
        if (err.response?.status === 403) {
          toast.error('Admin access denied');
          navigate('/dashboard');
        } else if (err.response?.status === 401) {
          navigate('/auth');
        } else {
          setAuthorized(true);
        }
      }
    };
    checkAdmin();
  }, [navigate]);

  if (authorized === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-foreground border-t-primary animate-spin mx-auto mb-4" />
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Verifying admin access...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Admin Header */}
      <HardReveal direction="down">
        <header className="sticky top-0 z-40 bg-foreground text-background border-b-4 border-primary">
          <div className="px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-10 h-10 border-2 border-background bg-primary text-primary-foreground">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h1 className="font-display text-3xl font-bold tracking-wide uppercase text-background">Arivu Admin</h1>
                  <p className="font-mono text-xs uppercase tracking-wider text-background/60">System Dashboard</p>
                </div>
              </div>
              <Button
                variant="outline"
                onClick={() => navigate('/dashboard')}
                className="border-2 border-background text-background bg-transparent hover:bg-background hover:text-foreground font-mono text-xs uppercase tracking-wider"
              >
                <ArrowLeft className="w-3 h-3 mr-2" /> Dashboard
              </Button>
            </div>
          </div>
        </header>
      </HardReveal>

      {/* Tab Navigation */}
      <div className="border-b-2 border-foreground bg-card">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex gap-0 overflow-x-auto">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 px-5 py-3 font-mono text-xs uppercase tracking-wider border-b-3 transition-colors whitespace-nowrap ${
                  activeTab === id
                    ? 'border-primary text-foreground font-bold bg-primary/5'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && <OverviewPanel />}
        {activeTab === 'api' && <ApiUsagePanel />}
        {activeTab === 'users' && <UserManagementPanel />}
        {activeTab === 'system' && <SystemHealthPanel />}

      </div>
    </div>
  );
};

export default AdminPage;
