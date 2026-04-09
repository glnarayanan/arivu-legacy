import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { BookmarkIcon, PlusIcon, SearchIcon, SparklesIcon as _u9_SparklesIcon, CheckSquare, Square, Trash2, CheckCircle, Circle, BookOpen, Grid3x3, List, Clock, Globe } from 'lucide-react';
import { motion } from 'framer-motion';
import KeyboardShortcutsModal from '../components/KeyboardShortcutsModal';
import BookmarkCard from '../components/BookmarkCard';
import { StaggerContainer, StaggerItem, HardReveal } from '../components/motion/PageOrchestrator';
import UserMenu from '../components/UserMenu';
import Sidebar from '../components/Sidebar';
import MemoryJogger from '../components/MemoryJogger';
import { BrutalConfetti, SuccessToast, MilestoneToast } from '../components/delight';
import { checkBookmarkCountMilestones, markMilestoneReached } from '../utils/milestones';
import { WelcomeModal, EmptyStateGuide, FirstBookmarkGuide } from '../components/onboarding';
import BookmarkCardSkeleton from '../components/BookmarkCardSkeleton';
import ErrorMessage from '../components/ErrorMessage';

const DashboardPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [bookmarks, setBookmarks] = useState([]);
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [filterCollection, setFilterCollection] = useState('');
  const [newBookmarkUrl, setNewBookmarkUrl] = useState('');
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [allTags, setAllTags] = useState([]);
  const [_u37_allDomains, setAllDomains] = useState([]);
  const [selectedBookmarks, setSelectedBookmarks] = useState([]);
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [readFilter, setReadFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [viewMode, setViewMode] = useState('list');
  const [agedCount, setAgedCount] = useState(0);
  const [showAgedOnly, setShowAgedOnly] = useState(false);
  const [resurfacingSuggestions, setResurfacingSuggestions] = useState([]);
  const [memoryJogger, setMemoryJogger] = useState(null);
  const [memoryJoggerDismissed, setMemoryJoggerDismissed] = useState(false);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [showConfetti, setShowConfetti] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [firstBookmarkId, setFirstBookmarkId] = useState(null);

  // Check if user should see welcome modal (first time)
  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem('arivu_welcome_completed');
    if (!hasSeenWelcome) {
      setShowWelcome(true);
    }
  }, []);

  const fetchBookmarks = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (filterTag) params.append('tag', filterTag);
      if (filterDomain) params.append('domain', filterDomain);
      if (filterCollection) params.append('collection_id', filterCollection);
      if (readFilter !== 'all') params.append('read_status', readFilter);
      if (sourceFilter !== 'all') params.append('source', sourceFilter);
      if (sortBy) params.append('sort_by', sortBy);

      const response = await axiosInstance.get(`/bookmarks?${params.toString()}`);
      setBookmarks(response.data);

      const tags = new Set();
      const domains = new Set();
      response.data.forEach(b => {
        if (b.ai_summary?.suggested_tags) {
          b.ai_summary.suggested_tags.forEach(tag => tags.add(tag));
        }
        if (b.domain) domains.add(b.domain);
      });
      setAllTags([...tags]);
      setAllDomains([...domains]);
    } catch (err) {
      const message = err.response?.status === 0
        ? 'Unable to connect. Check your internet connection.'
        : err.response?.data?.detail || 'Failed to load bookmarks';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterTag, filterDomain, filterCollection, readFilter, sourceFilter, sortBy]);

  const fetchCollections = useCallback(async () => {
    try {
      const response = await axiosInstance.get(`/collections`);
      setCollections(response.data);
    } catch (_u103_error) {
      console.error('Failed to fetch collections');
    }
  }, []);

  const fetchAgedCount = useCallback(async () => {
    try {
      const response = await axiosInstance.get(`/bookmarks/aged?min_days=30&limit=100`);
      setAgedCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch aged count:', error);
    }
  }, []);

  const fetchResurfacing = useCallback(async () => {
    try {
      const response = await axiosInstance.get(`/resurfacing?limit=3`);
      setResurfacingSuggestions(response.data.suggestions || []);
    } catch (error) {
      console.error('Failed to fetch resurfacing suggestions:', error);
    }
  }, []);

  const fetchMemoryJogger = useCallback(async () => {
    const dismissed = localStorage.getItem('memoryJoggerDismissed');
    if (dismissed === new Date().toDateString()) {
      setMemoryJoggerDismissed(true);
      return;
    }
    try {
      const response = await axiosInstance.get('/memory-jogger');
      if (response.data.has_memory) {
        setMemoryJogger(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch memory jogger:', error);
    }
  }, []);

  const handleMemoryRevisit = async (bookmarkId) => {
    try {
      await axiosInstance.post(`/bookmarks/${bookmarkId}/accessed`, {}, { params: { source: 'memory_jogger' } });
    } catch (error) {
      console.error('Failed to track memory jogger access:', error);
    }
  };

  const handleMemoryDismiss = async (bookmarkId) => {
    try {
      await axiosInstance.post('/memory-jogger/dismiss', { bookmark_id: bookmarkId });
      localStorage.setItem('memoryJoggerDismissed', new Date().toDateString());
      setMemoryJoggerDismissed(true);
      setMemoryJogger(null);
    } catch (error) {
      console.error('Failed to dismiss memory jogger:', error);
    }
  };

  const handleResurfacingSnooze = async (bookmarkId, days = 7) => {
    try {
      await axiosInstance.post(`/resurfacing/${bookmarkId}/snooze`, { days });
      toast.success(`Snoozed for ${days} days`);
      setResurfacingSuggestions(prev => prev.filter(s => s.id !== bookmarkId));
    } catch (_u166_error) {
      toast.error('Failed to snooze bookmark');
    }
  };

  const handleResurfacingArchive = async (bookmarkId) => {
    try {
      await axiosInstance.post(`/resurfacing/${bookmarkId}/archive`);
      toast.success('Removed from resurfacing');
      setResurfacingSuggestions(prev => prev.filter(s => s.id !== bookmarkId));
    } catch (_u176_error) {
      toast.error('Failed to archive bookmark');
    }
  };

  const handleResurfacingReadAgain = async (bookmarkId) => {
    try {
      await axiosInstance.post(`/bookmarks/${bookmarkId}/accessed`, {}, { params: { source: 'resurfacing' } });
      setResurfacingSuggestions(prev => prev.filter(s => s.id !== bookmarkId));
    } catch (error) {
      console.error('Failed to track access:', error);
    }
  };

  useEffect(() => {
    fetchBookmarks();
    fetchCollections();
    fetchAgedCount();
    fetchResurfacing();
    fetchMemoryJogger();
  }, [fetchBookmarks, fetchCollections, fetchAgedCount, fetchResurfacing, fetchMemoryJogger]);

  useEffect(() => {
    const hasPendingAI = bookmarks.some(b => b.ai_summary?.processing_status === 'pending');
    if (hasPendingAI) {
      const interval = setInterval(() => {
        fetchBookmarks();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [bookmarks, fetchBookmarks]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') {
          e.target.blur();
          setDialogOpen(false);
          setShortcutsOpen(false);
        }
        return;
      }

      if (e.key === 'q' || e.key === 'Q') {
        e.preventDefault();
        setDialogOpen(true);
      }
      if (e.key === '/' || e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        document.querySelector('[data-testid="search-input"]')?.focus();
      }
      if (e.key === '?') {
        e.preventDefault();
        setShortcutsOpen(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.querySelector('[data-testid="search-input"]')?.focus();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        window.print();
      }
      if (e.key === 'Escape') {
        setDialogOpen(false);
        setShortcutsOpen(false);
        setSelectedIndex(-1);
      }

      if (bookmarks.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, bookmarks.length - 1));
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, -1));
        }
        if (e.key === 'Enter' && selectedIndex >= 0) {
          e.preventDefault();
          navigate(`/bookmark/${bookmarks[selectedIndex].id}`);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [bookmarks, selectedIndex, navigate]);

  const handleAddBookmark = async (e) => {
    e.preventDefault();
    if (!newBookmarkUrl) return;

    setAddingBookmark(true);
    try {
      const response = await axiosInstance.post(`/bookmarks`, { url: newBookmarkUrl });
      setNewBookmarkUrl('');
      setDialogOpen(false);

      const savedBookmark = response.data.bookmark;

      // Check if this is the first bookmark ever saved
      const isFirstBookmark = !localStorage.getItem('arivu_first_bookmark_saved');

      if (isFirstBookmark) {
        // Mark first bookmark as saved
        localStorage.setItem('arivu_first_bookmark_saved', 'true');

        // Show confetti celebration
        setShowConfetti(true);

        // Set first bookmark ID to show guide
        setFirstBookmarkId(savedBookmark.id);

        // Show special first bookmark toast
        toast.custom((t) => (
          <SuccessToast
            message="First bookmark saved! Your second brain begins."
            action={{
              label: 'View',
              onClick: () => {
                toast.dismiss(t);
                navigate(`/bookmark/${savedBookmark.id}`);
              }
            }}
            onClose={() => toast.dismiss(t)}
          />
        ), { duration: 5000 });
      } else {
        // Show custom toast with animated checkmark for subsequent bookmarks
        toast.custom((t) => (
          <SuccessToast
            message="Saved!"
            action={{
              label: 'View',
              onClick: () => {
                toast.dismiss(t);
                navigate(`/bookmark/${savedBookmark.id}`);
              }
            }}
            onClose={() => toast.dismiss(t)}
          />
        ), { duration: 3000 });
      }

      // Refresh bookmarks list after a delay for AI to start processing
      // and check for milestone achievements
      setTimeout(async () => {
        await fetchBookmarks();

        // Check for bookmark count milestones
        // We need to get the updated count after the new bookmark is added
        try {
          const _u328_countResponse = await axiosInstance.get('/bookmarks?limit=1');
          // The backend returns paginated results, but we can estimate count from the current bookmarks length + 1
          // Or better, check the current bookmarks array after fetch
          const currentCount = bookmarks.length + 1; // +1 for the just-added bookmark
          const milestoneToTrigger = checkBookmarkCountMilestones(currentCount);

          if (milestoneToTrigger) {
            markMilestoneReached(milestoneToTrigger, currentCount);
            toast.custom((t) => (
              <MilestoneToast
                milestone={milestoneToTrigger}
                onDismiss={() => toast.dismiss(t)}
              />
            ), { duration: 6000 });
          }
        } catch (err) {
          console.error('Failed to check milestones:', err);
        }
      }, 2000);
    } catch (_u347_error) {
      toast.error('Failed to save bookmark');
    } finally {
      setAddingBookmark(false);
    }
  };

  const handleDeleteBookmark = async (bookmarkId) => {
    try {
      await axiosInstance.delete(`/bookmarks/${bookmarkId}`);
      toast.success('Bookmark deleted');
      fetchBookmarks();
    } catch (_u359_error) {
      toast.error('Failed to delete bookmark');
    }
  };

  const _u364_handleExportBookmarks = async () => {
    try {
      const response = await axiosInstance.get(`/bookmarks/export`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `arivu_bookmarks_${new Date().toISOString().split('T')[0]}.html`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Bookmarks exported successfully!');
    } catch (_u377_error) {
      toast.error('Failed to export bookmarks');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedBookmarks.length === 0) return;
    if (!window.confirm(`Delete ${selectedBookmarks.length} bookmarks?`)) return;

    try {
      await axiosInstance.post(`/bookmarks/bulk-delete`, selectedBookmarks);
      toast.success(`Deleted ${selectedBookmarks.length} bookmarks`);
      setSelectedBookmarks([]);
      setBulkMode(false);
      fetchBookmarks();
    } catch (_u392_error) {
      toast.error('Failed to delete bookmarks');
    }
  };

  const handleBulkMarkRead = async (status) => {
    if (selectedBookmarks.length === 0) return;

    try {
      await axiosInstance.post(`/bookmarks/bulk-mark-read`, {
        bookmark_ids: selectedBookmarks,
        read_status: status
      });
      toast.success(`Marked ${selectedBookmarks.length} as ${status ? 'read' : 'unread'}`);
      setSelectedBookmarks([]);
      setBulkMode(false);
      fetchBookmarks();
    } catch (_u409_error) {
      toast.error('Failed to update bookmarks');
    }
  };

  const toggleBookmarkSelection = (bookmarkId) => {
    setSelectedBookmarks(prev =>
      prev.includes(bookmarkId)
        ? prev.filter(id => id !== bookmarkId)
        : [...prev, bookmarkId]
    );
  };

  const selectAllBookmarks = () => {
    setSelectedBookmarks(bookmarks.map(b => b.id));
  };

  const deselectAllBookmarks = () => {
    setSelectedBookmarks([]);
  };

  // Get display title for the current filter state
  const getDisplayTitle = () => {
    if (filterCollection) {
      const col = collections.find(c => c.id === filterCollection);
      return col?.name || 'Collection';
    }
    if (filterTag) {
      return `#${filterTag}`;
    }
    return 'All Bookmarks';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <HardReveal direction="down">
          <div className="px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground shadow-brutal">
                  <BookmarkIcon className="w-5 h-5" />
                </div>
                <h1 className="font-display text-3xl font-bold tracking-wide uppercase">Arivu</h1>
              </div>

              <div className="flex items-center gap-3">
                {/* Search Bar in Header */}
                <div className="relative hidden md:block w-80">
                  <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    data-testid="search-input"
                    type="text"
                    placeholder="SEARCH..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    maxLength={200}
                    className="h-10 rounded-none border-2 border-foreground bg-background pl-10 text-sm shadow-none focus-visible:ring-0 font-mono placeholder:text-muted-foreground"
                  />
                </div>

                <UserMenu onLogout={onLogout} />
              </div>
            </div>
          </div>
        </HardReveal>
      </header>

      {/* Main Layout with Sidebar */}
      <div className="flex">
        {/* Sidebar */}
        <Sidebar
          collections={collections}
          allTags={allTags}
          filterTag={filterTag}
          setFilterTag={setFilterTag}
          filterCollection={filterCollection}
          setFilterCollection={setFilterCollection}
          onCreateCollection={fetchCollections}
          resurfacingSuggestions={resurfacingSuggestions}
          onResurfacingReadAgain={handleResurfacingReadAgain}
          onResurfacingSnooze={handleResurfacingSnooze}
          onResurfacingArchive={handleResurfacingArchive}
          agedCount={agedCount}
          onViewAged={() => setShowAgedOnly(true)}
          bookmarkCount={bookmarks.length}
          onOpenAddBookmark={() => setDialogOpen(true)}
        />

        {/* Main Content */}
        <main className="flex-1 min-w-0 px-6 py-6">
          {/* Mobile Search */}
          <div className="md:hidden mb-4">
            <div className="relative">
              <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-foreground" />
              <Input
                data-testid="search-input-mobile"
                type="text"
                placeholder="SEARCH BOOKMARKS..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                maxLength={200}
                className="h-12 rounded-none border-2 border-foreground bg-background px-4 pl-12 text-base shadow-none focus-visible:ring-0 font-mono placeholder:text-muted-foreground"
              />
            </div>
          </div>

          {/* Content Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-heading text-xl font-bold uppercase tracking-wide">
              {getDisplayTitle()}
            </h2>

            <div className="flex items-center gap-3">
              {/* View Mode Toggle */}
              <div className="flex gap-1 p-1 bg-background border-2 border-foreground rounded-none">
                <Button
                  data-testid="list-view-btn"
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  className={`h-8 px-3 rounded-none ${viewMode === 'list' ? 'bg-foreground text-background' : 'hover:bg-muted'}`}
                  onClick={() => setViewMode('list')}
                >
                  <List className="w-4 h-4" />
                </Button>
                <Button
                  data-testid="grid-view-btn"
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  className={`h-8 px-3 rounded-none ${viewMode === 'grid' ? 'bg-foreground text-background' : 'hover:bg-muted'}`}
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3x3 className="w-4 h-4" />
                </Button>
              </div>

              {/* Sort By */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger data-testid="sort-filter" className="w-[140px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <Clock className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="created_at">By Date</SelectItem>
                  <SelectItem value="reading_time">Reading Time</SelectItem>
                  <SelectItem value="title">Title</SelectItem>
                </SelectContent>
              </Select>

              {/* Read Filter */}
              <Select value={readFilter} onValueChange={setReadFilter}>
                <SelectTrigger data-testid="read-filter" className="w-[140px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <BookOpen className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="unread">Unread</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                </SelectContent>
              </Select>

              {/* Source Filter */}
              <Select value={sourceFilter} onValueChange={setSourceFilter}>
                <SelectTrigger data-testid="source-filter" className="w-[140px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <Globe className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Source" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="web">Web Only</SelectItem>
                  <SelectItem value="x">X Only</SelectItem>
                </SelectContent>
              </Select>

              {/* Bulk Mode Toggle */}
              <Button
                data-testid="bulk-mode-btn"
                variant={bulkMode ? "default" : "outline"}
                size="sm"
                className={`rounded-none border-2 border-foreground ${bulkMode ? 'bg-foreground text-background' : 'bg-background hover:bg-muted'}`}
                onClick={() => setBulkMode(!bulkMode)}
              >
                {bulkMode ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
              </Button>
            </div>
          </div>

          {/* Clear Filters */}
          {(filterTag || filterDomain || filterCollection || readFilter !== 'all' || sourceFilter !== 'all' || sortBy !== 'created_at') && (
            <div className="mb-4">
              <Button
                data-testid="clear-filters-btn"
                variant="ghost"
                size="sm"
                className="rounded-none border-2 border-transparent hover:border-red-500 hover:text-red-500 font-mono uppercase text-xs tracking-wider"
                onClick={() => {
                  setFilterTag('');
                  setFilterDomain('');
                  setFilterCollection('');
                  setReadFilter('all');
                  setSourceFilter('all');
                  setSortBy('created_at');
                }}
              >
                Clear filters
              </Button>
            </div>
          )}

          {/* Memory Jogger - prominent single bookmark reminder */}
          {memoryJogger && !memoryJoggerDismissed && (
            <MemoryJogger
              data={memoryJogger}
              onRevisit={handleMemoryRevisit}
              onDismiss={handleMemoryDismiss}
            />
          )}

          {/* Aged bookmarks filter active indicator */}
          {showAgedOnly && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-3 bg-amber-50 border-2 border-foreground flex items-center justify-between"
            >
              <div className="flex items-center gap-2 text-sm font-mono text-amber-700">
                <span className="uppercase tracking-wider">Showing stale bookmarks (30+ days inactive)</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAgedOnly(false)}
                className="rounded-none border-2 border-transparent hover:border-amber-700 text-amber-700 font-mono uppercase text-xs"
              >
                Clear Filter
              </Button>
            </motion.div>
          )}

          {bulkMode && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mb-6 p-4 bg-card border-2 border-foreground"
            >
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-mono uppercase tracking-wider font-medium">
                    {selectedBookmarks.length} selected
                  </span>
                  <div className="flex gap-2">
                    <Button
                      data-testid="select-all-btn"
                      variant="outline"
                      size="sm"
                      className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase text-xs"
                      onClick={selectAllBookmarks}
                      disabled={selectedBookmarks.length === bookmarks.length}
                    >
                      Select All
                    </Button>
                    <Button
                      data-testid="deselect-all-btn"
                      variant="outline"
                      size="sm"
                      className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase text-xs"
                      onClick={deselectAllBookmarks}
                      disabled={selectedBookmarks.length === 0}
                    >
                      Deselect All
                    </Button>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    data-testid="bulk-mark-read-btn"
                    variant="outline"
                    size="sm"
                    className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase text-xs"
                    onClick={() => handleBulkMarkRead(true)}
                    disabled={selectedBookmarks.length === 0}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark Read
                  </Button>
                  <Button
                    data-testid="bulk-mark-unread-btn"
                    variant="outline"
                    size="sm"
                    className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase text-xs"
                    onClick={() => handleBulkMarkRead(false)}
                    disabled={selectedBookmarks.length === 0}
                  >
                    <Circle className="w-4 h-4 mr-2" />
                    Mark Unread
                  </Button>
                  <Button
                    data-testid="bulk-delete-btn"
                    variant="destructive"
                    size="sm"
                    className="rounded-none border-2 border-foreground bg-destructive text-destructive-foreground hover:bg-destructive/90 font-mono uppercase text-xs"
                    onClick={handleBulkDelete}
                    disabled={selectedBookmarks.length === 0}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Selected
                  </Button>
                </div>
              </div>
            </motion.div>
          )}

          {loading ? (
            <div
              className={viewMode === 'grid'
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                : "space-y-3"
              }
            >
              {[...Array(6)].map((_, i) => (
                <BookmarkCardSkeleton key={i} viewMode={viewMode} />
              ))}
            </div>
          ) : error ? (
            <ErrorMessage
              title="Failed to load bookmarks"
              message={error}
              onRetry={() => {
                setLoading(true);
                fetchBookmarks();
              }}
              retrying={loading}
            />
          ) : bookmarks.length === 0 ? (
            searchQuery || filterTag || filterDomain || filterCollection || readFilter !== 'all' ? (
              <div className="text-center py-20 border-2 border-dashed border-muted-foreground/20 p-8">
                <SearchIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                <h2 className="font-display text-2xl font-semibold mb-2 uppercase tracking-wide">No results found</h2>
                <p className="text-muted-foreground mb-6 font-mono text-sm">
                  {searchQuery
                    ? `No bookmarks match "${searchQuery.length > 30 ? searchQuery.slice(0, 30) + '...' : searchQuery}"`
                    : 'No bookmarks match your current filters'
                  }
                </p>
                <Button
                  variant="outline"
                  size="lg"
                  className="rounded-none border-2 border-foreground bg-background hover:bg-muted font-mono uppercase tracking-wider"
                  onClick={() => {
                    setSearchQuery('');
                    setFilterTag('');
                    setFilterDomain('');
                    setFilterCollection('');
                    setReadFilter('all');
                  }}
                >
                  Clear all filters
                </Button>
              </div>
            ) : (
              <EmptyStateGuide
                type="bookmarks"
                onPrimaryAction={() => setDialogOpen(true)}
              />
            )
          ) : (
            <StaggerContainer
              className={viewMode === 'grid'
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                : "space-y-3"
              }
            >
              {bookmarks
                .filter(bookmark => {
                  if (!showAgedOnly) return true;
                  const lastAccessed = new Date(bookmark.last_accessed || bookmark.created_at);
                  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
                  return lastAccessed < thirtyDaysAgo;
                })
                .map((bookmark, index) => (
                  <StaggerItem key={bookmark.id}>
                    <BookmarkCard
                      bookmark={bookmark}
                      onDelete={handleDeleteBookmark}
                      onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                      bulkMode={bulkMode}
                      isSelected={selectedBookmarks.includes(bookmark.id)}
                      onToggleSelect={() => toggleBookmarkSelection(bookmark.id)}
                      isHighlighted={selectedIndex === index}
                      viewMode={viewMode}
                    />
                  </StaggerItem>
                ))}
            </StaggerContainer>
          )}
        </main>
      </div>

      {/* FAB for adding bookmarks */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button
            data-testid="add-bookmark-fab"
            size="lg"
            className="fixed bottom-6 right-6 md:right-6 rounded-none w-14 h-14 bg-primary text-primary-foreground border-2 border-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all z-40 p-0"
          >
            <PlusIcon className="w-6 h-6" />
          </Button>
        </DialogTrigger>
        <DialogContent className="rounded-none border-2 border-foreground shadow-brutal" aria-describedby="add-bookmark-description-fab">
          <DialogHeader>
            <DialogTitle className="font-heading font-bold uppercase">Add Bookmark</DialogTitle>
            <p id="add-bookmark-description-fab" className="text-sm text-muted-foreground sr-only">
              Enter a URL to save and get AI-powered summaries
            </p>
          </DialogHeader>
          <form onSubmit={handleAddBookmark} className="space-y-4">
            <Input
              data-testid="bookmark-url-input-fab"
              type="url"
              placeholder="HTTPS://EXAMPLE.COM/ARTICLE"
              value={newBookmarkUrl}
              onChange={(e) => setNewBookmarkUrl(e.target.value)}
              required
              maxLength={2048}
              className="rounded-none border-2 border-foreground font-mono"
              autoFocus
            />
            <Button
              data-testid="save-bookmark-btn-fab"
              type="submit"
              className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
              disabled={addingBookmark}
            >
              {addingBookmark ? 'SAVING...' : 'SAVE BOOKMARK'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      <KeyboardShortcutsModal open={shortcutsOpen} onOpenChange={setShortcutsOpen} />

      {/* First bookmark celebration confetti */}
      <BrutalConfetti
        active={showConfetti}
        onComplete={() => setShowConfetti(false)}
      />

      {/* Welcome modal for first-time users */}
      {showWelcome && (
        <WelcomeModal
          onComplete={() => setShowWelcome(false)}
        />
      )}

      {/* First bookmark guide */}
      {firstBookmarkId && (
        <FirstBookmarkGuide
          bookmarkId={firstBookmarkId}
          onDismiss={() => setFirstBookmarkId(null)}
        />
      )}
    </div>
  );
};

export default DashboardPage;
