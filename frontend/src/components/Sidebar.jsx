import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Bookmark,
  FolderOpen,
  Heart,
  StickyNote,
  Link2,
  FileText,
  File,
  Image,
  Tag,
  Network,
  BarChart3,
  ChevronDown,
  ChevronRight,
  Plus,
  Hash,
  Settings,
  User,
  Lock,
  Upload,
  Download,
  Copy,
  RefreshCw,
  Archive,
  ExternalLink,
  AlarmClockOff,
  Clock,
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Input } from './ui/input';
import axiosInstance from '../utils/axiosConfig';
import { toast } from 'sonner';
import { OnboardingChecklist } from './onboarding';

// Settings sections for when on settings page
const SETTINGS_SECTIONS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'account', label: 'Account', icon: Lock },
  { id: 'connections', label: 'Connections', icon: Link2 },
  { id: 'import', label: 'Import', icon: Upload },
  { id: 'backup', label: 'Backup', icon: Download },
  { id: 'duplicates', label: 'Duplicates', icon: Copy },
];

const Sidebar = ({
  collections = [],
  allTags = [],
  filterTag = '',
  setFilterTag = () => { },
  filterCollection = '',
  setFilterCollection = () => { },
  onCreateCollection,
  showFilters = true,
  // Settings page props
  settingsSection = '',
  onSettingsSectionChange = () => { },
  // Resurfacing props
  resurfacingSuggestions = [],
  onResurfacingReadAgain,
  onResurfacingSnooze,
  onResurfacingArchive,
  // Aged bookmarks props
  agedCount = 0,
  onViewAged,
  // Onboarding props
  bookmarkCount = 0,
  onOpenAddBookmark,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collectionsOpen, setCollectionsOpen] = useState(true);
  const [tagsOpen, setTagsOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [resurfacingOpen, setResurfacingOpen] = useState(true);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [collectionDialogOpen, setCollectionDialogOpen] = useState(false);

  const isSettingsPage = location.pathname === '/settings';

  const handleCreateCollection = async (e) => {
    e.preventDefault();
    if (!newCollectionName) return;

    try {
      await axiosInstance.post('/collections', { name: newCollectionName });
      toast.success('Collection created!');
      setNewCollectionName('');
      setCollectionDialogOpen(false);
      if (onCreateCollection) onCreateCollection();
    } catch (error) {
      toast.error('Failed to create collection');
    }
  };

  const NavItem = ({ icon: Icon, label, onClick, isActive, count }) => (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center justify-between gap-3 px-3 py-2 text-left transition-all
        font-mono text-xs uppercase tracking-wider border-l-2
        ${isActive
          ? 'bg-muted border-l-primary text-foreground font-medium'
          : 'border-l-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground'
        }
      `}
    >
      <div className="flex items-center gap-3">
        <Icon className="w-4 h-4 flex-shrink-0" />
        <span className="truncate">{label}</span>
      </div>
      {count !== undefined && (
        <span className="text-muted-foreground text-[10px]">{count}</span>
      )}
    </button>
  );

  const SectionHeader = ({ label, isOpen, onToggle, onAdd }) => (
    <div className="flex items-center justify-between px-3 py-2 border-b border-foreground/10">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
      >
        {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {label}
      </button>
      {onAdd && (
        <button
          onClick={onAdd}
          className="p-1 hover:bg-muted transition-colors"
        >
          <Plus className="w-3 h-3 text-muted-foreground" />
        </button>
      )}
    </div>
  );

  return (
    <aside className="w-64 flex-shrink-0 bg-card border-r-2 border-foreground flex flex-col h-[calc(100vh-73px)] sticky top-[73px]">
      <ScrollArea className="flex-1">
        <div className="py-2">
          {/* Main Navigation */}
          <div className="mb-2">
            <NavItem
              icon={Bookmark}
              label="All Bookmarks"
              onClick={() => {
                navigate('/dashboard');
                setFilterCollection('');
                setFilterTag('');
              }}
              isActive={!filterCollection && !filterTag && location.pathname === '/dashboard'}
            />
            <NavItem
              icon={Network}
              label="Knowledge Graph"
              onClick={() => navigate('/knowledge-graph')}
              isActive={location.pathname === '/knowledge-graph'}
            />
            <NavItem
              icon={BarChart3}
              label="Analytics"
              onClick={() => navigate('/analytics')}
              isActive={location.pathname === '/analytics'}
            />
            <NavItem
              icon={Settings}
              label="Settings"
              onClick={() => navigate('/settings')}
              isActive={location.pathname === '/settings'}
            />
          </div>

          {/* Show Settings Sections when on Settings Page */}
          {isSettingsPage && (
            <div className="mb-2 border-t-2 border-foreground/10 pt-2">
              <div className="px-3 py-2">
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  Settings
                </span>
              </div>
              {SETTINGS_SECTIONS.map((section) => (
                <NavItem
                  key={section.id}
                  icon={section.icon}
                  label={section.label}
                  onClick={() => onSettingsSectionChange(section.id)}
                  isActive={settingsSection === section.id}
                />
              ))}
            </div>
          )}

          {/* Show Collections/Filters/Tags when NOT on Settings Page */}
          {!isSettingsPage && (
            <>
              {/* Onboarding Checklist for new users */}
              <div className="px-3 pt-2">
                <OnboardingChecklist
                  bookmarkCount={bookmarkCount}
                  collectionCount={collections.length}
                  hasVisitedGraph={localStorage.getItem('arivu_milestone_first_graph') === 'true'}
                  onOpenAddBookmark={onOpenAddBookmark}
                />
              </div>

              {/* Aged Bookmarks Indicator */}
              {agedCount > 0 && (
                <div className="mx-3 mb-3 p-2 bg-amber-50 border-2 border-foreground">
                  <button
                    onClick={onViewAged}
                    className="w-full flex items-center gap-2 text-left"
                  >
                    <div className="p-1 bg-amber-100 border border-foreground flex-shrink-0">
                      <Archive className="w-3 h-3 text-amber-700" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-[10px] uppercase tracking-wider text-amber-900 font-bold">
                        {agedCount} collecting dust
                      </p>
                      <p className="font-mono text-[9px] uppercase tracking-wider text-amber-700 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        30+ days inactive
                      </p>
                    </div>
                  </button>
                </div>
              )}

              {/* Resurfacing Section */}
              {resurfacingSuggestions.length > 0 && (
                <div className="mb-2">
                  <SectionHeader
                    label={`Worth Revisiting (${resurfacingSuggestions.length})`}
                    isOpen={resurfacingOpen}
                    onToggle={() => setResurfacingOpen(!resurfacingOpen)}
                  />
                  {resurfacingOpen && (
                    <div className="py-1 space-y-1 px-2">
                      {resurfacingSuggestions.slice(0, 3).map((bookmark) => (
                        <div
                          key={bookmark.id}
                          className="p-2 bg-background border border-foreground text-xs"
                        >
                          <p className="font-heading font-bold text-[11px] uppercase leading-tight line-clamp-1 mb-1">
                            {bookmark.title || 'Untitled'}
                          </p>
                          <p className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground mb-1">
                            {bookmark.domain}
                          </p>
                          <p className="font-mono text-[9px] text-primary flex items-center gap-1">
                            <RefreshCw className="w-2.5 h-2.5" />
                            {bookmark.resurfacing_reason}
                          </p>
                          <div className="flex gap-1 mt-2">
                            <Button
                              variant="default"
                              size="sm"
                              onClick={() => {
                                window.open(bookmark.url, '_blank');
                                onResurfacingReadAgain?.(bookmark.id);
                              }}
                              className="flex-1 h-6 text-[9px] px-1"
                            >
                              <ExternalLink className="w-2.5 h-2.5 mr-1" />
                              READ
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onResurfacingSnooze?.(bookmark.id, 7)}
                              className="h-6 w-6 p-0"
                              title="Snooze 1 week"
                            >
                              <AlarmClockOff className="w-2.5 h-2.5" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onResurfacingArchive?.(bookmark.id)}
                              className="h-6 w-6 p-0"
                              title="Don't show again"
                            >
                              <Archive className="w-2.5 h-2.5" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Collections Section */}
              <div className="mb-2">
                <SectionHeader
                  label="My Collections"
                  isOpen={collectionsOpen}
                  onToggle={() => setCollectionsOpen(!collectionsOpen)}
                  onAdd={showFilters ? () => setCollectionDialogOpen(true) : undefined}
                />
                {collectionsOpen && (
                  <div className="py-1">
                    {collections.length === 0 ? (
                      <p className="px-3 py-2 text-xs text-muted-foreground font-mono">
                        No collections yet
                      </p>
                    ) : (
                      collections.map((col) => (
                        <NavItem
                          key={col.id}
                          icon={FolderOpen}
                          label={col.name}
                          onClick={() => {
                            navigate('/dashboard');
                            setFilterCollection(col.id);
                          }}
                          isActive={filterCollection === col.id && location.pathname === '/dashboard'}
                        />
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Filters Section */}
              {showFilters && (
                <div className="mb-2">
                  <SectionHeader
                    label="Filters"
                    isOpen={filtersOpen}
                    onToggle={() => setFiltersOpen(!filtersOpen)}
                  />
                  {filtersOpen && (
                    <div className="py-1">
                      <NavItem icon={Heart} label="Favorites" onClick={() => { }} />
                      <NavItem icon={StickyNote} label="Notes" onClick={() => { }} />
                      <NavItem icon={Link2} label="Links" onClick={() => { }} />
                      <NavItem icon={FileText} label="Articles" onClick={() => { }} />
                      <NavItem icon={File} label="Documents" onClick={() => { }} />
                      <NavItem icon={Image} label="Images" onClick={() => { }} />
                      <NavItem icon={Tag} label="Without Tags" onClick={() => { }} />
                    </div>
                  )}
                </div>
              )}

              {/* Tags Section */}
              {showFilters && (
                <div className="mb-2">
                  <SectionHeader
                    label={`Tags (${allTags.length})`}
                    isOpen={tagsOpen}
                    onToggle={() => setTagsOpen(!tagsOpen)}
                  />
                  {tagsOpen && (
                    <div className="py-1 max-h-[200px] overflow-y-auto">
                      {allTags.length === 0 ? (
                        <p className="px-3 py-2 text-xs text-muted-foreground font-mono">
                          No tags yet
                        </p>
                      ) : (
                        allTags.map((tag) => (
                          <NavItem
                            key={tag}
                            icon={Hash}
                            label={tag}
                            onClick={() => {
                              navigate('/dashboard');
                              setFilterTag(tag);
                            }}
                            isActive={filterTag === tag && location.pathname === '/dashboard'}
                          />
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Create Collection Dialog */}
      <Dialog open={collectionDialogOpen} onOpenChange={setCollectionDialogOpen}>
        <DialogContent className="rounded-none border-2 border-foreground shadow-brutal" aria-describedby="create-collection-description">
          <DialogHeader>
            <DialogTitle className="font-heading font-bold uppercase">Create Collection</DialogTitle>
            <p id="create-collection-description" className="text-sm text-muted-foreground sr-only">
              Create a new collection to organize your bookmarks
            </p>
          </DialogHeader>
          <form onSubmit={handleCreateCollection} className="space-y-4">
            <Input
              data-testid="collection-name-input-sidebar"
              placeholder="COLLECTION NAME"
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              className="rounded-none border-2 border-foreground font-mono"
              autoFocus
            />
            <Button
              data-testid="create-collection-btn-sidebar"
              type="submit"
              className="w-full rounded-none border-2 border-foreground bg-primary text-primary-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
            >
              CREATE
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </aside>
  );
};

export default Sidebar;
