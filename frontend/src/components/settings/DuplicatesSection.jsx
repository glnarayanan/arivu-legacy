import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../../utils/axiosConfig';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { CopyIcon, MergeIcon, TrashIcon, ExternalLinkIcon, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';

const DuplicatesSection = () => {
  const navigate = useNavigate();
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDuplicates();
  }, []);

  const fetchDuplicates = async () => {
    setLoading(true);
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold uppercase tracking-wide">Duplicate Detection</h2>
          <p className="text-muted-foreground font-mono text-xs uppercase tracking-wider mt-1">
            Find and merge duplicate bookmarks
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchDuplicates}
          disabled={loading}
          className="rounded-none border-2 border-foreground hover:bg-muted font-mono uppercase text-xs"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Scan
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-muted border-t-primary"></div>
        </div>
      ) : duplicates.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-12 border-2 border-dashed border-muted-foreground/30"
        >
          <CopyIcon className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <h3 className="font-display text-lg uppercase tracking-wide mb-2">No duplicates found</h3>
          <p className="text-muted-foreground font-mono text-sm">Your bookmarks are clean and organized!</p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          <p className="text-muted-foreground font-mono text-xs uppercase tracking-wider">
            Found {duplicates.length} duplicate group{duplicates.length !== 1 ? 's' : ''}
          </p>

          {duplicates.map((duplicate, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              data-testid={`duplicate-group-${idx}`}
              className="bg-muted border-2 border-foreground p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CopyIcon className="w-4 h-4 text-muted-foreground" />
                  <span className="font-heading font-bold text-sm uppercase">
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
                  className="rounded-none border-2 border-foreground hover:bg-background font-mono uppercase text-xs"
                  onClick={() => handleMerge(duplicate.bookmarks)}
                >
                  <MergeIcon className="w-3 h-3 mr-2" />
                  Merge All
                </Button>
              </div>

              <div className="space-y-2">
                {duplicate.bookmarks.map((bookmark) => (
                  <div
                    key={bookmark.id}
                    data-testid={`duplicate-bookmark-${bookmark.id}`}
                    className="flex items-start gap-3 p-3 bg-card border border-foreground/20"
                  >
                    {bookmark.thumbnail && (
                      <img
                        src={bookmark.thumbnail}
                        alt={bookmark.title}
                        className="w-16 h-12 object-cover flex-shrink-0 border border-foreground"
                        onError={(e) => e.target.style.display = 'none'}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-heading font-bold text-sm line-clamp-1">{bookmark.title}</h4>
                      <p className="font-mono text-xs text-muted-foreground line-clamp-1">{bookmark.url}</p>
                      <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground uppercase tracking-wider mt-1">
                        {bookmark.favicon && (
                          <img
                            src={bookmark.favicon}
                            alt=""
                            className="w-3 h-3"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        )}
                        <span>{bookmark.domain}</span>
                        <span>•</span>
                        <span>{new Date(bookmark.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <Button
                        data-testid={`view-duplicate-${bookmark.id}`}
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0"
                        onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                      >
                        <ExternalLinkIcon className="w-3 h-3" />
                      </Button>
                      <Button
                        data-testid={`delete-duplicate-${bookmark.id}`}
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                        onClick={() => handleDelete(bookmark.id)}
                      >
                        <TrashIcon className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DuplicatesSection;
