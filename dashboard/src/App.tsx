import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Globe,
  MessageSquare,
  Bookmark,
  RefreshCcw,
  ExternalLink,
  Zap,
  Newspaper,
  Save,
  LayoutGrid
} from 'lucide-react'
import NeuralHeroDemo from './components/NeuralHeroDemo'

interface Article {
  id: string;
  title: string;
  source: string;
  url: string;
  summary: string | null;
  published_at: string;
  thumbnail: string | null;
  tags: string[];
}

interface DashboardData {
  last_updated: string;
  articles: Article[];
}

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [savedIds, setSavedIds] = useState<string[]>(() => {
    const saved = localStorage.getItem('saved_articles');
    return saved ? JSON.parse(saved) : [];
  });
  const [filter, setFilter] = useState<'all' | 'newsletters' | 'reddit' | 'saved'>('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    setLoading(true);
    fetch('/data.json')
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load news data:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    localStorage.setItem('saved_articles', JSON.stringify(savedIds));
  }, [savedIds]);

  const toggleSave = (id: string) => {
    setSavedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const filteredArticles = (data?.articles || []).filter(a => {
    if (filter === 'saved') return savedIds.includes(a.id);
    if (filter === 'newsletters') return a.source !== 'Reddit';
    if (filter === 'reddit') return a.source === 'Reddit';
    return true;
  });

  const stats = {
    total: data?.articles.length || 0,
    saved: savedIds.length
  };

  if (loading && !data) return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
        <RefreshCcw size={40} className="text-[#BFF549]" />
      </motion.div>
    </div>
  );

  return (
    <div className="dashboard-root">
      {/* Header Section */}
      <header className="header">
        <div className="title-container">
          <div className="logo-icon">
            <Zap size={22} fill="black" strokeWidth={3} className="text-black" />
          </div>
          <span className="brand-name">Glaido</span>
          <div className="divider"></div>
          <span className="sub-title">AI News</span>
        </div>

        <div className="stats-container">
          <div className="stat-box">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Articles</div>
          </div>
          <div className="stat-box">
            <div className="stat-value">{stats.saved}</div>
            <div className="stat-label">Saved</div>
          </div>
        </div>
      </header>

      {/* Navigation Layer */}
      <nav className="nav-bar">
        <div className="tabs-container">
          <button
            className={`tab-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            <Globe size={18} />
            <span>All Sources</span>
          </button>
          <button
            className={`tab-btn ${filter === 'newsletters' ? 'active' : ''}`}
            onClick={() => setFilter('newsletters')}
          >
            <Newspaper size={18} />
            <span>Newsletters</span>
          </button>
          <button
            className={`tab-btn ${filter === 'reddit' ? 'active' : ''}`}
            onClick={() => setFilter('reddit')}
          >
            <MessageSquare size={18} />
            <span>Community</span>
          </button>
          <button
            className={`tab-btn ${filter === 'saved' ? 'active' : ''}`}
            onClick={() => setFilter('saved')}
          >
            <Save size={18} />
            <span>Saved</span>
          </button>
        </div>

        <button className="refresh-btn" onClick={fetchData}>
          <RefreshCcw size={16} />
          <span>Refresh</span>
        </button>
      </nav>

      {/* Hero Section */}
      <div className="px-[40px] pt-4 pb-2">
        <NeuralHeroDemo />
      </div>

      {/* Main Content Grid */}
      <main className="feed-grid">
        <AnimatePresence mode="popLayout">
          {filteredArticles.map((article, index) => (
            <motion.div
              layout
              key={article.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.02 }}
              className="article-card"
            >
              <div className="image-container">
                {article.thumbnail ? (
                  <img src={article.thumbnail} alt="" className="article-image" />
                ) : (
                  <div className="image-placeholder">
                    <LayoutGrid size={48} className="text-white opacity-5" />
                  </div>
                )}
              </div>

              <div className="card-content">
                <div className="source-tag">{article.source}</div>
                <h3 className="article-title">{article.title}</h3>
                {article.summary && (
                  <p className="article-summary">{article.summary}</p>
                )}

                <div className="card-footer">
                  <div className="date-text">{formatTime(article.published_at)}</div>
                  <div className="flex gap-4">
                    <button
                      className={`save-action-btn ${savedIds.includes(article.id) ? 'active' : ''}`}
                      onClick={() => toggleSave(article.id)}
                    >
                      <Bookmark size={20} fill={savedIds.includes(article.id) ? "currentColor" : "none"} />
                    </button>
                    <a href={article.url} target="_blank" rel="noopener" className="text-muted hover:text-white">
                      <ExternalLink size={20} />
                    </a>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </main>

      {filteredArticles.length === 0 && (
        <div className="flex flex-col items-center justify-center p-20 opacity-20">
          <Newspaper size={64} strokeWidth={1} />
          <p className="mt-4 font-bold text-lg">No content found</p>
        </div>
      )}
    </div>
  )
}

function formatTime(isoString: string) {
  const date = new Date(isoString);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));

  if (diffInHours < 1) return 'Just now';
  if (diffInHours < 24) return `${diffInHours}h ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export default App
