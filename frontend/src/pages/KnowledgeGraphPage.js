import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeftIcon, NetworkIcon, SearchIcon, SparklesIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { HardReveal, StaggerContainer, StaggerItem } from '../components/motion/PageOrchestrator';

const KnowledgeGraphPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState(null);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const response = await axiosInstance.get('/knowledge-graph/explore?limit=100');
        setGraphData(response.data);
      } catch (error) {
        toast.error('Failed to load knowledge graph');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || searchQuery.length < 3) {
      toast.error('Search query must be at least 3 characters');
      return;
    }

    setSearching(true);
    try {
      const response = await axiosInstance.get(`/knowledge-graph/search?query=${encodeURIComponent(searchQuery)}&limit=10`);
      setSearchResults(response.data.results || []);
      if (response.data.results.length === 0) {
        toast.info('No semantically similar bookmarks found');
      }
    } catch (error) {
      toast.error('Search failed');
      console.error(error);
    } finally {
      setSearching(false);
    }
  };

  const filterBookmarksByConcept = (concept) => {
    if (!graphData) return [];
    const bookmarkIds = graphData.concept_connections[concept] || [];
    return graphData.bookmarks.filter(b => bookmarkIds.includes(b.id));
  };

  const filterBookmarksByEntity = (entity) => {
    if (!graphData) return [];
    const bookmarkIds = graphData.entity_connections[entity] || [];
    return graphData.bookmarks.filter(b => bookmarkIds.includes(b.id));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
      </div>
    );
  }

  if (!graphData) return null;

  const topConcepts = Object.entries(graphData.concept_connections || {})
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 20);

  const topEntities = Object.entries(graphData.entity_connections || {})
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 20);

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <HardReveal direction="down">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/dashboard')}
                >
                  <ArrowLeftIcon className="w-4 h-4 mr-2" />
                  BACK
                </Button>
                <div className="h-6 w-px bg-foreground" />
                <div className="flex items-center gap-2">
                  <NetworkIcon className="w-5 h-5" />
                  <h1 className="font-display text-xl uppercase tracking-wide">Knowledge Graph</h1>
                </div>
              </div>
              <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                {graphData.total_bookmarks} Bookmarks • {graphData.total_concepts} Concepts
              </div>
            </div>
          </div>
        </HardReveal>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <StaggerContainer>
          {/* Semantic Search */}
          <StaggerItem>
            <div className="mb-8">
              <div className="border-2 border-accent bg-accent/10 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <SparklesIcon className="w-5 h-5 text-accent" />
                  <h2 className="font-display text-xl uppercase tracking-wide">Semantic Search</h2>
                </div>
                <form onSubmit={handleSearch} className="flex gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="SEARCH BY MEANING, NOT JUST KEYWORDS..."
                    className="flex-1 h-12 bg-background border-2 border-foreground px-4 py-3 font-mono text-sm placeholder:uppercase placeholder:tracking-wider focus:shadow-brutal-sm focus:outline-none"
                  />
                  <Button
                    type="submit"
                    disabled={searching}
                    className="h-12 px-6 font-mono uppercase tracking-wider"
                  >
                    <SearchIcon className="w-4 h-4 mr-2" />
                    {searching ? 'Searching...' : 'Search'}
                  </Button>
                </form>

                {searchResults.length > 0 && (
                  <div className="mt-6 space-y-3">
                    <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                      Search Results ({searchResults.length})
                    </h3>
                    {searchResults.map((result) => (
                      <motion.div
                        key={result.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="border-2 border-foreground bg-background p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 cursor-pointer"
                        onClick={() => navigate(`/bookmark/${result.id}`)}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <h4 className="font-semibold mb-1">{result.title || 'Untitled'}</h4>
                            {result.description && (
                              <p className="text-sm text-muted-foreground line-clamp-2">{result.description}</p>
                            )}
                            <div className="flex items-center gap-2 mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                              <span>{result.domain}</span>
                            </div>
                          </div>
                          <div className="font-mono text-xs text-accent border border-accent px-2 py-1 bg-accent/10">
                            {Math.round(result.similarity_score * 100)}%
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </StaggerItem>

          {/* Statistics */}
          <StaggerItem>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Total Bookmarks
                </div>
                <div className="font-display text-4xl uppercase tracking-wide">{graphData.total_bookmarks}</div>
              </div>
              <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Unique Concepts
                </div>
                <div className="font-display text-4xl uppercase tracking-wide">{graphData.total_concepts}</div>
              </div>
              <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                  Named Entities
                </div>
                <div className="font-display text-4xl uppercase tracking-wide">{graphData.total_entities}</div>
              </div>
            </div>
          </StaggerItem>

          {/* Top Concepts */}
          {topConcepts.length > 0 && (
            <StaggerItem>
              <div className="mb-8">
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <h2 className="font-display text-xl uppercase tracking-wide mb-6 pb-4 border-b-2 border-foreground">
                    Top Concepts
                  </h2>
                  <div className="flex flex-wrap gap-3">
                    {topConcepts.map(([concept, bookmarkIds]) => (
                      <motion.button
                        key={concept}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setSelectedConcept(selectedConcept === concept ? null : concept)}
                        className={`px-4 py-2 border-2 font-mono text-sm uppercase tracking-wider transition-all duration-150 ${
                          selectedConcept === concept
                            ? 'bg-primary text-primary-foreground border-primary shadow-brutal-sm'
                            : 'bg-muted text-foreground border-foreground hover:bg-foreground hover:text-background'
                        }`}
                      >
                        {concept}
                        <span className="ml-2 text-xs opacity-70">({bookmarkIds.length})</span>
                      </motion.button>
                    ))}
                  </div>

                  {selectedConcept && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-6 pt-6 border-t-2 border-foreground space-y-3"
                    >
                      <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                        Bookmarks with "{selectedConcept}" ({filterBookmarksByConcept(selectedConcept).length})
                      </h3>
                      {filterBookmarksByConcept(selectedConcept).map((bookmark) => (
                        <div
                          key={bookmark.id}
                          onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                          className="border-2 border-foreground bg-background p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 cursor-pointer"
                        >
                          <h4 className="font-semibold mb-1">{bookmark.title || 'Untitled'}</h4>
                          {bookmark.description && (
                            <p className="text-sm text-muted-foreground line-clamp-2">{bookmark.description}</p>
                          )}
                          <div className="flex items-center gap-2 mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                            <span>{bookmark.domain}</span>
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </div>
              </div>
            </StaggerItem>
          )}

          {/* Top Entities */}
          {topEntities.length > 0 && (
            <StaggerItem>
              <div className="mb-8">
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <h2 className="font-display text-xl uppercase tracking-wide mb-6 pb-4 border-b-2 border-foreground">
                    Named Entities
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {topEntities.map(([entity, bookmarkIds]) => (
                      <div
                        key={entity}
                        className="px-3 py-1 border border-foreground bg-muted font-mono text-xs uppercase tracking-wider"
                      >
                        {entity}
                        <span className="ml-1 text-[10px] opacity-70">({bookmarkIds.length})</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </StaggerItem>
          )}

          {/* All Bookmarks */}
          <StaggerItem>
            <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
              <h2 className="font-display text-xl uppercase tracking-wide mb-6 pb-4 border-b-2 border-foreground">
                All Bookmarks in Graph
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {graphData.bookmarks.map((bookmark) => (
                  <motion.div
                    key={bookmark.id}
                    whileHover={{ scale: 1.02 }}
                    onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                    className="border-2 border-foreground bg-background p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all duration-150 cursor-pointer"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {bookmark.favicon && (
                        <img
                          src={bookmark.favicon}
                          alt=""
                          className="w-4 h-4 border border-foreground"
                          onError={(e) => (e.target.style.display = 'none')}
                        />
                      )}
                      <h3 className="font-semibold text-sm truncate">{bookmark.title || 'Untitled'}</h3>
                    </div>
                    {bookmark.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{bookmark.description}</p>
                    )}
                    <div className="flex flex-wrap gap-1 mt-2">
                      {bookmark.concepts && bookmark.concepts.slice(0, 3).map((concept, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 border border-foreground bg-muted font-mono text-[10px] uppercase tracking-wider"
                        >
                          {concept}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </StaggerItem>
        </StaggerContainer>
      </div>
    </div>
  );
};

export default KnowledgeGraphPage;
