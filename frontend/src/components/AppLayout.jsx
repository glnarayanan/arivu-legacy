import { useState, useEffect } from 'react';
import { BookmarkIcon, SearchIcon } from 'lucide-react';
import { Input } from './ui/input';
import UserMenu from './UserMenu';
import Sidebar from './Sidebar';
import { HardReveal } from './motion/PageOrchestrator';
import axiosInstance from '../utils/axiosConfig';

/**
 * AppLayout - Shared layout component for authenticated pages.
 * Provides consistent header with logo, search, user menu, and sidebar navigation.
 */
const AppLayout = ({
  children,
  onLogout,
  searchQuery = '',
  onSearchChange,
  showSearch = true,
  headerRight,
  // Settings page props
  settingsSection = '',
  onSettingsSectionChange = () => { },
  settingsSections,
}) => {
  const [collections, setCollections] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [filterTag, setFilterTag] = useState('');
  const [filterCollection, setFilterCollection] = useState('');

  const fetchCollections = async () => {
    try {
      const response = await axiosInstance.get('/collections');
      setCollections(response.data);
    } catch (error) {
      console.error('Failed to fetch collections');
    }
  };

  const fetchTags = async () => {
    try {
      const response = await axiosInstance.get('/bookmarks?limit=500');
      const tags = new Set();
      response.data.forEach(b => {
        if (b.ai_summary?.suggested_tags) {
          b.ai_summary.suggested_tags.forEach(tag => tags.add(tag));
        }
      });
      setAllTags([...tags]);
    } catch (error) {
      console.error('Failed to fetch tags');
    }
  };

  useEffect(() => {
    fetchCollections();
    fetchTags();
  }, []);

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
                {/* Search Bar */}
                {showSearch && onSearchChange && (
                  <div className="relative hidden md:block w-80">
                    <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      data-testid="search-input"
                      type="text"
                      placeholder="SEARCH..."
                      value={searchQuery}
                      onChange={(e) => onSearchChange(e.target.value)}
                      className="h-10 rounded-none border-2 border-foreground bg-background pl-10 text-sm shadow-none focus-visible:ring-0 font-mono placeholder:text-muted-foreground"
                    />
                  </div>
                )}

                {/* Custom header right content */}
                {headerRight}

                <UserMenu onLogout={onLogout} />
              </div>
            </div>
          </div>
        </HardReveal>
      </header>

      {/* Main Layout with Sidebar */}
      <div className="flex">
        <Sidebar
          collections={collections}
          allTags={allTags}
          filterTag={filterTag}
          setFilterTag={setFilterTag}
          filterCollection={filterCollection}
          setFilterCollection={setFilterCollection}
          onCreateCollection={fetchCollections}
          showFilters={true}
          settingsSection={settingsSection}
          onSettingsSectionChange={onSettingsSectionChange}
          settingsSections={settingsSections}
        />

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
