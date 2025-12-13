import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeftIcon, CopyIcon, MergeIcon, TrashIcon, ExternalLinkIcon } from 'lucide-react';

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
      {/* Header */}
      <header className="sticky top-0 z-40 glassmorphism border-b border-border/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                data-testid="back-to-dashboard-btn"
                variant="ghost"
                size="sm"
                className="rounded-full"
                onClick={() => navigate('/dashboard')}
              >
                <ArrowLeftIcon className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div className="flex items-center gap-3">
                <h1 className="font-heading text-2xl font-bold tracking-tight">Duplicate Detection</h1>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          </div>
        ) : duplicates.length === 0 ? (
          <div className="text-center py-20">
            <CopyIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="font-heading text-2xl font-semibold mb-2">No duplicates found</h2>
            <p className="text-muted-foreground mb-6">Your bookmarks are clean and organized!</p>
            <Button
              data-testid="go-back-btn"
              variant="outline"
              className="rounded-full"
              onClick={() => navigate('/dashboard')}
            >
              Back to Dashboard
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="mb-4">
              <p className="text-muted-foreground">
                Found {duplicates.length} duplicate group{duplicates.length !== 1 ? 's' : ''}
              </p>
            </div>

            {duplicates.map((duplicate, idx) => (
              <div
                key={idx}
                data-testid={`duplicate-group-${idx}`}
                className="bg-card border rounded-2xl p-6 space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CopyIcon className="w-5 h-5 text-muted-foreground" />
                    <span className="font-medium">
                      {duplicate.type === 'exact_url' ? 'Same URL' : 'Similar Content'}
                    </span>
                    {duplicate.similarity && (
                      <span className="text-sm text-muted-foreground">
                        ({Math.round(duplicate.similarity * 100)}% similar)
                      </span>
                    )}
                  </div>
                  <Button
                    data-testid={`merge-group-${idx}`}
                    size="sm"
                    variant="outline"
                    className="rounded-full"
                    onClick={() => handleMerge(duplicate.bookmarks)}
                  >
                    <MergeIcon className="w-4 h-4 mr-2" />
                    Merge All
                  </Button>
                </div>

                <div className="space-y-3">
                  {duplicate.bookmarks.map((bookmark) => (
                    <div
                      key={bookmark.id}
                      data-testid={`duplicate-bookmark-${bookmark.id}`}
                      className="flex items-start gap-4 p-4 rounded-xl bg-muted/50 border border-border/50"
                    >
                      {bookmark.thumbnail && (
                        <img
                          src={bookmark.thumbnail}
                          alt={bookmark.title}
                          className="w-24 h-16 rounded-lg object-cover flex-shrink-0"
                          onError={(e) => e.target.style.display = 'none'}
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium line-clamp-1 mb-1">{bookmark.title}</h3>
                        <p className="text-sm text-muted-foreground line-clamp-1 mb-2">{bookmark.url}</p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {bookmark.favicon && (
                            <img
                              src={bookmark.favicon}
                              alt=""
                              className="w-4 h-4 rounded"
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
                          className="h-8 w-8 p-0 rounded-full"
                          onClick={() => navigate(`/bookmark/${bookmark.id}`)}
                        >
                          <ExternalLinkIcon className="w-4 h-4" />
                        </Button>
                        <Button
                          data-testid={`delete-duplicate-${bookmark.id}`}
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 rounded-full text-destructive hover:text-destructive"
                          onClick={() => handleDelete(bookmark.id)}
                        >
                          <TrashIcon className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DuplicatesPage;
