import { useState, useCallback } from 'react';
import {
  Sparkles,
  Search,
  Copy,
  Check,
  Zap,
  Command,
  BrainCircuit,
  Filter,
} from 'lucide-react';

const PROMPT_CATEGORIES = ['All', 'Analysis', 'Coding', 'Writing', 'Research', 'Creative'];

const SAMPLE_PROMPTS = [
  { id: 1, title: 'Deep Dive Analysis', text: 'Take a deep dive into this. Explore all angles, identify hidden assumptions, and build a structured analysis.', category: 'Analysis', tags: ['deep', 'structured'] },
  { id: 2, title: 'Simplify', text: 'Explain this in the simplest possible terms. Assume I am a beginner.', category: 'Analysis', tags: ['simple', 'explain'] },
  { id: 3, title: "Devil's Advocate", text: "Play devil's advocate. What are the strongest objections to this?", category: 'Analysis', tags: ['critique', 'objections'] },
  { id: 4, title: 'Connect the Dots', text: 'How does this connect to our broader work? Draw explicit links.', category: 'Research', tags: ['connect', 'links'] },
  { id: 5, title: 'Code Review', text: 'Review this code for bugs, edge cases, and improvements. Be thorough.', category: 'Coding', tags: ['code', 'review'] },
  { id: 6, title: 'Refactor', text: 'Refactor this for clarity, performance, and maintainability. Explain your changes.', category: 'Coding', tags: ['refactor', 'clean'] },
  { id: 7, title: 'Draft Response', text: 'Draft a clear, professional response to this. Be concise but complete.', category: 'Writing', tags: ['draft', 'professional'] },
  { id: 8, title: 'Brainstorm', text: 'Generate 10 creative ideas related to this topic. No bad ideas.', category: 'Creative', tags: ['ideas', 'creative'] },
];

export function PromptsPanel({ onCopyToComposer }) {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');
  const [copiedId, setCopiedId] = useState(null);

  const filtered = SAMPLE_PROMPTS.filter((p) => {
    const matchesSearch = !search || p.title.toLowerCase().includes(search.toLowerCase()) || p.text.toLowerCase().includes(search.toLowerCase());
    const matchesCat = category === 'All' || p.category === category;
    return matchesSearch && matchesCat;
  });

  const handleCopy = useCallback((prompt) => {
    onCopyToComposer?.(prompt.text);
    setCopiedId(prompt.id);
    setTimeout(() => setCopiedId(null), 1500);
  }, [onCopyToComposer]);

  return (
    <div className="prompts-panel">
      <div className="prompts-header">
        <h3><Sparkles size={16} /> Prompt Library</h3>
        <p>{filtered.length} prompts</p>
      </div>

      <div className="prompts-search">
        <Search size={14} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search prompts..."
        />
        {search && <button className="prompts-clear" onClick={() => setSearch('')}>Clear</button>}
      </div>

      <div className="prompts-categories">
        {PROMPT_CATEGORIES.map((cat) => (
          <button
            key={cat}
            className={category === cat ? 'active' : ''}
            onClick={() => setCategory(cat)}
          >
            {cat}
            <span className="cat-count">
              {cat === 'All' ? SAMPLE_PROMPTS.length : SAMPLE_PROMPTS.filter((p) => p.category === cat).length}
            </span>
          </button>
        ))}
      </div>

      <div className="prompts-list">
        {filtered.length === 0 ? (
          <div className="prompts-empty">
            <Filter size={24} />
            <p>No prompts match your search</p>
          </div>
        ) : (
          filtered.map((prompt) => (
            <div key={prompt.id} className="prompt-card">
              <div className="prompt-card-head">
                <b>{prompt.title}</b>
                <div className="prompt-tags">
                  {prompt.tags.map((t) => <span key={t}>{t}</span>)}
                </div>
              </div>
              <p className="prompt-text">{prompt.text}</p>
              <div className="prompt-card-actions">
                <button
                  onClick={() => handleCopy(prompt)}
                  className={copiedId === prompt.id ? 'copied' : ''}
                >
                  {copiedId === prompt.id ? <Check size={11} /> : <Copy size={11} />}
                  {copiedId === prompt.id ? 'Copied' : 'Use'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
