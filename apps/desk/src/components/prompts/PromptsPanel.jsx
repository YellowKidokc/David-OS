import { useState, useMemo } from 'react';
import {
  Sparkles,
  Zap,
  Search,
  Copy,
  Check,
  MessageSquare
} from 'lucide-react';

/*
  PromptsPanel — a full prompt library.
  Categories, search, one-click copy to composer.
  Categories match David's command vocabulary and daily workflow.
*/

import { PROMPT_CATEGORIES, PROMPTS, exportPromptsJson } from './promptLibrary';
export function PromptsPanel({ onCopyToComposer }) {
  const [activeCategory, setActiveCategory] = useState('analysis');
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [exported, setExported] = useState(false);

  const filtered = useMemo(() => {
    let list = PROMPTS.filter((p) => p.category === activeCategory);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = PROMPTS.filter(
        (p) =>
          p.label.toLowerCase().includes(q) ||
          p.text.toLowerCase().includes(q) ||
          p.tags.some((t) => t.includes(q))
      );
    }
    return list;
  }, [activeCategory, search]);

  const handleExport = async () => {
    const json = exportPromptsJson();
    await navigator.clipboard?.writeText?.(json);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'top-of-mind-prompts.json';
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
    setTimeout(() => setExported(false), 1400);
  };

  const handleCopy = (prompt) => {
    onCopyToComposer?.(prompt.text);
    setCopiedId(prompt.id);
    setTimeout(() => setCopiedId(null), 1200);
  };

  return (
    <section className="prompts-panel">
      <div className="prompts-header">
        <h3>
          <Sparkles size={15} /> Prompt Library
        </h3>
        <div className="prompts-header-actions"><p>{PROMPTS.length} prompts across {PROMPT_CATEGORIES.length} categories</p><button onClick={handleExport}>{exported ? 'JSON copied' : 'Export JSON'}</button></div>
      </div>

      <div className="prompts-search">
        <Search size={14} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search prompts by name, text, or tag..."
        />
        {search && (
          <button className="prompts-clear" onClick={() => setSearch('')}>
            Clear
          </button>
        )}
      </div>

      <div className="prompts-categories">
        {PROMPT_CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const count = PROMPTS.filter((p) => p.category === cat.id).length;
          return (
            <button
              key={cat.id}
              className={activeCategory === cat.id ? 'active' : ''}
              onClick={() => { setActiveCategory(cat.id); setSearch(''); }}
            >
              <Icon size={14} />
              {cat.label}
              <span className="cat-count">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="prompts-list">
        {filtered.map((p) => (
          <div key={p.id} className="prompt-card">
            <div className="prompt-card-head">
              <Zap size={12} />
              <b>{p.label}</b>
              <div className="prompt-tags">
                {p.tags.map((t) => (
                  <span key={t}>{t}</span>
                ))}
              </div>
            </div>
            <p className="prompt-text">{p.text}</p>
            <div className="prompt-card-actions">
              <button
                onClick={() => handleCopy(p)}
                className={copiedId === p.id ? 'copied' : ''}
              >
                {copiedId === p.id ? (
                  <>
                    <Check size={12} /> Copied
                  </>
                ) : (
                  <>
                    <Copy size={12} /> Use
                  </>
                )}
              </button>
              <button
                onClick={() => navigator.clipboard?.writeText?.(p.text)}
                title="Copy to clipboard"
              >
                <MessageSquare size={12} /> Copy
              </button>
            </div>
          </div>
        ))}
        {!filtered.length && (
          <div className="prompts-empty">
            <Search size={32} strokeWidth={1} />
            <p>No prompts match &quot;{search}&quot;</p>
          </div>
        )}
      </div>
    </section>
  );
}
