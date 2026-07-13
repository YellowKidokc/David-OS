import { useState } from 'react';
import {
  Merge,
  X,
  ArrowRight,
  GitMerge,
  History,
  MessageSquare,
} from 'lucide-react';
import { SourceAvatar, getSourceMeta } from '../icons/AppIcons';

export function MergeDialog({ target, sources, onMerge, onClose }) {
  const [mergeFrom, setMergeFrom] = useState('');
  const [mergeScope, setMergeScope] = useState('forward'); // 'forward' | 'all'
  const [mergeMode, setMergeMode] = useState('fifo'); // 'fifo' | 'sequence' | 'priority'
  const targetMeta = getSourceMeta(target?.agentId || '');

  const otherSources = sources.filter((s) => s.id !== target?.agentId);

  return (
    <div className="merge-dialog-overlay" onClick={onClose}>
      <div className="merge-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="merge-dialog-header">
          <GitMerge size={18} />
          <h3>Merge Conversation</h3>
          <button onClick={onClose}><X size={16} /></button>
        </div>

        <div className="merge-dialog-body">
          {/* Target */}
          <div className="merge-target">
            <span>Target:</span>
            <div className="merge-agent-chip">
              <SourceAvatar source={target?.agentId} status="online" compact />
              <span>{targetMeta.label}</span>
            </div>
          </div>

          {/* Source selection */}
          <label className="merge-label">Merge with:</label>
          <div className="merge-source-list">
            {otherSources.map((s) => {
              const meta = getSourceMeta(s.id);
              return (
                <button
                  key={s.id}
                  className={`merge-source-btn ${mergeFrom === s.id ? 'selected' : ''}`}
                  onClick={() => setMergeFrom(s.id)}
                >
                  <SourceAvatar source={s.id} status={s.status || 'online'} compact />
                  <span>{meta.label}</span>
                </button>
              );
            })}
          </div>

          {/* Scope */}
          <label className="merge-label">Scope:</label>
          <div className="merge-scope-selector">
            <button
              className={mergeScope === 'forward' ? 'selected' : ''}
              onClick={() => setMergeScope('forward')}
            >
              <ArrowRight size={13} />
              <div>
                <b>From this point forward</b>
                <small>Only new messages will be merged</small>
              </div>
            </button>
            <button
              className={mergeScope === 'all' ? 'selected' : ''}
              onClick={() => setMergeScope('all')}
            >
              <History size={13} />
              <div>
                <b>All history</b>
                <small>Merge entire conversation history</small>
              </div>
            </button>
          </div>

          {/* Response mode */}
          <label className="merge-label">Response mode:</label>
          <div className="merge-mode-selector">
            <button
              className={mergeMode === 'fifo' ? 'selected' : ''}
              onClick={() => setMergeMode('fifo')}
              title="First to respond speaks first"
            >
              <MessageSquare size={13} />
              <div>
                <b>First In, First Out</b>
                <small>Whoever responds first speaks</small>
              </div>
            </button>
            <button
              className={mergeMode === 'sequence' ? 'selected' : ''}
              onClick={() => setMergeMode('sequence')}
              title="Each AI responds in turn"
            >
              <GitMerge size={13} />
              <div>
                <b>Round Robin</b>
                <small>Each AI takes turns responding</small>
              </div>
            </button>
            <button
              className={mergeMode === 'priority' ? 'selected' : ''}
              onClick={() => setMergeMode('priority')}
              title="Priority AI always responds first"
            >
              <ArrowRight size={13} />
              <div>
                <b>Priority Order</b>
                <small>Set priority for who goes first</small>
              </div>
            </button>
          </div>
        </div>

        <div className="merge-dialog-footer">
          <button className="merge-cancel" onClick={onClose}>Cancel</button>
          <button
            className="merge-confirm"
            disabled={!mergeFrom}
            onClick={() => onMerge({ from: mergeFrom, scope: mergeScope, mode: mergeMode })}
          >
            <Merge size={14} /> Merge Conversations
          </button>
        </div>
      </div>
    </div>
  );
}
