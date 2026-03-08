import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { Network, SearchIcon, SparklesIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { StaggerContainer, StaggerItem } from '../components/motion/PageOrchestrator';
import AppLayout from '../components/AppLayout';
import { AILoadingSpinner, AnimatedCounter, MilestoneToast } from '../components/delight';
import { checkMilestone, markMilestoneReached } from '../utils/milestones';
import { EmptyStateGuide } from '../components/onboarding';
import ErrorMessage from '../components/ErrorMessage';

const KnowledgeGraphPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState(null);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState(null);

  // Track if milestone has been shown this session
  const milestoneShownRef = useRef(false);

  const fetchGraphData = async () => {
    try {
      setError(null);
      setLoading(true);
      const response = await axiosInstance.get('/knowledge-graph/explore?limit=100');
      setGraphData(response.data);
    } catch (err) {
      const message = err.response?.status === 0
        ? 'Unable to connect. Check your internet connection.'
        : err.response?.data?.detail || 'Failed to load knowledge graph';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, []);

  // Check for first_graph milestone on mount
  useEffect(() => {
    if (milestoneShownRef.current) return;

    const { reached } = checkMilestone('first_graph');
    if (!reached) {
      milestoneShownRef.current = true;
      markMilestoneReached('first_graph');

      // Slight delay to let the page load first
      const timer = setTimeout(() => {
        toast.custom((t) => (
          <MilestoneToast
            milestone="first_graph"
            onDismiss={() => toast.dismiss(t)}
          />
        ), { duration: 5000 });
      }, 500);

      return () => clearTimeout(timer);
    }
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
      setHasSearched(true);
      if (response.data.results.length === 0) {
        const message = response.data.message || 'No semantically similar bookmarks found';
        toast.info(message);
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

  const topConcepts = graphData
    ? Object.entries(graphData.concept_connections || {})
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 20)
    : [];

  const topEntities = graphData
    ? Object.entries(graphData.entity_connections || {})
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 20)
    : [];

  return (
    <AppLayout onLogout={onLogout} showSearch={false}>
      <div className="px-6 py-6">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-xl font-bold uppercase tracking-wide">Knowledge Graph</h2>
              {graphData && (
                <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  {graphData.total_bookmarks} Bookmarks • {graphData.total_concepts} Concepts
                </p>
              )}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
          </div>
        ) : error ? (
          <ErrorMessage
            title="Failed to load knowledge graph"
            message={error}
            onRetry={fetchGraphData}
            retrying={loading}
          />
        ) : !graphData || graphData.total_bookmarks === 0 ? (
          <EmptyStateGuide
            type="graph"
            onPrimaryAction={() => navigate('/dashboard')}
          />
        ) : (
          <StaggerContainer className="space-y-6">
            {/* Semantic Search */}
            <StaggerItem>
              <div className="border-2 border-accent bg-accent/5 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <SparklesIcon className="w-5 h-5 text-accent" />
                  <h3 className="font-heading font-bold uppercase tracking-wide">Semantic Search</h3>
                </div>
                <form onSubmit={handleSearch} className="flex gap-3">
                  <Input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="SEARCH BY MEANING, NOT JUST KEYWORDS..."
                    maxLength={500}
                    disabled={searching}
                    className="flex-1 h-12 rounded-none border-2 border-foreground font-mono text-sm placeholder:uppercase placeholder:tracking-wider disabled:opacity-50"
                  />
                  <Button
                    type="submit"
                    disabled={searching || searchQuery.length < 3}
                    className="h-12 px-6 rounded-none border-2 border-foreground bg-foreground text-background font-mono uppercase tracking-wider hover:bg-foreground/90 disabled:opacity-50"
                  >
                    {searching ? (
                      <AILoadingSpinner
                        messages={[
                          'Understanding your intent...',
                          'Finding semantic matches...',
                          'Connecting concepts...',
                          'Searching the graph...'
                        ]}
                        size="sm"
                        className="text-background [&_span]:text-background [&_div]:border-background [&_div]:border-t-transparent"
                      />
                    ) : (
                      <>
                        <SearchIcon className="w-4 h-4 mr-2" />
                        Search
                      </>
                    )}
                  </Button>
                </form>

                {/* Empty state for no results */}
                {searchResults.length === 0 && hasSearched && !searching && (
                  <div className="mt-6 text-center py-8 border-2 border-dashed border-muted-foreground/30">
                    <SearchIcon className="w-10 h-10 mx-auto mb-3 text-muted-foreground/50" />
                    <p className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
                      No semantic matches found. Try different wording?
                    </p>
                  </div>
                )}

                {searchResults.length > 0 && (
                  <div className="mt-6 space-y-3">
                    <style>{`
                      @keyframes similarity-pulse {
                        0%, 100% { border-color: #3B82F6; }
                        50% { border-color: #F97316; }
                      }
                      .high-similarity-pulse {
                        animation: similarity-pulse 0.5s ease-in-out 2;
                      }
                    `}</style>
                    <h4 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                      Search Results ({searchResults.length})
                    </h4>
                    {searchResults.map((result, index) => {
                      const similarityPercent = Math.round(result.similarity_score * 100);
                      const isHighSimilarity = similarityPercent > 85;

                      return (
                        <motion.div
                          key={result.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{
                            type: 'spring',
                            stiffness: 400,
                            damping: 25,
                            delay: index * 0.08
                          }}
                          className="border-2 border-foreground bg-card p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all cursor-pointer"
                          onClick={() => navigate(`/bookmark/${result.id}`)}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <h5 className="font-heading font-bold text-sm line-clamp-1">{result.title || 'Untitled'}</h5>
                              {result.description && (
                                <p className="text-sm text-muted-foreground line-clamp-2 mt-1">{result.description}</p>
                              )}
                              <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-2">
                                {result.domain}
                              </div>
                            </div>
                            <div className={`font-mono text-xs text-accent border-2 border-accent px-2 py-1 bg-accent/10 flex-shrink-0 ${isHighSimilarity ? 'high-similarity-pulse' : ''}`}>
                              <AnimatedCounter
                                endValue={similarityPercent}
                                suffix="%"
                                duration={0.5}
                                delay={index * 0.1}
                              />
                            </div>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>
            </StaggerItem>

            {/* Statistics */}
            <StaggerItem>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                    Total Bookmarks
                  </div>
                  <div className="font-display text-4xl font-bold">{graphData.total_bookmarks}</div>
                </div>
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                    Unique Concepts
                  </div>
                  <div className="font-display text-4xl font-bold">{graphData.total_concepts}</div>
                </div>
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                    Named Entities
                  </div>
                  <div className="font-display text-4xl font-bold">{graphData.total_entities}</div>
                </div>
              </div>
            </StaggerItem>

            {/* Top Concepts */}
            {topConcepts.length > 0 && (
              <StaggerItem>
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <h3 className="font-heading font-bold uppercase tracking-wide mb-4 pb-4 border-b-2 border-foreground">
                    Top Concepts
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {topConcepts.map(([concept, bookmarkIds]) => (
                      <button
                        key={concept}
                        onClick={() => setSelectedConcept(selectedConcept === concept ? null : concept)}
                        className={`px-3 py-1.5 border-2 font-mono text-xs uppercase tracking-wider transition-all ${selectedConcept === concept
                          ? 'bg-primary text-primary-foreground border-primary shadow-brutal-sm'
                          : 'bg-muted text-foreground border-foreground hover:bg-foreground hover:text-background'
                          }`}
                      >
                        {concept}
                        <span className="ml-2 opacity-70">({bookmarkIds.length})</span>
                      </button>
                    ))}
                  </div>

                  {selectedConcept && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-6 pt-6 border-t-2 border-foreground space-y-3"
                    >
                      <h4 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                        Bookmarks with "{selectedConcept}" ({filterBookmarksByConcept(selectedConcept).length})
                      </h4>
                      {filterBookmarksByConcept(selectedConcept).map((bookmark) => (
                        <div
                          key={bookmark.id}
                          onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                          className="border-2 border-foreground bg-background p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all cursor-pointer"
                        >
                          <h5 className="font-heading font-bold text-sm line-clamp-1">{bookmark.title || 'Untitled'}</h5>
                          {bookmark.description && (
                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">{bookmark.description}</p>
                          )}
                          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mt-2">
                            {bookmark.domain}
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </div>
              </StaggerItem>
            )}

            {/* Named Entities */}
            {topEntities.length > 0 && (
              <StaggerItem>
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <h3 className="font-heading font-bold uppercase tracking-wide mb-4 pb-4 border-b-2 border-foreground">
                    Named Entities
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {topEntities.map(([entity, bookmarkIds]) => (
                      <div
                        key={entity}
                        className="px-3 py-1 border-2 border-foreground bg-muted font-mono text-xs uppercase tracking-wider"
                      >
                        {entity}
                        <span className="ml-1 opacity-70">({bookmarkIds.length})</span>
                      </div>
                    ))}
                  </div>
                </div>
              </StaggerItem>
            )}

            {/* All Bookmarks in Graph */}
            <StaggerItem>
              <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                <h3 className="font-heading font-bold uppercase tracking-wide mb-4 pb-4 border-b-2 border-foreground">
                  All Bookmarks in Graph
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {graphData.bookmarks.map((bookmark) => (
                    <div
                      key={bookmark.id}
                      onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                      className="border-2 border-foreground bg-background p-4 shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all cursor-pointer"
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
                        <h4 className="font-heading font-bold text-sm truncate">{bookmark.title || 'Untitled'}</h4>
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
                    </div>
                  ))}
                </div>
              </div>
            </StaggerItem>
          </StaggerContainer>
        )}
      </div>
    </AppLayout>
  );
};

export default KnowledgeGraphPage;
