import { useState } from 'react';
import {
  Zap,
  Plus,
  X,
  Clock,
  MessageSquare,
  Bot,
  Play,
  Pause,
  Trash2,
  Repeat,
  Bell,
} from 'lucide-react';
import { getSourceMeta } from '../icons/AppIcons';

const DEFAULT_TRIGGERS = [
  {
    id: 'at-1',
    name: 'Conversation Check',
    enabled: true,
    condition: 'conversation_duration',
    params: { everyMinutes: 10, maxDuration: 120, action: 'send_prompt' },
    target: 'kimi',
    message: 'Check your messages and provide a status update.',
    lastRun: '10 min ago',
  },
  {
    id: 'at-2',
    name: 'Memory Handoff Reminder',
    enabled: false,
    condition: 'time_of_day',
    params: { hour: 18, minute: 0 },
    target: 'all',
    message: 'Prepare memory handoff summaries for all active agents.',
    lastRun: null,
  },
  {
    id: 'at-3',
    name: 'Idle Check',
    enabled: true,
    condition: 'idle_time',
    params: { idleMinutes: 30, action: 'notify' },
    target: 'codex',
    message: 'System idle for 30 minutes. Check for pending tasks.',
    lastRun: '1 hr ago',
  },
];

const CONDITION_TYPES = [
  { id: 'conversation_duration', label: 'Conversation Duration', desc: 'While actively chatting, every X minutes' },
  { id: 'time_of_day', label: 'Time of Day', desc: 'Run at a specific time' },
  { id: 'idle_time', label: 'Idle Time', desc: 'After X minutes of no activity' },
  { id: 'message_count', label: 'Message Count', desc: 'After X messages in conversation' },
];

export function AutomationPanel({ sources }) {
  const [triggers, setTriggers] = useState(DEFAULT_TRIGGERS);
  const [showCreate, setShowCreate] = useState(false);
  const [newTrigger, setNewTrigger] = useState({
    name: '',
    condition: 'conversation_duration',
    everyMinutes: 10,
    maxDuration: 120,
    action: 'send_prompt',
    target: 'kimi',
    message: '',
  });

  const toggleTrigger = (id) => {
    setTriggers((prev) =>
      prev.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t))
    );
  };

  const deleteTrigger = (id) => {
    setTriggers((prev) => prev.filter((t) => t.id !== id));
  };

  const addTrigger = () => {
    if (!newTrigger.name.trim()) return;
    setTriggers((prev) => [
      ...prev,
      {
        id: `at-${Date.now()}`,
        name: newTrigger.name,
        enabled: true,
        condition: newTrigger.condition,
        params: {
          everyMinutes: newTrigger.everyMinutes,
          maxDuration: newTrigger.maxDuration,
          action: newTrigger.action,
        },
        target: newTrigger.target,
        message: newTrigger.message,
        lastRun: null,
      },
    ]);
    setShowCreate(false);
    setNewTrigger({
      name: '',
      condition: 'conversation_duration',
      everyMinutes: 10,
      maxDuration: 120,
      action: 'send_prompt',
      target: 'kimi',
      message: '',
    });
  };

  return (
    <div className="automation-panel">
      {/* Header */}
      <div className="auto-header">
        <div className="auto-title">
          <Zap size={15} />
          <span>Automation</span>
        </div>
        <button className="auto-add-btn" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? <X size={13} /> : <Plus size={13} />}
          {showCreate ? 'Cancel' : 'New Trigger'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="auto-create-form">
          <label>
            <span>Trigger Name</span>
            <input
              value={newTrigger.name}
              onChange={(e) => setNewTrigger((p) => ({ ...p, name: e.target.value }))}
              placeholder="e.g., Status Check"
            />
          </label>

          <label>
            <span>When</span>
            <select
              value={newTrigger.condition}
              onChange={(e) => setNewTrigger((p) => ({ ...p, condition: e.target.value }))}
            >
              {CONDITION_TYPES.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </label>

          {newTrigger.condition === 'conversation_duration' && (
            <>
              <label>
                <span>Every X minutes</span>
                <input
                  type="number"
                  value={newTrigger.everyMinutes}
                  onChange={(e) => setNewTrigger((p) => ({ ...p, everyMinutes: Number(e.target.value) }))}
                  min={1}
                  max={120}
                />
              </label>
              <label>
                <span>Cutoff after X minutes total</span>
                <input
                  type="number"
                  value={newTrigger.maxDuration}
                  onChange={(e) => setNewTrigger((p) => ({ ...p, maxDuration: Number(e.target.value) }))}
                  min={5}
                  max={600}
                />
              </label>
            </>
          )}

          <label>
            <span>Target Agent</span>
            <select
              value={newTrigger.target}
              onChange={(e) => setNewTrigger((p) => ({ ...p, target: e.target.value }))}
            >
              <option value="all">All Agents</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id}>{s.name || s.id}</option>
              ))}
            </select>
          </label>

          <label>
            <span>Prompt / Message</span>
            <textarea
              value={newTrigger.message}
              onChange={(e) => setNewTrigger((p) => ({ ...p, message: e.target.value }))}
              placeholder="What should the agent do when triggered?"
              rows={2}
            />
          </label>

          <button className="auto-create-submit" onClick={addTrigger}>
            <Zap size={13} /> Create Trigger
          </button>
        </div>
      )}

      {/* Trigger list */}
      <div className="auto-trigger-list">
        {triggers.length === 0 ? (
          <div className="auto-empty">
            <Bell size={24} />
            <p>No automation triggers set up</p>
          </div>
        ) : (
          triggers.map((t) => {
            const condLabel = CONDITION_TYPES.find((c) => c.id === t.condition)?.label || t.condition;
            const targetMeta = getSourceMeta(t.target);
            return (
              <div key={t.id} className={`auto-trigger ${!t.enabled ? 'disabled' : ''}`}>
                <div className="auto-trigger-main">
                  <button
                    className={`auto-toggle ${t.enabled ? 'on' : 'off'}`}
                    onClick={() => toggleTrigger(t.id)}
                    title={t.enabled ? 'Disable' : 'Enable'}
                  >
                    {t.enabled ? <Play size={11} /> : <Pause size={11} />}
                  </button>

                  <div className="auto-trigger-info">
                    <span className="auto-trigger-name">{t.name}</span>
                    <div className="auto-trigger-meta">
                      <span><Clock size={10} /> {condLabel}</span>
                      <span><Bot size={10} /> {targetMeta.label}</span>
                      {t.lastRun && <span>· {t.lastRun}</span>}
                    </div>
                  </div>

                  <button
                    className="auto-trigger-delete"
                    onClick={() => deleteTrigger(t.id)}
                    title="Delete trigger"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
