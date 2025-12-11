import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { BookmarkIcon, PlusIcon, SearchIcon, FilterIcon, SparklesIcon, FolderIcon, LogOutIcon, CopyIcon, UploadIcon, DownloadIcon } from 'lucide-react';
import BookmarkCard from '../components/BookmarkCard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [selectedBookmarks, setSelectedBookmarks] = useState([]);
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [readFilter, setReadFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');

  const token = localStorage.getItem('token');
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

      const response = await axios.get(`${API}/bookmarks?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
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
      const response = await axios.get(`${API}/collections`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCollections(response.data);
    } catch (error) {
      console.error('Failed to fetch collections');
    }
  };

  useEffect(() => {
    fetchBookmarks();
    fetchCollections();
  }, [searchQuery, filterTag, filterDomain, filterCollection]);

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
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setDialogOpen(true);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        document.querySelector('[data-testid="search-input"]')?.focus();
      }
      if (e.key === 'Escape') {
        setDialogOpen(false);
        setCollectionDialogOpen(false);
        setImportDialogOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleAddBookmark = async (e) => {
    e.preventDefault();
    if (!newBookmarkUrl) return;

    setAddingBookmark(true);
    try {
      await axios.post(
        `${API}/bookmarks`,
        { url: newBookmarkUrl },
        { headers: { Authorization: `Bearer ${token}` } }
      );
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
      await axios.post(
        `${API}/collections`,
        { name: newCollectionName },
        { headers: { Authorization: `Bearer ${token}` } }
      );
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
      await axios.delete(`${API}/bookmarks/${bookmarkId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Bookmark deleted');
      fetchBookmarks();
    } catch (error) {
      toast.error('Failed to delete bookmark');
    }
  };

  const handleImportBookmarks = async (e) => {
    e.preventDefault();
    if (!importFile) return;

    setImporting(true);
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const response = await axios.post(
            `${API}/bookmarks/import`,
            event.target.result,
            {
              headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'text/plain'
              }
            }
          );
          toast.success(`Imported ${response.data.count} bookmarks! AI processing...`);
          setImportFile(null);
          setImportDialogOpen(false);
          fetchBookmarks();
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

  const handleExportBookmarks = async () => {
    try {
      const response = await axios.get(`${API}/bookmarks/export`, {
        headers: { Authorization: `Bearer ${token}` },
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 glassmorphism border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary text-primary-foreground">
                <BookmarkIcon className="w-5 h-5" />
              </div>
              <h1 className="font-heading text-2xl font-bold tracking-tight">Arivu</h1>
            </div>
            <div className="flex items-center gap-2">
              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    data-testid="add-bookmark-header-btn"
                    size="sm"
                    className="rounded-full"
                  >
                    <PlusIcon className="w-4 h-4 mr-2" />
                    Add Bookmark
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-2xl" aria-describedby="add-bookmark-header-description">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Add Bookmark</DialogTitle>
                    <p id="add-bookmark-header-description" className="text-sm text-muted-foreground sr-only">
                      Enter a URL to save and get AI-powered summaries
                    </p>
                  </DialogHeader>
                  <form onSubmit={handleAddBookmark} className="space-y-4">
                    <Input
                      data-testid="bookmark-url-input-header"
                      type="url"
                      placeholder="https://example.com/article"
                      value={newBookmarkUrl}
                      onChange={(e) => setNewBookmarkUrl(e.target.value)}
                      required
                      className="rounded-xl"
                      autoFocus
                    />
                    <Button
                      data-testid="save-bookmark-btn-header"
                      type="submit"
                      className="w-full rounded-full"
                      disabled={addingBookmark}
                    >
                      {addingBookmark ? 'Saving...' : 'Save Bookmark'}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
              <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    data-testid="import-btn"
                    variant="ghost"
                    size="sm"
                    className="rounded-full"
                  >
                    <UploadIcon className="w-4 h-4 mr-2" />
                    Import
                  </Button>
                </DialogTrigger>
                <DialogContent className="rounded-2xl" aria-describedby="import-description">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Import Bookmarks</DialogTitle>
                    <p id="import-description" className="text-sm text-muted-foreground sr-only">
                      Import bookmarks from your browser HTML file
                    </p>
                  </DialogHeader>
                  <form onSubmit={handleImportBookmarks} className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Select HTML file</label>
                      <Input
                        data-testid="import-file-input"
                        type="file"
                        accept=".html"
                        onChange={(e) => setImportFile(e.target.files[0])}
                        required
                        className="rounded-xl"
                      />
                      <p className="text-xs text-muted-foreground">
                        Export bookmarks from Chrome, Firefox, or Safari
                      </p>
                    </div>
                    <Button
                      data-testid="import-submit-btn"
                      type="submit"
                      className="w-full rounded-full"
                      disabled={importing}
                    >
                      {importing ? 'Importing...' : 'Import Bookmarks'}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
              <Button
                data-testid="export-btn"
                variant="ghost"
                size="sm"
                className="rounded-full"
                onClick={handleExportBookmarks}
              >
                <DownloadIcon className="w-4 h-4 mr-2" />
                Export
              </Button>
              <Button
                data-testid="duplicates-btn"
                variant="ghost"
                size="sm"
                className="rounded-full"
                onClick={() => navigate('/duplicates')}
              >
                <CopyIcon className="w-4 h-4 mr-2" />
                Duplicates
              </Button>
              <Button
                data-testid="logout-btn"
                variant="ghost"
                size="sm"
                className="rounded-full"
                onClick={onLogout}
              >
                <LogOutIcon className="w-4 h-4 mr-2" />
                Log Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search and Filters */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              data-testid="search-input"
              type="text"
              placeholder="Search bookmarks, content, or notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-14 rounded-2xl border-none bg-muted/50 px-4 pl-12 text-base shadow-none focus-visible:ring-0 focus-visible:bg-muted"
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <Select value={filterTag} onValueChange={setFilterTag}>
              <SelectTrigger data-testid="tag-filter" className="w-[180px] rounded-xl">
                <FilterIcon className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by tag" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_clear">All tags</SelectItem>
                {allTags.map(tag => (
                  <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filterDomain} onValueChange={setFilterDomain}>
              <SelectTrigger data-testid="domain-filter" className="w-[180px] rounded-xl">
                <SelectValue placeholder="Filter by domain" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_clear">All domains</SelectItem>
                {allDomains.map(domain => (
                  <SelectItem key={domain} value={domain}>{domain}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filterCollection} onValueChange={setFilterCollection}>
              <SelectTrigger data-testid="collection-filter" className="w-[200px] rounded-xl">
                <FolderIcon className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by collection" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_clear">All collections</SelectItem>
                {collections.map(col => (
                  <SelectItem key={col.id} value={col.id}>{col.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Dialog open={collectionDialogOpen} onOpenChange={setCollectionDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="new-collection-btn" variant="outline" size="sm" className="rounded-xl">
                  <FolderIcon className="w-4 h-4 mr-2" />
                  New Collection
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-2xl" aria-describedby="create-collection-description">
                <DialogHeader>
                  <DialogTitle className="font-heading">Create Collection</DialogTitle>
                  <p id="create-collection-description" className="text-sm text-muted-foreground sr-only">
                    Create a new collection to organize your bookmarks
                  </p>
                </DialogHeader>
                <form onSubmit={handleCreateCollection} className="space-y-4">
                  <Input
                    data-testid="collection-name-input"
                    placeholder="Collection name"
                    value={newCollectionName}
                    onChange={(e) => setNewCollectionName(e.target.value)}
                    className="rounded-xl"
                    autoFocus
                  />
                  <Button data-testid="create-collection-btn" type="submit" className="w-full rounded-full">
                    Create
                  </Button>
                </form>
              </DialogContent>
            </Dialog>

            {(filterTag || filterDomain || filterCollection) && (
              <Button
                data-testid="clear-filters-btn"
                variant="ghost"
                size="sm"
                className="rounded-xl"
                onClick={() => {
                  setFilterTag('');
                  setFilterDomain('');
                  setFilterCollection('');
                }}
              >
                Clear filters
              </Button>
            )}
          </div>
        </div>

        {/* Bookmarks Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        ) : bookmarks.length === 0 ? (
          <div className="text-center py-20">
            <SparklesIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="font-heading text-2xl font-semibold mb-2">No bookmarks yet</h2>
            <p className="text-muted-foreground mb-6">Start saving web pages and let AI organize them for you</p>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="add-first-bookmark-btn" size="lg" className="rounded-full">
                  <PlusIcon className="w-5 h-5 mr-2" />
                  Add Your First Bookmark
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-2xl" aria-describedby="add-bookmark-description">
                <DialogHeader>
                  <DialogTitle className="font-heading">Add Bookmark</DialogTitle>
                  <p id="add-bookmark-description" className="text-sm text-muted-foreground sr-only">
                    Enter a URL to save and get AI-powered summaries
                  </p>
                </DialogHeader>
                <form onSubmit={handleAddBookmark} className="space-y-4">
                  <Input
                    data-testid="bookmark-url-input"
                    type="url"
                    placeholder="https://example.com/article"
                    value={newBookmarkUrl}
                    onChange={(e) => setNewBookmarkUrl(e.target.value)}
                    required
                    className="rounded-xl"
                    autoFocus
                  />
                  <Button
                    data-testid="save-bookmark-btn"
                    type="submit"
                    className="w-full rounded-full"
                    disabled={addingBookmark}
                  >
                    {addingBookmark ? 'Saving...' : 'Save Bookmark'}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {bookmarks.map(bookmark => (
              <BookmarkCard
                key={bookmark.id}
                bookmark={bookmark}
                onDelete={handleDeleteBookmark}
                onClick={() => navigate(`/bookmark/${bookmark.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Floating Action Button - Positioned to avoid overlays */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button
            data-testid="add-bookmark-fab"
            size="lg"
            className="fixed bottom-6 right-20 md:right-6 rounded-full w-14 h-14 shadow-xl hover:shadow-2xl z-40"
          >
            <PlusIcon className="w-6 h-6" />
          </Button>
        </DialogTrigger>
        <DialogContent className="rounded-2xl" aria-describedby="add-bookmark-description-fab">
          <DialogHeader>
            <DialogTitle className="font-heading">Add Bookmark</DialogTitle>
            <p id="add-bookmark-description-fab" className="text-sm text-muted-foreground sr-only">
              Enter a URL to save and get AI-powered summaries
            </p>
          </DialogHeader>
          <form onSubmit={handleAddBookmark} className="space-y-4">
            <Input
              data-testid="bookmark-url-input-fab"
              type="url"
              placeholder="https://example.com/article"
              value={newBookmarkUrl}
              onChange={(e) => setNewBookmarkUrl(e.target.value)}
              required
              className="rounded-xl"
              autoFocus
            />
            <Button
              data-testid="save-bookmark-btn-fab"
              type="submit"
              className="w-full rounded-full"
              disabled={addingBookmark}
            >
              {addingBookmark ? 'Saving...' : 'Save Bookmark'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DashboardPage;
