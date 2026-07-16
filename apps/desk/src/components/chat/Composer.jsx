import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Mic,
  MicOff,
  Paperclip,
  Send,
  Sparkles,
  Command,
  CornerDownLeft,
  Zap,
  ChevronDown,
  Bot,
  AtSign,
  Image,
  FileText,
  Code,
} from 'lucide-react';

/*
  Composer — the message input bar.
  Features: textarea, send, mic toggle, attach (placeholder),
  slash-command autocomplete, prompt-chip bar, persona selector.
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

const QUICK_PROMPTS = [
  { label: 'Deep dive', text: 'Take a deep dive into this. Explore all angles, identify hidden assumptions, and build a structured analysis.', icon: Sparkles },
  { label: 'Simplify', text: 'Explain this in the simplest possible terms. Assume I am a beginner.', icon: Zap },
  { label: 'Critique', text: "Play devil's advocate. What are the strongest objections to this?", icon: Command },
  { label: 'Connect', text: 'How does this connect to our broader work? Draw explicit links.', icon: Sparkles },
];

const PERSONA_QUICK_SELECT = [
  { id: 'kimi', name: 'Kimi', color: '#22d3ee' },
  { id: 'claude', name: 'Claude', color: '#fb923c' },
  { id: 'codex', name: 'Codex', color: '#60a5fa' },
  { id: 'gemini', name: 'Gemini', color: '#60a5fa' },
  { id: 'gpt', name: 'GPT', color: '#4ade80' },
  { id: 'opus', name: 'Opus', color: '#c084fc' },
];

export function Composer({
  input,
  setInput,
  onSend,
  onMicToggle,
  onAttach,
  busy,
  activeSource,
  sources = [],
  onSelectSource,
}) {
  const [micOn, setMicOn] = useState(false);
  const [showSlash, setShowSlash] = useState(false);
  const [slashQuery, setSlashQuery] = useState('');
  const [showPrompts, setShowPrompts] = useState(false);
  const [showPlus, setShowPlus] = useState(false);
  const [showPersonaMenu, setShowPersonaMenu] = useState(false);
  const [showMention, setShowMention] = useState(false);
  const textareaRef = useRef(null);

  const normalizedSlashQuery = slashQuery.toLowerCase().replace(/^\//, '');
  const filteredSlash = SLASH_COMMANDS.filter((c) =>
    c.cmd.toLowerCase().replace(/^\//, '').includes(normalizedSlashQuery)
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        if (input.trim() && !busy) onSend();
        return;
      }
      if (e.key === 'Escape') {
        setShowSlash(false);
        setShowPrompts(false);
        setShowPlus(false);
        setShowPersonaMenu(false);
        setShowMention(false);
        return;
      }
      if (e.key === '/' && !showSlash && !input.trim()) {
        setShowSlash(true);
        setSlashQuery('');
        return;
      }
      if (e.key === 'Backspace' && showSlash) {
        if (slashQuery.length <= 1) {
          setShowSlash(false);
        }
        setSlashQuery((q) => q.slice(0, -1));
      }
      if (e.key === '@' && !showMention) {
        setShowMention(true);
      }
      if (e.key === 'Backspace' && showMention) {
        const lastAt = input.lastIndexOf('@');
        if (lastAt < 0 || input.length - lastAt <= 1) {
          setShowMention(false);
        }
      }
    },
    [input, busy, onSend, showSlash, slashQuery, showMention]
  );

  const handleInput = (e) => {
    const val = e.target.value;
    setInput(val);
    if (val.startsWith('/')) {
      setShowSlash(true);
      setSlashQuery(val.slice(1));
    } else {
      setShowSlash(false);
    }
    if (val.includes('@')) {
      setShowMention(true);
    } else {
      setShowMention(false);
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

  const insertMention = (name) => {
    const lastAt = input.lastIndexOf('@');
    if (lastAt >= 0) {
      setInput(input.slice(0, lastAt) + '@' + name + ' ');
    } else {
      setInput(input + '@' + name + ' ');
    }
    setShowMention(false);
    textareaRef.current?.focus();
  };

  const plusActions = [
    { label: 'Upload file', desc: 'Attach a document, image, audio, or source file', icon: Image, action: onAttach },
    { label: 'New folder', desc: 'Create a workspace folder or nested subfolder', icon: FileText, action: () => setInput((current) => current ? current : '[New folder] ') },
    { label: 'Clipboard', desc: 'Save or paste a clipboard item into this chat', icon: Paperclip, action: () => setInput((current) => current ? current + '\n\n[Clipboard] ' : '[Clipboard] ') },
    { label: 'Markdown note', desc: 'Start a markdown message block', icon: Code, action: () => setInput((current) => current ? current + '\n\n```md\n\n```' : '```md\n\n```') },
    { label: 'Prompt library', desc: 'Open quick prompt chips and slash commands', icon: Sparkles, action: () => { setShowPrompts(true); setShowSlash(true); } },
  ];

  const runPlusAction = (action) => {
    action?.();
    setShowPlus(false);
    textareaRef.current?.focus();
  };

  const toggleMic = () => {
    const next = !micOn;
    setMicOn(next);
    onMicToggle?.(next);
  };

  useEffect(() => {
    if (!micOn) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { setMicOn(false); return; }
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

  const activePersona = PERSONA_QUICK_SELECT.find((p) =>
    activeSource?.toLowerCase().includes(p.id)
  ) || PERSONA_QUICK_SELECT[0];

  return (
    <div className="composer-panel">
      {/* Persona quick-select bar */}
      <div className="composer-personas">
        <button
          className="persona-current"
          onClick={() => setShowPersonaMenu(!showPersonaMenu)}
          style={{ '--persona-color': activePersona?.color || '#22d3ee' }}
        >
          <Bot size={13} />
          <span>{activeSource || 'Kimi'}</span>
          <ChevronDown size={12} />
        </button>
        {showPersonaMenu && (
          <div className="persona-menu">
            {PERSONA_QUICK_SELECT.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  onSelectSource?.(p.name);
                  setShowPersonaMenu(false);
                  textareaRef.current?.focus();
                }}
                style={{ '--persona-color': p.color }}
                className={activeSource?.toLowerCase().includes(p.id) ? 'active' : ''}
              >
                <span className="persona-dot" />
                {p.name}
              </button>
            ))}
          </div>
        )}
        <div className="composer-divider" />
        <button
          className="prompts-toggle"
          onClick={() => setShowPrompts(!showPrompts)}
          title="Quick prompts"
        >
          <Sparkles size={13} /> Prompts
        </button>
        {showPrompts &&
          QUICK_PROMPTS.map((p) => (
            <button
              key={p.label}
              className="prompt-chip"
              onClick={() => insertPrompt(p.text)}
              title={p.text}
            >
              <p.icon size={11} /> {p.label}
            </button>
          ))}
      </div>

      {/* Slash command autocomplete */}
      {showSlash && filteredSlash.length > 0 && (
        <div className="slash-menu">
          {filteredSlash.map((c) => (
            <button key={c.cmd} onClick={() => insertSlashCommand(c.cmd)}>
              <c.icon size={13} />
              <b>{c.cmd}</b>
              <span>{c.desc}</span>
            </button>
          ))}
        </div>
      )}

      {/* Mention autocomplete */}
      {showMention && (
        <div className="mention-menu">
          {PERSONA_QUICK_SELECT.map((p) => (
            <button key={p.id} onClick={() => insertMention(p.name)}>
              <span className="mention-dot" style={{ background: p.color }} />
              <b>{p.name}</b>
              <span>@{p.id}</span>
            </button>
          ))}
        </div>
      )}

      {showPlus && (
        <div className="plus-menu">
          {plusActions.map((item) => (
            <button key={item.label} onClick={() => runPlusAction(item.action)}>
              <item.icon size={14} />
              <div>
                <b>{item.label}</b>
                <span>{item.desc}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Main input row */}
      <div className="composer-main">
        <button
          className="composer-plus"
          onClick={() => setShowPlus(!showPlus)}
          title="Open everything menu"
        >
          <AtSign size={16} />
        </button>

        <button
          className={`composer-mic ${micOn ? 'mic-on' : ''}`}
          onClick={toggleMic}
          title={micOn ? 'Stop listening' : 'Voice input'}
        >
          {micOn ? <Mic size={18} /> : <MicOff size={18} />}
        </button>

        <button
          className="composer-attach"
          onClick={onAttach}
          title="Attach file (coming soon)"
        >
          <Paperclip size={18} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${activeSource || 'Top of Mind'}...  Ctrl+Enter to send`}
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
