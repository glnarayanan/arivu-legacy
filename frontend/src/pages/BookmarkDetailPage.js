import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeftIcon, ExternalLinkIcon, SparklesIcon, ListIcon, BookOpenIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const BookmarkDetailPage = ({ onLogout }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [bookmark, setBookmark] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchBookmark = async () => {
      try {
        const response = await axiosInstance.get(`/bookmarks/${id}`);
        setBookmark(response.data);
      } catch (error) {
        toast.error('Failed to load bookmark');
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchBookmark();
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!bookmark) return null;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 glassmorphism border-b border-border/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Button
              data-testid="back-btn"
              variant="ghost"
              size="sm"
              className="rounded-full"
              onClick={() => navigate('/dashboard')}
            >
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button
              data-testid="open-original-btn"
              variant="outline"
              size="sm"
              className="rounded-full"
              onClick={() => window.open(bookmark.url, '_blank')}
            >
              <ExternalLinkIcon className="w-4 h-4 mr-2" />
              Open Original
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Title & Metadata */}
        <div className="mb-8 space-y-4">
          <h1 className="font-heading text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
            {bookmark.title}
          </h1>
          {bookmark.description && (
            <p className="text-lg text-muted-foreground leading-relaxed">
              {bookmark.description}
            </p>
          )}
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {bookmark.favicon && (
              <img src={bookmark.favicon} alt="" className="w-5 h-5 rounded" onError={(e) => e.target.style.display = 'none'} />
            )}
            <span>{bookmark.domain}</span>
            <span>•</span>
            <span>{new Date(bookmark.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* AI Summaries Section */}
        {bookmark.ai_summary && bookmark.ai_summary.processing_status === 'completed' && (
          <div className="mb-8">
            <div className="rounded-2xl border border-violet-200 bg-violet-50/50 dark:border-violet-900/50 dark:bg-violet-950/10 p-6 space-y-6">
              <div className="flex items-center gap-2">
                <SparklesIcon className="w-5 h-5 ai-gradient" />
                <h2 className="font-heading text-xl font-semibold ai-gradient">AI Insights</h2>
              </div>

              <Tabs defaultValue="quick" className="w-full">
                <TabsList className="grid w-full grid-cols-3 rounded-xl">
                  <TabsTrigger data-testid="quick-summary-tab" value="quick" className="rounded-lg">
                    <ListIcon className="w-4 h-4 mr-2" />
                    Quick
                  </TabsTrigger>
                  <TabsTrigger data-testid="detailed-summary-tab" value="detailed" className="rounded-lg">
                    <BookOpenIcon className="w-4 h-4 mr-2" />
                    Detailed
                  </TabsTrigger>
                  <TabsTrigger data-testid="highlights-tab" value="highlights" className="rounded-lg">
                    <SparklesIcon className="w-4 h-4 mr-2" />
                    Highlights
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="quick" className="space-y-4 mt-4">
                  {/* One Sentence */}
                  {bookmark.ai_summary.one_sentence && (
                    <div>
                      <h3 className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Summary</h3>
                      <p className="font-reader text-lg leading-relaxed">
                        {bookmark.ai_summary.one_sentence}
                      </p>
                    </div>
                  )}

                  {/* Bullet Points */}
                  {bookmark.ai_summary.bullet_points && bookmark.ai_summary.bullet_points.length > 0 && (
                    <div>
                      <h3 className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Key Points</h3>
                      <ul className="space-y-2">
                        {bookmark.ai_summary.bullet_points.map((point, idx) => (
                          <li key={idx} className="flex gap-3">
                            <span className="text-violet-500 font-bold">•</span>
                            <span className="font-reader leading-relaxed">{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="detailed" className="mt-4">
                  {bookmark.ai_summary.long_form && (
                    <div className="prose prose-sm max-w-none font-reader leading-loose">
                      {bookmark.ai_summary.long_form.split('\n').map((para, idx) => (
                        <p key={idx} className="mb-4 leading-loose">{para}</p>
                      ))}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="highlights" className="space-y-3 mt-4">
                  {bookmark.ai_summary.highlights && bookmark.ai_summary.highlights.length > 0 ? (
                    bookmark.ai_summary.highlights.map((highlight, idx) => (
                      <div key={idx} className="border-l-4 border-yellow-400 bg-yellow-50/30 dark:bg-yellow-900/10 pl-4 py-2 rounded-r">
                        <p className="font-reader italic leading-relaxed">"{highlight}"</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-muted-foreground">No highlights extracted</p>
                  )}
                </TabsContent>
              </Tabs>

              {/* Tags */}
              {bookmark.ai_summary.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {bookmark.ai_summary.suggested_tags.map((tag, idx) => (
                      <span
                        key={idx}
                        data-testid={`tag-${tag}`}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm font-mono bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* AI Processing Status */}
        {bookmark.ai_summary?.processing_status === 'pending' && (
          <div className="mb-8 p-6 rounded-2xl border border-border bg-muted/30 flex items-center gap-3">
            <SparklesIcon className="w-5 h-5 animate-pulse ai-gradient" />
            <span className="text-muted-foreground">AI is processing summaries and insights...</span>
          </div>
        )}

        {/* Archived Content (Reader View) */}
        <div className="bg-card rounded-2xl border p-8 sm:p-12">
          <h2 className="font-heading text-2xl font-semibold mb-6">Archived Content</h2>
          {bookmark.html_content ? (
            <div
              className="reader-content font-reader prose prose-lg max-w-none"
              dangerouslySetInnerHTML={{ __html: bookmark.html_content }}
            />
          ) : bookmark.text_content ? (
            <div className="reader-content font-reader prose prose-lg max-w-none whitespace-pre-wrap">
              {bookmark.text_content}
            </div>
          ) : (
            <p className="text-muted-foreground">No content available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default BookmarkDetailPage;
