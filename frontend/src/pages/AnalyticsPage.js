import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import {
  BarChart3, BookOpen, Clock, TrendingUp, ArrowLeft,
  BookmarkPlus, CheckCircle2, AlertCircle, Info, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';

const AnalyticsPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/analytics/summary?days=${days}`);
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const StatCard = ({ icon: Icon, label, value, sublabel, color = 'primary' }) => (
    <div className="bg-card border-2 border-foreground p-4 shadow-brutal">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 border-2 border-foreground bg-${color}/10`}>
          <Icon className={`w-5 h-5 text-${color}`} />
        </div>
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="font-display text-3xl font-bold">{value}</div>
      {sublabel && (
        <div className="text-xs text-muted-foreground mt-1 font-mono uppercase">
          {sublabel}
        </div>
      )}
    </div>
  );

  const TopicBar = ({ topic, count, maxCount, readingTime }) => {
    const width = maxCount > 0 ? (count / maxCount) * 100 : 0;
    return (
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1">
          <span className="font-mono text-sm uppercase truncate max-w-[200px]">
            {topic}
          </span>
          <span className="text-xs text-muted-foreground font-mono">
            {count} articles • {readingTime} min
          </span>
        </div>
        <div className="h-3 bg-muted border border-foreground/20">
          <div
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${width}%` }}
          />
        </div>
      </div>
    );
  };

  const InsightCard = ({ insight }) => {
    const icons = {
      success: CheckCircle2,
      warning: AlertCircle,
      info: Info
    };
    const colors = {
      success: 'text-green-600 bg-green-50 border-green-600',
      warning: 'text-amber-600 bg-amber-50 border-amber-600',
      info: 'text-blue-600 bg-blue-50 border-blue-600'
    };
    const Icon = icons[insight.severity] || Info;
    const colorClass = colors[insight.severity] || colors.info;

    return (
      <div className={`p-4 border-2 ${colorClass}`}>
        <div className="flex items-start gap-3">
          <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm font-mono">{insight.message}</p>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card border-b-2 border-foreground">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/dashboard')}
                className="rounded-none border-2 border-transparent hover:border-foreground"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                BACK
              </Button>
              <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground shadow-brutal">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h1 className="font-display text-2xl font-bold tracking-wide uppercase">
                Learning Analytics
              </h1>
            </div>
            <div className="flex items-center gap-2">
              {/* Time Period Selector */}
              <div className="flex gap-1 p-1 bg-background border-2 border-foreground">
                {[7, 30, 90].map((d) => (
                  <Button
                    key={d}
                    variant={days === d ? 'default' : 'ghost'}
                    size="sm"
                    className={`h-8 px-3 rounded-none font-mono text-xs ${days === d ? 'bg-foreground text-background' : 'hover:bg-muted'
                      }`}
                    onClick={() => setDays(d)}
                  >
                    {d}D
                  </Button>
                ))}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchAnalytics}
                disabled={loading}
                className="rounded-none border-2 border-transparent hover:border-foreground"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
          </div>
        ) : data ? (
          <div className="space-y-8">
            {/* Stats Grid */}
            <section>
              <h2 className="font-heading font-bold uppercase tracking-wide mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Reading Stats ({days} days)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  icon={BookmarkPlus}
                  label="Bookmarks Saved"
                  value={data.stats?.bookmarks_saved_in_period || 0}
                  sublabel={`${data.stats?.total_bookmarks || 0} total`}
                />
                <StatCard
                  icon={BookOpen}
                  label="Articles Read"
                  value={data.stats?.bookmarks_read_in_period || 0}
                  sublabel={`${data.stats?.unread_count || 0} unread`}
                />
                <StatCard
                  icon={CheckCircle2}
                  label="Completion Rate"
                  value={`${data.stats?.completion_rate || 0}%`}
                  color={data.stats?.completion_rate >= 50 ? 'green' : 'amber'}
                />
                <StatCard
                  icon={Clock}
                  label="Reading Time"
                  value={`${Math.round((data.stats?.total_reading_time_minutes || 0) / 60 * 10) / 10}h`}
                  sublabel={`~${data.stats?.avg_reading_time_per_article || 0} min/article`}
                />
              </div>
            </section>

            {/* Topics Section */}
            {data.topics && data.topics.length > 0 && (
              <section>
                <h2 className="font-heading font-bold uppercase tracking-wide mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Top Topics
                </h2>
                <div className="bg-card border-2 border-foreground p-6">
                  {data.topics.slice(0, 10).map((topic, index) => (
                    <TopicBar
                      key={topic.topic}
                      topic={topic.topic}
                      count={topic.count}
                      maxCount={data.topics[0]?.count || 1}
                      readingTime={topic.reading_time_minutes}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Reading Patterns */}
            {data.patterns && data.patterns.total_sessions > 0 && (
              <section>
                <h2 className="font-heading font-bold uppercase tracking-wide mb-4 flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Reading Patterns
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-card border-2 border-foreground p-4">
                    <div className="font-mono text-xs uppercase text-muted-foreground mb-1">
                      Peak Reading Time
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.peak_hour_label || '--:--'}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono">
                      {data.patterns.peak_hour_count} sessions
                    </div>
                  </div>
                  <div className="bg-card border-2 border-foreground p-4">
                    <div className="font-mono text-xs uppercase text-muted-foreground mb-1">
                      Weekday Reading
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.weekday_percent || 0}%
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono">
                      vs {data.patterns.weekend_percent || 0}% weekends
                    </div>
                  </div>
                  <div className="bg-card border-2 border-foreground p-4">
                    <div className="font-mono text-xs uppercase text-muted-foreground mb-1">
                      Total Sessions
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.total_sessions || 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono">
                      reading sessions tracked
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* Insights */}
            {data.insights && data.insights.length > 0 && (
              <section>
                <h2 className="font-heading font-bold uppercase tracking-wide mb-4 flex items-center gap-2">
                  <Info className="w-5 h-5" />
                  Insights
                </h2>
                <div className="space-y-3">
                  {data.insights.map((insight, index) => (
                    <InsightCard key={index} insight={insight} />
                  ))}
                </div>
              </section>
            )}

            {/* Empty State */}
            {(!data.topics || data.topics.length === 0) &&
              (!data.insights || data.insights.length === 0) &&
              data.stats?.total_bookmarks === 0 && (
                <div className="text-center py-12 border-2 border-dashed border-muted-foreground/20">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="font-heading text-xl mb-2">No analytics yet</h3>
                  <p className="text-muted-foreground font-mono text-sm">
                    Start saving and reading bookmarks to see your learning analytics
                  </p>
                </div>
              )}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Failed to load analytics</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPage;
