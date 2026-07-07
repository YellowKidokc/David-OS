import { SourceAvatar, StatusBadge } from '../icons/AppIcons';

export function MessageCard({ message, onPatch }) {
  const id = message.id || message.message_id || message.created_at;
  const source = message.source || message.agent || 'Top of Mind';
  const status = message.status || message.source_status || 'online';
  return <article className={`message ${message.wall ? `wall-${message.wall}` : ''}`}><div className="message-meta"><div className="source-badge"><SourceAvatar source={source} status={status}/><span>{source}</span><StatusBadge status={status}/></div><span>{message.folder || 'Inbox'} · Wall {message.wall || 1}</span></div><p>{message.content || message.text || message.message || JSON.stringify(message)}</p><div className="message-actions"><button onClick={() => onPatch(id, { pinned: !message.pinned })}><span>⌖</span>Pin</button><button onClick={() => onPatch(id, { archived: true })}><span>□</span>Archive</button><button onClick={() => onPatch(id, { folder: 'projects' })}><span>▸</span>Move folder</button><button onClick={() => onPatch(id, { wall: ((message.wall || 1) % 3) + 1 })}><span>→</span>Move wall</button></div></article>;
}
