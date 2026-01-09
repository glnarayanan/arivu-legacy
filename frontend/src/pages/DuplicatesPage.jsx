import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeftIcon, CopyIcon, MergeIcon, TrashIcon, ExternalLinkIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { HardReveal, StaggerContainer, StaggerItem } from '../components/motion/PageOrchestrator';

const DuplicatesPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDuplicates();
  }, []);

  const fetchDuplicates = async () => {
    try {
      const response = await axiosInstance.get(`/bookmarks/duplicates/detect`);
      setDuplicates(response.data.duplicates || []);
    } catch (error) {
      toast.error('Failed to detect duplicates');
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async (bookmarks) => {
    const ids = bookmarks.map(b => b.id);
    try {
      await axiosInstance.post(`/bookmarks/merge`, ids);
      toast.success('Duplicates merged!');
      fetchDuplicates();
    } catch (error) {
      toast.error('Failed to merge bookmarks');
    }
  };

  const handleDelete = async (bookmarkId) => {
    try {
      await axiosInstance.delete(`/bookmarks/${bookmarkId}`);
      toast.success('Bookmark deleted');
      fetchDuplicates();
    } catch (error) {
      toast.error('Failed to delete bookmark');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <HardReveal direction="down">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Button
                  data-testid="back-to-dashboard-btn"
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate('/dashboard')}
                >
                  <ArrowLeftIcon className="w-4 h-4 mr-2" />
                  BACK
                </Button>
                <div className="flex items-center gap-3">
                  <h1 className="font-display text-2xl tracking-wide uppercase">Duplicate Detection</h1>
                </div>
              </div>
            </div>
          </div>
        </HardReveal>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
          </div>
        ) : duplicates.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20 border-2 border-dashed border-muted-foreground/30"
          >
            <CopyIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="font-display text-2xl uppercase tracking-wide mb-2">No duplicates found</h2>
            <p className="text-muted-foreground font-mono text-sm mb-6">Your bookmarks are clean and organized!</p>
            <Button
              data-testid="go-back-btn"
              variant="outline"
              onClick={() => navigate('/dashboard')}
            >
              BACK TO DASHBOARD
            </Button>
          </motion.div>
        ) : (
          <StaggerContainer className="space-y-6">
            <StaggerItem>
              <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
                Found {duplicates.length} duplicate group{duplicates.length !== 1 ? 's' : ''}
              </p>
            </StaggerItem>

            {duplicates.map((duplicate, idx) => (
              <StaggerItem key={idx}>
                <div
                  data-testid={`duplicate-group-${idx}`}
                  className="bg-card border-2 border-foreground p-6 space-y-4 shadow-brutal"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CopyIcon className="w-5 h-5 text-muted-foreground" />
                      <span className="font-heading font-bold uppercase">
                        {duplicate.type === 'exact_url' ? 'Same URL' : 'Similar Content'}
                      </span>
                      {duplicate.similarity && (
                        <span className="font-mono text-xs text-muted-foreground uppercase tracking-wider">
                          ({Math.round(duplicate.similarity * 100)}% similar)
                        </span>
                      )}
                    </div>
                    <Button
                      data-testid={`merge-group-${idx}`}
                      size="sm"
                      variant="outline"
                      onClick={() => handleMerge(duplicate.bookmarks)}
                    >
                      <MergeIcon className="w-4 h-4 mr-2" />
                      MERGE ALL
                    </Button>
                  </div>

                  <div className="space-y-3">
                    {duplicate.bookmarks.map((bookmark) => (
                      <div
                        key={bookmark.id}
                        data-testid={`duplicate-bookmark-${bookmark.id}`}
                        className="flex items-start gap-4 p-4 bg-muted border-2 border-foreground"
                      >
                        {bookmark.thumbnail && (
                          <img
                            src={bookmark.thumbnail}
                            alt={bookmark.title}
                            className="w-24 h-16 object-cover flex-shrink-0 border border-foreground"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <h3 className="font-heading font-bold line-clamp-1 mb-1">{bookmark.title}</h3>
                          <p className="font-mono text-xs text-muted-foreground line-clamp-1 mb-2">{bookmark.url}</p>
                          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground uppercase tracking-wider">
                            {bookmark.favicon && (
                              <img
                                src={bookmark.favicon}
                                alt=""
                                className="w-4 h-4 border border-foreground"
                                onError={(e) => e.target.style.display = 'none'}
                              />
                            )}
                            <span>{bookmark.domain}</span>
                            <span>•</span>
                            <span>{new Date(bookmark.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <Button
                            data-testid={`view-duplicate-${bookmark.id}`}
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0"
                            onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                          >
                            <ExternalLinkIcon className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`delete-duplicate-${bookmark.id}`}
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(bookmark.id)}
                          >
                            <TrashIcon className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        )}
      </div>
    </div>
  );
};

export default DuplicatesPage;
