import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Mic,
  MicOff,
  Plus,
  Send,
  Sparkles,
  Command,
  CornerDownLeft,
  Zap,
} from 'lucide-react';
import { PROMPT_CATEGORIES, PROMPTS, categoryForPrompt, exportPromptsJson } from '../prompts/promptLibrary';

/*
  Composer — the message input bar.
  Features: textarea, send, mic toggle, attach (placeholder),
  slash-command autocomplete, prompt-chip bar.
*/

const SLASH_COMMANDS = [
  { cmd: '/PROBE', desc: 'Run a structured probe', icon: Zap },
  { cmd: '/EAST', desc: 'Expand and simplify text', icon: Sparkles },
  { cmd: '/CHAIN', desc: 'Build a reasoning chain', icon: Command },
  { cmd: '/SUMMARIZE', desc: 'Summarize selected messages', icon: Sparkles },
  { cmd: '/DRAFT', desc: 'Draft a response', icon: Sparkles },
  { cmd: '/CLEAR', desc: 'Clear the conversation view', icon: Command },
  { cmd: '/api filesystem intake <source_folder>', desc: 'POST /fis/intake', icon: Command },
  { cmd: '/api filesystem neardup', desc: 'POST /fis/neardup', icon: Command },
  { cmd: '/api comm send codex "message here"', desc: 'POST /mattermost/send', icon: Command },
  { cmd: '/api comm broadcast "message here"', desc: 'POST /mattermost/broadcast', icon: Command },
  { cmd: '/api nlp classify <file_path>', desc: 'POST /fis/classify', icon: Command },
];

const QUICK_PROMPTS = PROMPTS.filter((prompt) => ['a1', 'w1', 'd2', 'fis1', 'mf3'].includes(prompt.id));

export function Composer({
  input,
  setInput,
  onSend,
  onMicToggle,
  onAttach,
  busy,
  activeSource,
}) {
  const [micOn, setMicOn] = useState(false);
  const [showSlash, setShowSlash] = useState(false);
  const [slashQuery, setSlashQuery] = useState('');
  const [showPrompts, setShowPrompts] = useState(false);
  const [promptCategory, setPromptCategory] = useState('analysis');
  const textareaRef = useRef(null);

  const normalizedSlashQuery = slashQuery.toLowerCase().replace(/^\//, '');
  const filteredSlashCommands = SLASH_COMMANDS.filter((c) =>
    c.cmd.toLowerCase().replace(/^\//, '').includes(normalizedSlashQuery)
  );
  const filteredSlashPrompts = PROMPTS.filter((prompt) => {
    const haystack = [prompt.label, prompt.category, prompt.text, ...prompt.tags].join(' ').toLowerCase();
    return haystack.includes(normalizedSlashQuery);
  }).slice(0, 8);
  const visiblePrompts = PROMPTS.filter((prompt) => prompt.category === promptCategory);

  const handleKeyDown = useCallback(
    (e) => {
      // Ctrl/Cmd + Enter to send
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (input.trim() && !busy) onSend();
        return;
      }

      // Escape to close menus
      if (e.key === 'Escape') {
        setShowSlash(false);
        setShowPrompts(false);
        return;
      }

      // Slash command trigger
      if (e.key === '/' && !showSlash && !input.trim()) {
        setShowSlash(true);
        setSlashQuery('');
        return;
      }

      // Backspace to dismiss slash menu
      if (e.key === 'Backspace' && showSlash) {
        if (slashQuery.length <= 1) {
          setShowSlash(false);
        }
        setSlashQuery((q) => q.slice(0, -1));
      }
    },
    [input, busy, onSend, showSlash, slashQuery]
  );

  const handleInput = (e) => {
    const val = e.target.value;
    setInput(val);

    // Detect slash commands
    if (val.startsWith('/')) {
      setShowSlash(true);
      setSlashQuery(val.slice(1));
    } else {
      setShowSlash(false);
    }
  };

  const insertSlashCommand = (cmd) => {
    setInput(cmd + ' ');
    setShowSlash(false);
    textareaRef.current?.focus();
  };

  const insertPrompt = (text) => {
    setInput((current) => (current ? current + '\n\n' + text : text));
    setShowPrompts(false);
    textareaRef.current?.focus();
  };

  const handleExportPrompts = async () => {
    const json = exportPromptsJson();
    await navigator.clipboard?.writeText?.(json);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'top-of-mind-prompts.json';
    a.click();
    URL.revokeObjectURL(url);
    textareaRef.current?.focus();
  };

  const toggleMic = () => {
    const next = !micOn;
    setMicOn(next);
    onMicToggle?.(next);
  };

  // Speech recognition
  useEffect(() => {
    if (!micOn) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMicOn(false);
      return;
    }
    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let final = '';
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      if (final) setInput((c) => (c ? c + ' ' + final : final));
    };
    rec.onerror = () => setMicOn(false);
    rec.onend = () => { if (micOn) rec.start(); };
    rec.start();
    return () => rec.stop();
  }, [micOn]);

  const canSend = input.trim() && !busy;

  return (
    <div className="composer-panel">
      {/* Prompt chips bar */}
      <div className="composer-prompts">
        <button
          className="prompts-toggle"
          onClick={() => setShowPrompts(!showPrompts)}
          title="Open prompt picker (+ or /)"
        >
          <Plus size={13} /> Prompts
        </button>
        {QUICK_PROMPTS.map((p) => {
          const CatIcon = categoryForPrompt(p).icon;
          return <button
            key={p.id}
            className="prompt-chip"
            onClick={() => insertPrompt(p.text)}
            title={p.text}
          >
            <CatIcon size={11} /> {p.label}
          </button>;
        })}
      </div>

      {/* Slash command autocomplete */}
      {showSlash && (filteredSlashCommands.length > 0 || filteredSlashPrompts.length > 0) && (
        <div className="slash-menu">
          {filteredSlashCommands.map((c) => (
            <button key={c.cmd} onClick={() => insertSlashCommand(c.cmd)}>
              <c.icon size={13} />
              <b>{c.cmd}</b>
              <span>{c.desc}</span>
            </button>
          ))}
          {filteredSlashPrompts.map((prompt) => {
            const CatIcon = categoryForPrompt(prompt).icon;
            return <button key={prompt.id} onClick={() => insertPrompt(prompt.text)}>
              <CatIcon size={13} />
              <b>/{prompt.label}</b>
              <span>{prompt.tags.join(' · ')}</span>
            </button>;
          })}
        </div>
      )}

      {showPrompts && (
        <div className="prompt-picker">
          <div className="prompt-picker-head">
            <div><b>Prompt picker</b><small>Click + or type / to insert a reusable prompt.</small></div>
            <button onClick={handleExportPrompts}>Export JSON</button>
          </div>
          <div className="prompt-picker-tabs">
            {PROMPT_CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              return <button key={cat.id} className={promptCategory === cat.id ? 'active' : ''} onClick={() => setPromptCategory(cat.id)}><Icon size={12}/>{cat.label}</button>;
            })}
          </div>
          <div className="prompt-picker-list">
            {visiblePrompts.map((prompt) => (
              <button key={prompt.id} onClick={() => insertPrompt(prompt.text)}>
                <b>{prompt.label}</b><span>{prompt.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main input row */}
      <div className="composer-main">
        <button
          className={`composer-mic ${micOn ? 'mic-on' : ''}`}
          onClick={toggleMic}
          title={micOn ? 'Stop listening' : 'Voice input'}
        >
          {micOn ? <Mic size={18} /> : <MicOff size={18} />}
        </button>

        <button
          className="composer-attach"
          onClick={() => setShowPrompts((current) => !current)}
          title="Open prompt picker"
        >
          <Plus size={18} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${activeSource || 'Top of Mind'}...  + for prompts, / for prompts and commands`}
          rows={1}
        />

        <button
          className="composer-send"
          onClick={onSend}
          disabled={!canSend}
          title="Send"
        >
          <Send size={16} />
          <CornerDownLeft size={10} />
        </button>
      </div>
    </div>
  );
}
