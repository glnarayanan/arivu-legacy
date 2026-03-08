import { useState, useEffect } from 'react';
import axiosInstance from '../utils/axiosConfig';
import { Button } from '../components/ui/button';
import {
  BarChart3, BookOpen, Clock, TrendingUp,
  BookmarkPlus, CheckCircle2, AlertCircle, Info, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { StaggerContainer, StaggerItem } from '../components/motion/PageOrchestrator';
import AppLayout from '../components/AppLayout';
import { useNavigate } from 'react-router-dom';
import { EmptyStateGuide } from '../components/onboarding';
import ErrorMessage from '../components/ErrorMessage';

const AnalyticsPage = ({ onLogout }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.get(`/analytics/summary?days=${days}`);
      setData(response.data);
    } catch (err) {
      const message = err.response?.status === 0
        ? 'Unable to connect. Check your internet connection.'
        : err.response?.data?.detail || 'Failed to load analytics';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const StatCard = ({ icon: Icon, label, value, sublabel }) => (
    <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
      <div className="flex items-center gap-3 mb-3">
        <div className="p-2 border-2 border-foreground bg-primary/10">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="font-display text-3xl font-bold">{value}</div>
      {sublabel && (
        <div className="text-xs text-muted-foreground mt-1 font-mono uppercase tracking-wider">
          {sublabel}
        </div>
      )}
    </div>
  );

  const TopicBar = ({ topic, count, maxCount, readingTime }) => {
    const width = maxCount > 0 ? (count / maxCount) * 100 : 0;
    return (
      <div className="py-3 border-b border-foreground/10 last:border-b-0">
        <div className="flex justify-between items-center mb-2">
          <span className="font-mono text-sm uppercase tracking-wider truncate max-w-[200px]">
            {topic}
          </span>
          <span className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
            {count} articles • {readingTime} min
          </span>
        </div>
        <div className="h-2 bg-muted border border-foreground/20">
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
      success: 'border-green-600 bg-green-50',
      warning: 'border-amber-600 bg-amber-50',
      info: 'border-accent bg-accent/10'
    };
    const iconColors = {
      success: 'text-green-600',
      warning: 'text-amber-600',
      info: 'text-accent'
    };
    const Icon = icons[insight.severity] || Info;
    const colorClass = colors[insight.severity] || colors.info;
    const iconColor = iconColors[insight.severity] || iconColors.info;

    return (
      <div className={`p-4 border-2 ${colorClass}`}>
        <div className="flex items-start gap-3">
          <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconColor}`} />
          <p className="text-sm font-mono">{insight.message}</p>
        </div>
      </div>
    );
  };

  return (
    <AppLayout
      onLogout={onLogout}
      showSearch={false}
      headerRight={
        <div className="flex items-center gap-2">
          {/* Time Period Selector */}
          <div className="flex gap-1 p-1 bg-background border-2 border-foreground">
            {[7, 30, 90].map((d) => (
              <Button
                key={d}
                variant={days === d ? 'default' : 'ghost'}
                size="sm"
                className={`h-8 px-3 rounded-none font-mono text-xs uppercase ${days === d ? 'bg-foreground text-background' : 'hover:bg-muted'
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
      }
    >
      <div className="px-6 py-6">
        {/* Page Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center justify-center w-10 h-10 border-2 border-foreground bg-primary text-primary-foreground">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-heading text-xl font-bold uppercase tracking-wide">Learning Analytics</h2>
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Track your reading progress and patterns
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin h-12 w-12 border-4 border-muted border-t-primary"></div>
          </div>
        ) : error ? (
          <ErrorMessage
            title="Failed to load analytics"
            message={error}
            onRetry={fetchAnalytics}
            retrying={loading}
          />
        ) : data ? (
          <StaggerContainer className="space-y-6">
            {/* Stats Grid */}
            <StaggerItem>
              <div className="mb-2">
                <h3 className="font-heading font-bold uppercase tracking-wide flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  Reading Stats ({days} days)
                </h3>
              </div>
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
                />
                <StatCard
                  icon={Clock}
                  label="Reading Time"
                  value={`${Math.round((data.stats?.total_reading_time_minutes || 0) / 60 * 10) / 10}h`}
                  sublabel={`~${data.stats?.avg_reading_time_per_article || 0} min/article`}
                />
              </div>
            </StaggerItem>

            {/* Topics Section */}
            {data.topics && data.topics.length > 0 && (
              <StaggerItem>
                <div className="mb-2">
                  <h3 className="font-heading font-bold uppercase tracking-wide flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Top Topics
                  </h3>
                </div>
                <div className="bg-card border-2 border-foreground p-6 shadow-brutal">
                  {data.topics.slice(0, 10).map((topic) => (
                    <TopicBar
                      key={topic.topic}
                      topic={topic.topic}
                      count={topic.count}
                      maxCount={data.topics[0]?.count || 1}
                      readingTime={topic.reading_time_minutes}
                    />
                  ))}
                </div>
              </StaggerItem>
            )}

            {/* Reading Patterns */}
            {data.patterns && data.patterns.total_sessions > 0 && (
              <StaggerItem>
                <div className="mb-2">
                  <h3 className="font-heading font-bold uppercase tracking-wide flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Reading Patterns
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
                    <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                      Peak Reading Time
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.peak_hour_label || '--:--'}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono uppercase tracking-wider">
                      {data.patterns.peak_hour_count} sessions
                    </div>
                  </div>
                  <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
                    <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                      Weekday Reading
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.weekday_percent || 0}%
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono uppercase tracking-wider">
                      vs {data.patterns.weekend_percent || 0}% weekends
                    </div>
                  </div>
                  <div className="bg-card border-2 border-foreground p-5 shadow-brutal">
                    <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                      Total Sessions
                    </div>
                    <div className="font-display text-2xl font-bold">
                      {data.patterns.total_sessions || 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 font-mono uppercase tracking-wider">
                      reading sessions tracked
                    </div>
                  </div>
                </div>
              </StaggerItem>
            )}

            {/* Insights */}
            {data.insights && data.insights.length > 0 && (
              <StaggerItem>
                <div className="mb-2">
                  <h3 className="font-heading font-bold uppercase tracking-wide flex items-center gap-2">
                    <Info className="w-5 h-5" />
                    Insights
                  </h3>
                </div>
                <div className="space-y-3">
                  {data.insights.map((insight, index) => (
                    <InsightCard key={index} insight={insight} />
                  ))}
                </div>
              </StaggerItem>
            )}

            {/* Empty State */}
            {(!data.topics || data.topics.length === 0) &&
              (!data.insights || data.insights.length === 0) &&
              data.stats?.total_bookmarks === 0 && (
                <StaggerItem>
                  <EmptyStateGuide
                    type="analytics"
                    onPrimaryAction={() => navigate('/dashboard')}
                  />
                </StaggerItem>
              )}
          </StaggerContainer>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground font-mono">Failed to load analytics</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default AnalyticsPage;
