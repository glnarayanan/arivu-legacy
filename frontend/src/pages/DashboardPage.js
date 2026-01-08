import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { BookmarkIcon, PlusIcon, SearchIcon, FilterIcon, SparklesIcon, FolderIcon, LogOutIcon, CopyIcon, UploadIcon, DownloadIcon, CheckSquare, Square, Trash2, CheckCircle, Circle, BookOpen, Grid3x3, List, Archive, Clock, NetworkIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import KeyboardShortcutsModal from '../components/KeyboardShortcutsModal';
import BookmarkCard from '../components/BookmarkCard';
import AgedBookmarksBanner from '../components/AgedBookmarksBanner';
import { StaggerContainer, StaggerItem, HardReveal } from '../components/motion/PageOrchestrator';

const API = '/api';

const DashboardPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [bookmarks, setBookmarks] = useState([]);
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [filterCollection, setFilterCollection] = useState('');
  const [newBookmarkUrl, setNewBookmarkUrl] = useState('');
  const [addingBookmark, setAddingBookmark] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [collectionDialogOpen, setCollectionDialogOpen] = useState(false);
  const [allTags, setAllTags] = useState([]);
  const [allDomains, setAllDomains] = useState([]);
  const [selectedBookmarks, setSelectedBookmarks] = useState([]);
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [readFilter, setReadFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [viewMode, setViewMode] = useState('list');
  const [agedCount, setAgedCount] = useState(0);
  const [showAgedOnly, setShowAgedOnly] = useState(false);

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const fetchBookmarks = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (filterTag) params.append('tag', filterTag);
      if (filterDomain) params.append('domain', filterDomain);
      if (filterCollection) params.append('collection_id', filterCollection);
      if (readFilter !== 'all') params.append('read_status', readFilter);
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
    } catch (error) {
      toast.error('Failed to fetch bookmarks');
    } finally {
      setLoading(false);
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await axiosInstance.get(`/collections`);
      setCollections(response.data);
    } catch (error) {
      console.error('Failed to fetch collections');
    }
  };

  const fetchAgedCount = async () => {
    try {
      const response = await axiosInstance.get(`/bookmarks/aged?min_days=30&limit=100`);
      setAgedCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch aged count:', error);
    }
  };

  useEffect(() => {
    fetchBookmarks();
    fetchCollections();
    fetchAgedCount();
  }, [searchQuery, filterTag, filterDomain, filterCollection, readFilter, sortBy]);

  useEffect(() => {
    const hasPendingAI = bookmarks.some(b => b.ai_summary?.processing_status === 'pending');
    if (hasPendingAI) {
      const interval = setInterval(() => {
        fetchBookmarks();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [bookmarks]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') {
          e.target.blur();
          setDialogOpen(false);
          setCollectionDialogOpen(false);
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
        setCollectionDialogOpen(false);
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
      await axiosInstance.post(`/bookmarks`, { url: newBookmarkUrl });
      toast.success('Bookmark saved! AI is processing summaries...');
      setNewBookmarkUrl('');
      setDialogOpen(false);
      setTimeout(() => fetchBookmarks(), 2000);
    } catch (error) {
      toast.error('Failed to save bookmark');
    } finally {
      setAddingBookmark(false);
    }
  };

  const handleCreateCollection = async (e) => {
    e.preventDefault();
    if (!newCollectionName) return;

    try {
      await axiosInstance.post(`/collections`, { name: newCollectionName });
      toast.success('Collection created!');
      setNewCollectionName('');
      setCollectionDialogOpen(false);
      fetchCollections();
    } catch (error) {
      toast.error('Failed to create collection');
    }
  };

  const handleDeleteBookmark = async (bookmarkId) => {
    try {
      await axiosInstance.delete(`/bookmarks/${bookmarkId}`);
      toast.success('Bookmark deleted');
      fetchBookmarks();
    } catch (error) {
      toast.error('Failed to delete bookmark');
    }
  };

  const handleExportBookmarks = async () => {
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
    } catch (error) {
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
    } catch (error) {
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
    } catch (error) {
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

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <HardReveal direction="down">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground shadow-brutal">
                  <BookmarkIcon className="w-5 h-5" />
                </div>
                <h1 className="font-display text-3xl font-bold tracking-wide uppercase">Arivu</h1>
              </div>
              <div className="flex items-center gap-2">
                <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                  <DialogTrigger asChild>
                    <Button
                      data-testid="add-bookmark-header-btn"
                      size="sm"
                      className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                    >
                      <PlusIcon className="w-4 h-4 mr-2" />
                      ADD BOOKMARK
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="rounded-none border-2 border-foreground shadow-brutal" aria-describedby="add-bookmark-header-description">
                    <DialogHeader>
                      <DialogTitle className="font-heading font-bold uppercase tracking-wider">Add Bookmark</DialogTitle>
                      <p id="add-bookmark-header-description" className="text-sm text-muted-foreground sr-only">
                        Enter a URL to save and get AI-powered summaries
                      </p>
                    </DialogHeader>
                    <form onSubmit={handleAddBookmark} className="space-y-4">
                      <Input
                        data-testid="bookmark-url-input-header"
                        type="url"
                        placeholder="HTTPS://EXAMPLE.COM/ARTICLE"
                        value={newBookmarkUrl}
                        onChange={(e) => setNewBookmarkUrl(e.target.value)}
                        required
                        className="rounded-none border-2 border-foreground font-mono"
                        autoFocus
                      />
                      <Button
                        data-testid="save-bookmark-btn-header"
                        type="submit"
                        className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                        disabled={addingBookmark}
                      >
                        {addingBookmark ? 'SAVING...' : 'SAVE BOOKMARK'}
                      </Button>
                    </form>
                  </DialogContent>
                </Dialog>
                <Button
                  data-testid="import-btn"
                  variant="ghost"
                  size="sm"
                  className="rounded-none border-2 border-transparent hover:border-foreground hover:bg-muted font-mono uppercase text-xs tracking-wider"
                  onClick={() => navigate('/imports')}
                >
                  <UploadIcon className="w-4 h-4 mr-2" />
                  Imports
                </Button>
                <Button
                  data-testid="export-btn"
                  variant="ghost"
                  size="sm"
                  className="rounded-none border-2 border-transparent hover:border-foreground hover:bg-muted font-mono uppercase text-xs tracking-wider"
                  onClick={handleExportBookmarks}
                >
                  <DownloadIcon className="w-4 h-4 mr-2" />
                  Export
                </Button>
                <Button
                  data-testid="duplicates-btn"
                  variant="ghost"
                  size="sm"
                  className="rounded-none border-2 border-transparent hover:border-foreground hover:bg-muted font-mono uppercase text-xs tracking-wider"
                  onClick={() => navigate('/duplicates')}
                >
                  <CopyIcon className="w-4 h-4 mr-2" />
                  Duplicates
                </Button>
                <Button
                  data-testid="knowledge-graph-btn"
                  variant="ghost"
                  size="sm"
                  className="rounded-none border-2 border-transparent hover:border-foreground hover:bg-muted font-mono uppercase text-xs tracking-wider"
                  onClick={() => navigate('/knowledge-graph')}
                >
                  <NetworkIcon className="w-4 h-4 mr-2" />
                  Knowledge Graph
                </Button>
                <Button
                  data-testid="logout-btn"
                  variant="ghost"
                  size="sm"
                  className="rounded-none border-2 border-transparent hover:border-foreground hover:bg-muted font-mono uppercase text-xs tracking-wider"
                  onClick={onLogout}
                >
                  <LogOutIcon className="w-4 h-4 mr-2" />
                  Log Out
                </Button>
              </div>
            </div>
          </div>
        </HardReveal>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8 space-y-4">
          <HardReveal direction="left" delay={0.1}>
            <div className="relative">
              <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-foreground" />
              <Input
                data-testid="search-input"
                type="text"
                placeholder="SEARCH BOOKMARKS, CONTENT, OR NOTES..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-14 rounded-none border-2 border-foreground bg-background px-4 pl-12 text-base shadow-none focus-visible:ring-0 font-mono placeholder:text-muted-foreground"
              />
            </div>
          </HardReveal>

          <HardReveal direction="left" delay={0.2}>
            <div className="flex flex-wrap gap-3 items-center">
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

              <Button
                data-testid="bulk-mode-btn"
                variant={bulkMode ? "default" : "outline"}
                size="sm"
                className={`rounded-none border-2 border-foreground ${bulkMode ? 'bg-foreground text-background' : 'bg-background hover:bg-muted'}`}
                onClick={() => setBulkMode(!bulkMode)}
              >
                {bulkMode ? <CheckSquare className="w-4 h-4 mr-2" /> : <Square className="w-4 h-4 mr-2" />}
                <span className="font-mono uppercase text-xs tracking-wider">Bulk Select</span>
              </Button>

              <Select value={readFilter} onValueChange={setReadFilter}>
                <SelectTrigger data-testid="read-filter" className="w-[180px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <BookOpen className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Reading status" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="all">All articles</SelectItem>
                  <SelectItem value="unread">Unread only</SelectItem>
                  <SelectItem value="read">Read only</SelectItem>
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger data-testid="sort-filter" className="w-[180px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <Clock className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="created_at">Date added</SelectItem>
                  <SelectItem value="reading_time">Reading time</SelectItem>
                  <SelectItem value="title">Title</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterTag} onValueChange={setFilterTag}>
                <SelectTrigger data-testid="tag-filter" className="w-[180px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <FilterIcon className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Filter by tag" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="_clear">All tags</SelectItem>
                  {allTags.map(tag => (
                    <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={filterDomain} onValueChange={setFilterDomain}>
                <SelectTrigger data-testid="domain-filter" className="w-[180px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <SelectValue placeholder="Filter by domain" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="_clear">All domains</SelectItem>
                  {allDomains.map(domain => (
                    <SelectItem key={domain} value={domain}>{domain}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={filterCollection} onValueChange={setFilterCollection}>
                <SelectTrigger data-testid="collection-filter" className="w-[200px] rounded-none border-2 border-foreground shadow-none font-mono text-xs uppercase tracking-wider bg-background">
                  <FolderIcon className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Filter by collection" />
                </SelectTrigger>
                <SelectContent className="rounded-none border-2 border-foreground shadow-brutal">
                  <SelectItem value="_clear">All collections</SelectItem>
                  {collections.map(col => (
                    <SelectItem key={col.id} value={col.id}>{col.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Dialog open={collectionDialogOpen} onOpenChange={setCollectionDialogOpen}>
                <DialogTrigger asChild>
                  <Button data-testid="new-collection-btn" variant="outline" size="sm" className="rounded-none border-2 border-foreground shadow-none hover:bg-muted font-mono uppercase text-xs tracking-wider">
                    <FolderIcon className="w-4 h-4 mr-2" />
                    New Collection
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-none border-2 border-foreground shadow-brutal" aria-describedby="create-collection-description">
                  <DialogHeader>
                    <DialogTitle className="font-heading font-bold uppercase">Create Collection</DialogTitle>
                    <p id="create-collection-description" className="text-sm text-muted-foreground sr-only">
                      Create a new collection to organize your bookmarks
                    </p>
                  </DialogHeader>
                  <form onSubmit={handleCreateCollection} className="space-y-4">
                    <Input
                      data-testid="collection-name-input"
                      placeholder="COLLECTION NAME"
                      value={newCollectionName}
                      onChange={(e) => setNewCollectionName(e.target.value)}
                      className="rounded-none border-2 border-foreground font-mono"
                      autoFocus
                    />
                    <Button data-testid="create-collection-btn" type="submit" className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                      CREATE
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>

              {(filterTag || filterDomain || filterCollection || readFilter !== 'all' || sortBy !== 'created_at') && (
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
                    setSortBy('created_at');
                  }}
                >
                  Clear filters
                </Button>
              )}
            </div>
          </HardReveal>
        </div>

        <AgedBookmarksBanner
          agedCount={agedCount}
          onViewAged={() => setShowAgedOnly(true)}
        />

        {showAgedOnly && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 p-3 bg-card border-2 border-foreground flex items-center justify-between"
          >
            <div className="flex items-center gap-2 text-sm font-mono text-amber-700">
              <Archive className="w-4 h-4" />
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
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary rounded-none"></div>
          </div>
        ) : bookmarks.length === 0 ? (
          <div className="text-center py-20 border-2 border-dashed border-muted-foreground/20 p-8">
            <SparklesIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="font-display text-2xl font-semibold mb-2 uppercase tracking-wide">No bookmarks yet</h2>
            <p className="text-muted-foreground mb-6 font-mono text-sm">Start saving web pages and let AI organize them for you</p>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="add-first-bookmark-btn" size="lg" className="rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                  <PlusIcon className="w-5 h-5 mr-2" />
                  ADD YOUR FIRST BOOKMARK
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-none border-2 border-foreground shadow-brutal" aria-describedby="add-bookmark-description">
                <DialogHeader>
                  <DialogTitle className="font-heading font-bold uppercase">Add Bookmark</DialogTitle>
                  <p id="add-bookmark-description" className="text-sm text-muted-foreground sr-only">
                    Enter a URL to save and get AI-powered summaries
                  </p>
                </DialogHeader>
                <form onSubmit={handleAddBookmark} className="space-y-4">
                  <Input
                    data-testid="bookmark-url-input"
                    type="url"
                    placeholder="HTTPS://EXAMPLE.COM/ARTICLE"
                    value={newBookmarkUrl}
                    onChange={(e) => setNewBookmarkUrl(e.target.value)}
                    required
                    className="rounded-none border-2 border-foreground font-mono"
                    autoFocus
                  />
                  <Button
                    data-testid="save-bookmark-btn"
                    type="submit"
                    className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                    disabled={addingBookmark}
                  >
                    {addingBookmark ? 'SAVING...' : 'SAVE BOOKMARK'}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        ) : (
          <StaggerContainer 
            className={viewMode === 'grid'
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
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
      </div>

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
    </div>
  );
};

export default DashboardPage;
