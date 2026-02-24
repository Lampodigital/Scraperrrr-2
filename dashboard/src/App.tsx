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
  LayoutGrid,
  ChevronRight,
  Heart
} from 'lucide-react'
import NeuralHeroDemo from './components/NeuralHeroDemo'

interface Story {
  id: string;
  title: string;
  url: string;
  summary: string;
  thumbnail: string | null;
}

interface Article {
  id: string;
  type: 'edition' | 'article';
  title: string;
  source: string;
  url: string;
  resume: string | null;
  summary: string | null; // Keep for backward compatibility/reddit
  published_at: string;
  thumbnail: string | null;
  stories: Story[];
}

interface DashboardData {
  last_updated: string;
  articles: Article[];
}

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedEditions, setExpandedEditions] = useState<Set<string>>(new Set());

  // Persistence: Editions and Individual Stories
  const [savedIds, setSavedIds] = useState<string[]>(() => {
    const saved = localStorage.getItem('saved_items');
    return saved ? JSON.parse(saved) : [];
  });

  const [filter, setFilter] = useState<'all' | 'newsletters' | 'reddit' | 'saved'>('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    setLoading(true);
    const MODAL_URL = 'https://stefanorossiw93--glaido-scraper-get-data.modal.run';
    fetch(MODAL_URL)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load news data:", err);
        fetch('/data.json')
          .then(r => r.json())
          .then(d => {
            setData(d);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  };

  useEffect(() => {
    localStorage.setItem('saved_items', JSON.stringify(savedIds));
  }, [savedIds]);

  const toggleSave = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSavedIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
  };

  const isSaved = (id: string) => savedIds.includes(id);

  const toggleExpanded = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedEditions(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const filteredArticles = (data?.articles || []).filter(a => {
    if (filter === 'saved') {
      // Show edition if saved, OR show edition if ANY of its stories are saved
      const editionSaved = isSaved(a.id);
      const storySaved = a.stories?.some(s => isSaved(s.id));
      return editionSaved || storySaved;
    }
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
            <div className="stat-label">Editions</div>
          </div>
          <div className="stat-box">
            <div className="stat-value">{stats.saved}</div>
            <div className="stat-label">Pinned</div>
          </div>
        </div>
      </header>

      <nav className="nav-bar">
        <div className="tabs-container">
          <button className={`tab-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
            <Globe size={18} /><span>All Sources</span>
          </button>
          <button className={`tab-btn ${filter === 'newsletters' ? 'active' : ''}`} onClick={() => setFilter('newsletters')}>
            <Newspaper size={18} /><span>Editions</span>
          </button>
          <button className={`tab-btn ${filter === 'reddit' ? 'active' : ''}`} onClick={() => setFilter('reddit')}>
            <MessageSquare size={18} /><span>Community</span>
          </button>
          <button className={`tab-btn ${filter === 'saved' ? 'active' : ''}`} onClick={() => setFilter('saved')}>
            <Save size={18} /><span>Collection</span>
          </button>
        </div>

        <button className="refresh-btn" onClick={fetchData}>
          <RefreshCcw size={16} /><span>Refresh</span>
        </button>
      </nav>

      <div className="px-[40px] pt-4 pb-2">
        <NeuralHeroDemo />
      </div>

      <main className="feed-grid">
        <AnimatePresence mode="popLayout">
          {filteredArticles.map((article, index) => (
            <motion.div
              layout
              key={article.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.02 }}
              className={`article-card ${article.type === 'edition' ? 'edition-mode' : ''}`}
            >
              <div className="image-container relative">
                {article.thumbnail ? (
                  <img src={article.thumbnail} alt="" className="article-image" />
                ) : (
                  <div className="image-placeholder">
                    <LayoutGrid size={48} className="text-white opacity-5" />
                  </div>
                )}
                <div className="absolute top-4 left-4 source-tag bg-black/60 backdrop-blur-md border border-white/10 uppercase tracking-widest text-[10px] py-1 px-3 rounded-full flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${article.source === 'Reddit' ? 'bg-orange-500' : 'bg-[#BFF549]'}`}></div>
                  {article.source}
                </div>
                <button
                  className={`absolute top-4 right-4 p-2 rounded-full transition-all ${isSaved(article.id) ? 'bg-[#BFF549] text-black scale-110' : 'bg-black/40 text-white hover:bg-white/20'}`}
                  onClick={(e) => toggleSave(article.id, e)}
                >
                  <Bookmark size={18} fill={isSaved(article.id) ? "black" : "none"} />
                </button>
              </div>

              <div className="card-content">
                <h3 className="article-title text-xl font-bold leading-tight mb-4">{article.title}</h3>

                {article.type === 'edition' && article.resume && (
                  <div className="edition-resume">
                    {article.resume}
                  </div>
                )}

                {!article.resume && article.summary && (
                  <p className="article-summary text-muted text-sm line-clamp-2 mb-4">
                    {article.summary}
                  </p>
                )}

                {/* NESTED STORIES */}
                {article.stories && article.stories.length > 0 && (
                  <div className="nested-stories-container border-t border-white/5 pt-4 mt-2 space-y-2">
                    <div className="text-[10px] uppercase font-bold tracking-widest text-muted/60 mb-2 flex items-center gap-2">
                      <ChevronRight size={12} className="text-[#BFF549]" />
                      Highlights
                    </div>
                    {(expandedEditions.has(article.id) ? article.stories : article.stories.slice(0, 3)).map(story => (
                      <div key={story.id} className={`story-item group transition-all ${isSaved(story.id) ? 'saved' : ''}`}>
                        <div className="flex justify-between items-start gap-4">
                          <div className="flex-1 min-w-0">
                            <h4 className="text-[14px] font-semibold text-white/90 group-hover:text-[#BFF549] transition-colors truncate">{story.title}</h4>
                            <p className="text-[12px] text-muted line-clamp-1 mt-0.5 opacity-60 leading-relaxed font-mono">{story.summary}</p>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={(e) => toggleSave(story.id, e)}
                              className={`p-1.5 rounded-lg transition-all ${isSaved(story.id) ? 'text-[#BFF549]' : 'text-muted/40 hover:text-white'}`}
                            >
                              <Heart size={14} fill={isSaved(story.id) ? "currentColor" : "none"} />
                            </button>
                            <a href={story.url} target="_blank" rel="noopener" className="p-1.5 rounded-lg text-muted/40 hover:text-white">
                              <ExternalLink size={14} />
                            </a>
                          </div>
                        </div>
                      </div>
                    ))}
                    {article.stories.length > 3 && (
                      <button
                        onClick={(e) => toggleExpanded(article.id, e)}
                        className="w-full mt-2 py-2 text-[11px] font-bold text-[#BFF549]/70 hover:text-[#BFF549] border border-white/5 hover:border-[#BFF549]/30 rounded-lg transition-all flex items-center justify-center gap-1.5"
                      >
                        <ChevronRight size={12} className={`transition-transform ${expandedEditions.has(article.id) ? 'rotate-90' : ''}`} />
                        {expandedEditions.has(article.id) ? `Show fewer` : `${article.stories.length - 3} more highlights`}
                      </button>
                    )}
                  </div>
                )}

                <div className="card-footer mt-auto pt-4 flex justify-between items-center">
                  <div className="date-text text-xs opacity-40">{formatTime(article.published_at)}</div>
                  <a href={article.url} target="_blank" rel="noopener" className="flex items-center gap-2 text-[10px] font-black tracking-tighter text-[#BFF549] hover:brightness-125 transition-all">
                    {article.type === 'edition' ? 'FULL NEWSLETTER' : 'FULL SOURCE'} <ChevronRight size={14} />
                  </a>
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
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));

    if (isNaN(date.getTime())) return isoString;
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch { return isoString; }
}

export default App
