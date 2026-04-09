import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { ArrowLeftIcon, ExternalLinkIcon, SparklesIcon, ListIcon, NetworkIcon, Shield, CheckCircle2, AlertTriangle, Clock as _u6_Clock } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { motion } from 'framer-motion';
import DOMPurify from 'dompurify';
import { HardReveal, StaggerContainer, StaggerItem } from '../components/motion/PageOrchestrator';

const BookmarkDetailPage = ({ _u12_onLogout }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [bookmark, setBookmark] = useState(null);
  const [loading, setLoading] = useState(true);
  const [relatedBookmarks, setRelatedBookmarks] = useState([]);
  const [loadingRelated, setLoadingRelated] = useState(false);
  const [contentQuality, setContentQuality] = useState(null);

  useEffect(() => {
    const fetchBookmark = async () => {
      try {
        const response = await axiosInstance.get(`/bookmarks/${id}`);
        setBookmark(response.data);
      } catch (_u26_error) {
        toast.error('Failed to load bookmark');
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchBookmark();
  }, [id, navigate]);

  useEffect(() => {
    const fetchRelatedBookmarks = async () => {
      if (!bookmark) return;

      setLoadingRelated(true);
      try {
        const response = await axiosInstance.get(`/bookmarks/${id}/related?limit=5`);
        if (response.data.related) {
          setRelatedBookmarks(response.data.related);
        }
      } catch (error) {
        console.error('Failed to load related bookmarks:', error);
      } finally {
        setLoadingRelated(false);
      }
    };

    fetchRelatedBookmarks();
  }, [id, bookmark]);

  // Fetch content quality score
  useEffect(() => {
    const fetchContentQuality = async () => {
      if (!bookmark?.url || !bookmark?.text_content) return;

      try {
        const response = await axiosInstance.post('/content/evaluate', {
          url: bookmark.url,
          content: bookmark.text_content,
          metadata: {
            author: bookmark.author,
            publication_date: bookmark.publication_date
          }
        });
        setContentQuality(response.data);
      } catch (error) {
        console.error('Failed to evaluate content quality:', error);
      }
    };

    fetchContentQuality();
  }, [bookmark]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
      </div>
    );
  }

  if (!bookmark) return null;

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <HardReveal direction="down">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <Button
                data-testid="back-btn"
                variant="ghost"
                size="sm"
                onClick={() => navigate('/dashboard')}
              >
                <ArrowLeftIcon className="w-4 h-4 mr-2" />
                BACK
              </Button>
              <Button
                data-testid="open-original-btn"
                variant="outline"
                size="sm"
                onClick={() => window.open(bookmark.url, '_blank')}
              >
                <ExternalLinkIcon className="w-4 h-4 mr-2" />
                OPEN ORIGINAL
              </Button>
            </div>
          </div>
        </HardReveal>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <StaggerContainer>
          <StaggerItem>
            <div className="mb-8 space-y-4">
              <h1 className="font-display text-4xl sm:text-5xl tracking-wide uppercase leading-tight">
                {bookmark.title}
              </h1>
              {bookmark.description && (
                <p className="text-lg text-muted-foreground leading-relaxed">
                  {bookmark.description}
                </p>
              )}
              <div className="flex items-center gap-3 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                {bookmark.favicon && (
                  <img src={bookmark.favicon} alt="" className="w-5 h-5 border border-foreground" onError={(e) => e.target.style.display = 'none'} />
                )}
                <span>{bookmark.domain}</span>
                <span className="text-foreground">•</span>
                <span>{new Date(bookmark.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </StaggerItem>

          {/* Content Quality Score */}
          {contentQuality && (
            <StaggerItem>
              <div className="mb-6 flex flex-wrap items-center gap-3">
                <div className={`flex items-center gap-2 px-3 py-1.5 border-2 ${contentQuality.score >= 70 ? 'border-green-600 bg-green-50 text-green-700' :
                    contentQuality.score >= 50 ? 'border-amber-500 bg-amber-50 text-amber-700' :
                      'border-red-500 bg-red-50 text-red-700'
                  }`}>
                  <Shield className="w-4 h-4" />
                  <span className="font-mono text-xs uppercase tracking-wider">
                    {contentQuality.label}: {contentQuality.score}/100
                  </span>
                </div>
                {contentQuality.badges?.map((badge, idx) => (
                  <span
                    key={idx}
                    className={`px-2 py-1 text-xs font-mono uppercase tracking-wider border ${badge.type === 'positive' ? 'border-green-500 bg-green-50 text-green-700' :
                        badge.type === 'negative' ? 'border-red-400 bg-red-50 text-red-600' :
                          'border-gray-400 bg-gray-50 text-gray-600'
                      }`}
                  >
                    {badge.type === 'positive' && <CheckCircle2 className="w-3 h-3 inline mr-1" />}
                    {badge.type === 'negative' && <AlertTriangle className="w-3 h-3 inline mr-1" />}
                    {badge.text}
                  </span>
                ))}
              </div>
            </StaggerItem>
          )}

          {bookmark.ai_summary && bookmark.ai_summary.processing_status === 'completed' && (
            <StaggerItem>
              <div className="mb-8">
                <div className="border-2 border-accent bg-accent/10 p-6 space-y-6">
                  <div className="flex items-center gap-2 border-b-2 border-accent pb-4">
                    <SparklesIcon className="w-5 h-5 text-accent" />
                    <h2 className="font-display text-xl uppercase tracking-wide text-accent">AI Insights</h2>
                  </div>

                  <Tabs defaultValue="quick" className="w-full">
                    <TabsList className="grid w-full grid-cols-2 bg-background border-2 border-foreground p-1">
                      <TabsTrigger data-testid="quick-summary-tab" value="quick" className="data-[state=active]:bg-foreground data-[state=active]:text-background font-mono text-xs uppercase tracking-wider">
                        <ListIcon className="w-4 h-4 mr-2" />
                        Summary
                      </TabsTrigger>
                      <TabsTrigger data-testid="detailed-summary-tab" value="detailed" className="data-[state=active]:bg-foreground data-[state=active]:text-background font-mono text-xs uppercase tracking-wider">
                        <SparklesIcon className="w-4 h-4 mr-2" />
                        Highlights
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="quick" className="space-y-4 mt-4">
                      {bookmark.ai_summary.one_sentence && (
                        <div>
                          <h3 className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-2">TL;DR</h3>
                          <p className="text-lg leading-relaxed font-medium">
                            {bookmark.ai_summary.one_sentence}
                          </p>
                        </div>
                      )}

                      {/* Exec Summary - new field, fallback to long_form for backward compat */}
                      {(bookmark.ai_summary.exec_summary || bookmark.ai_summary.long_form) && (
                        <div>
                          <h3 className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-2">Executive Summary</h3>
                          <div className="prose prose-sm max-w-none">
                            {(bookmark.ai_summary.exec_summary || bookmark.ai_summary.long_form).split('\n').filter(p => p.trim()).map((para, idx) => (
                              <p key={idx} className="mb-3 leading-relaxed text-foreground/90">{para}</p>
                            ))}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="detailed" className="mt-4">
                      {bookmark.ai_summary.highlights && bookmark.ai_summary.highlights.length > 0 ? (
                        <div className="space-y-3">
                          {bookmark.ai_summary.highlights.map((highlight, idx) => (
                            <div key={idx} className="border-l-4 border-primary bg-primary/5 pl-4 py-3">
                              <p className="leading-relaxed">{highlight}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-muted-foreground font-mono text-sm">No highlights extracted</p>
                      )}
                    </TabsContent>
                  </Tabs>

                  {bookmark.ai_summary.suggested_tags && bookmark.ai_summary.suggested_tags.length > 0 && (
                    <div className="pt-4 border-t-2 border-accent">
                      <h3 className="font-mono text-xs uppercase tracking-widest text-muted-foreground mb-2">Tags</h3>
                      <div className="flex flex-wrap gap-2">
                        {bookmark.ai_summary.suggested_tags.map((tag, idx) => (
                          <span
                            key={idx}
                            data-testid={`tag-${tag}`}
                            className="inline-flex items-center px-3 py-1 border border-accent bg-accent text-accent-foreground font-mono text-xs uppercase tracking-wider"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </StaggerItem>
          )}

          {bookmark.ai_summary?.processing_status === 'pending' && (
            <StaggerItem>
              <div className="mb-8 p-6 border-2 border-foreground bg-muted flex items-center gap-3">
                <SparklesIcon className="w-5 h-5 animate-pulse text-accent" />
                <span className="text-muted-foreground font-mono text-sm uppercase tracking-wider">AI is processing summaries and insights...</span>
              </div>
            </StaggerItem>
          )}

          {/* Semantic Knowledge Graph: Related Bookmarks */}
          {relatedBookmarks.length > 0 && (
            <StaggerItem>
              <div className="mb-8">
                <div className="border-2 border-foreground bg-card p-6 shadow-brutal">
                  <div className="flex items-center gap-2 mb-6 pb-4 border-b-2 border-foreground">
                    <NetworkIcon className="w-5 h-5 text-foreground" />
                    <h2 className="font-display text-xl uppercase tracking-wide">Related Bookmarks</h2>
                    <span className="ml-auto font-mono text-xs uppercase tracking-wider text-muted-foreground">
                      Semantic Connections
                    </span>
                  </div>

                  <div className="space-y-4">
                    {relatedBookmarks.map((related) => (
                      <motion.div
                        key={related.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                        className="border-2 border-foreground bg-background p-4 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none shadow-brutal-sm transition-all duration-150 cursor-pointer"
                        onClick={() => navigate(`/bookmark/${related.id}`)}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              {related.favicon && (
                                <img
                                  src={related.favicon}
                                  alt=""
                                  className="w-4 h-4 border border-foreground flex-shrink-0"
                                  onError={(e) => (e.target.style.display = 'none')}
                                />
                              )}
                              <h3 className="font-semibold text-sm truncate">{related.title || 'Untitled'}</h3>
                            </div>
                            {related.description && (
                              <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                                {related.description}
                              </p>
                            )}
                            <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                              <span>{related.domain}</span>
                              {related.concepts && related.concepts.length > 0 && (
                                <>
                                  <span>•</span>
                                  <div className="flex gap-1 flex-wrap">
                                    {related.concepts.slice(0, 3).map((concept, idx) => (
                                      <span
                                        key={idx}
                                        className="px-1 py-0.5 border border-foreground bg-muted text-[9px]"
                                      >
                                        {concept}
                                      </span>
                                    ))}
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                          <div className="flex-shrink-0">
                            <div className="font-mono text-xs text-accent border border-accent px-2 py-1 bg-accent/10">
                              {Math.round(related.similarity_score * 100)}%
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  {relatedBookmarks.length >= 5 && (
                    <div className="mt-6 pt-4 border-t-2 border-foreground">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate('/knowledge-graph')}
                        className="w-full font-mono uppercase tracking-wider"
                      >
                        <NetworkIcon className="w-4 h-4 mr-2" />
                        Explore Knowledge Graph
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </StaggerItem>
          )}

          {loadingRelated && !relatedBookmarks.length && (
            <StaggerItem>
              <div className="mb-8 p-6 border-2 border-foreground bg-muted flex items-center gap-3">
                <NetworkIcon className="w-5 h-5 animate-pulse text-foreground" />
                <span className="text-muted-foreground font-mono text-sm uppercase tracking-wider">Finding related bookmarks...</span>
              </div>
            </StaggerItem>
          )}

          <StaggerItem>
            <div className="bg-card border-2 border-foreground p-8 sm:p-12 shadow-brutal">
              <h2 className="font-display text-2xl uppercase tracking-wide mb-6 pb-4 border-b-2 border-foreground">Archived Content</h2>
              {bookmark.html_content ? (
                <div
                  className="reader-content prose prose-lg max-w-none"
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(bookmark.html_content, {
                      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'b', 'i', 'u', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'img', 'div', 'span', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
                      ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class'],
                      ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
                    })
                  }}
                />
              ) : bookmark.text_content ? (
                <div className="reader-content prose prose-lg max-w-none whitespace-pre-wrap">
                  {bookmark.text_content}
                </div>
              ) : (
                <p className="text-muted-foreground font-mono text-sm uppercase">No content available</p>
              )}
            </div>
          </StaggerItem>
        </StaggerContainer>
      </div>
    </div>
  );
};

export default BookmarkDetailPage;
