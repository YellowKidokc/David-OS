import React, { useEffect, useMemo, useState } from 'react';
import { topOfMindApi } from '../lib/api/topOfMindApi';

const emptyFilters = { query: '', source_app: '', source_window: '', folder: '', tag: '', kind: '', date_from: '', date_to: '', pinned: '', deleted: '' };
const compact = (text = '', n = 220) => text.length > n ? `${text.slice(0, n)}…` : text;
const tags = (value = '') => value.split(',').map((tag) => tag.trim()).filter(Boolean);

export function ClipboardWorkspace({ onSendToComposer, setNotice }) {
  const [items, setItems] = useState([]);
  const [facets, setFacets] = useState({ source_apps: [], source_windows: [], folders: [], tags: [], kinds: [] });
  const [duplicates, setDuplicates] = useState([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [selected, setSelected] = useState([]);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retention, setRetention] = useState({ days: 90, include_pinned: false });
  const [importText, setImportText] = useState('');

  const selectedItems = useMemo(() => items.filter((item) => selected.includes(item.id)), [items, selected]);
  const selectedBody = useMemo(() => selectedItems.map((item) => item.body).join('\n\n---\n\n'), [selectedItems]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''));
      if (params.pinned) params.pinned = params.pinned === 'true';
      if (params.deleted) params.deleted = params.deleted === 'true';
      const [list, facetList, dupes, retentionResponse] = await Promise.all([
        topOfMindApi.getClipboardItems({ ...params, include_deleted: true, limit: 250 }),
        topOfMindApi.getClipboardFacets(),
        topOfMindApi.getClipboardDuplicates(),
        topOfMindApi.getClipboardRetention(),
      ]);
      setItems(list.items || []);
      setFacets(facetList.facets || facets);
      setDuplicates(dupes.duplicates || []);
      setRetention(retentionResponse.retention || retention);
    } catch (err) {
      setError(err.message || 'Clipboard API unavailable');
      setNotice?.(`Clipboard workspace offline: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const patch = async (id, patchBody) => {
    const previous = items;
    setItems((current) => current.map((item) => item.id === id ? { ...item, ...patchBody } : item));
    try {
      const response = await topOfMindApi.updateClipboardItem(id, patchBody);
      setItems((current) => current.map((item) => item.id === id ? response.item : item));
    } catch (err) {
      setItems(previous);
      setError(err.message);
    }
  };

  const remove = async (id) => {
    try { const response = await topOfMindApi.deleteClipboardItem(id); setItems((current) => current.map((item) => item.id === id ? response.item : item)); }
    catch (err) { setError(err.message); }
  };

  const restore = async (id) => {
    try { const response = await topOfMindApi.restoreClipboardItem(id); setItems((current) => current.map((item) => item.id === id ? response.item : item)); }
    catch (err) { setError(err.message); }
  };

  const copyToWindowsClipboard = async (item) => {
    try {
      const response = await topOfMindApi.copyClipboardItem(item.id);
      await navigator.clipboard?.writeText?.(response.item.body);
      setNotice?.('Clipboard entry is ready for the AHK bridge / browser clipboard.');
    } catch (err) { setError(err.message); }
  };

  const mergeSelected = async (save = false) => {
    try {
      const response = await topOfMindApi.mergeClipboardItems({ item_ids: selected, save });
      onSendToComposer?.(response.merge.body);
      if (response.merge.item) setItems((current) => [response.merge.item, ...current]);
      setNotice?.(`Merged ${response.merge.count} clipboard records${save ? ' and saved a new item' : ''}.`);
    } catch (err) { setError(err.message); }
  };

  const exportSelected = async (format) => {
    try {
      let text = selectedBody;
      if (format === 'json') {
        const response = await topOfMindApi.exportClipboardItems({ item_ids: selected, format });
        text = JSON.stringify(response.items || [], null, 2);
      } else if (format === 'markdown') {
        text = selectedItems.map((item) => `<!-- clipboard:${item.id} created:${item.created_at} -->\n\n${item.body}`).join('\n\n');
      }
      await navigator.clipboard?.writeText?.(text);
      setNotice?.(`Exported ${selected.length || items.length} clipboard records as ${format}.`);
    } catch (err) { setError(err.message); }
  };

  const importItems = async () => {
    try {
      const parsed = JSON.parse(importText || '[]');
      const response = await topOfMindApi.importClipboardItems({ items: Array.isArray(parsed) ? parsed : parsed.items || [] });
      setNotice?.(`Imported ${response.stored} clipboard records.`);
      setImportText('');
      load();
    } catch (err) { setError(`Import failed: ${err.message}`); }
  };

  const saveRetention = async () => {
    try { const response = await topOfMindApi.setClipboardRetention(retention); setRetention(response.retention); setNotice?.('Clipboard retention preference saved.'); }
    catch (err) { setError(err.message); }
  };

  const selectItem = (id) => setSelected((current) => current.includes(id) ? current.filter((itemId) => itemId !== id) : [...current, id]);
  const setFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));

  return <section className="tm-page clipboard-page">
    <div className="tm-page-head">
      <div><h1>Clipboard Workspace</h1><p>Durable clipboard history powered by the existing SQLite clipboard routes and AHK bridge.</p></div>
      <div className="tm-head-actions"><button className="tm-secondary" onClick={load}>Refresh</button><button className="tm-primary" disabled={!selected.length} onClick={() => onSendToComposer?.(selectedBody)}>Send to composer</button></div>
    </div>
    {error && <div className="tm-error">{error}</div>}
    <div className="clip-controls">
      <input value={filters.query} onChange={(e) => setFilter('query', e.target.value)} placeholder="Search clipboard text…" />
      <select value={filters.source_app} onChange={(e) => setFilter('source_app', e.target.value)}><option value="">All apps</option>{facets.source_apps.map((value) => <option key={value}>{value}</option>)}</select>
      <select value={filters.source_window} onChange={(e) => setFilter('source_window', e.target.value)}><option value="">All windows</option>{facets.source_windows.map((value) => <option key={value}>{value}</option>)}</select>
      <select value={filters.folder} onChange={(e) => setFilter('folder', e.target.value)}><option value="">All folders</option>{facets.folders.map((value) => <option key={value}>{value}</option>)}</select>
      <select value={filters.tag} onChange={(e) => setFilter('tag', e.target.value)}><option value="">All tags</option>{facets.tags.map((value) => <option key={value}>{value}</option>)}</select>
      <select value={filters.kind} onChange={(e) => setFilter('kind', e.target.value)}><option value="">All types</option>{facets.kinds.map((value) => <option key={value}>{value}</option>)}</select>
      <input type="date" value={filters.date_from} onChange={(e) => setFilter('date_from', e.target.value)} />
      <input type="date" value={filters.date_to} onChange={(e) => setFilter('date_to', e.target.value)} />
      <select value={filters.pinned} onChange={(e) => setFilter('pinned', e.target.value)}><option value="">Pinned + unpinned</option><option value="true">Pinned only</option><option value="false">Unpinned only</option></select>
      <select value={filters.deleted} onChange={(e) => setFilter('deleted', e.target.value)}><option value="">Active + deleted</option><option value="false">Active only</option><option value="true">Deleted only</option></select>
      <button onClick={load}>{loading ? 'Loading…' : 'Apply'}</button><button onClick={() => setFilters(emptyFilters)}>Clear</button>
    </div>
    <div className="clip-bulkbar"><b>{selected.length}</b><span>selected</span><button disabled={selected.length < 2} onClick={() => mergeSelected(false)}>Merge to composer</button><button disabled={selected.length < 2} onClick={() => mergeSelected(true)}>Merge + save</button><button disabled={!selected.length} onClick={() => exportSelected('markdown')}>Save as Markdown</button><button disabled={!selected.length} onClick={() => exportSelected('text')}>Save as text</button><button disabled={!selected.length} onClick={() => exportSelected('json')}>Export JSON</button></div>
    <div className="clip-shell">
      <div className="clip-list">
        {items.map((item) => <article key={item.id} className={`clip-card ${selected.includes(item.id) ? 'selected' : ''} ${item.deleted ? 'deleted' : ''}`}>
          <label><input type="checkbox" checked={selected.includes(item.id)} onChange={() => selectItem(item.id)} /><b>#{item.id}</b><span>{item.kind}</span>{item.pinned && <span>★</span>}{item.secret_warning && <span className="secret">Secret-sensitive</span>}</label>
          <p>{compact(item.body)}</p>
          <div className="clip-tags">{tags(item.tags).map((tag) => <em key={tag}>{tag}</em>)}</div>
          <small>{item.source_app || 'unknown app'} · {item.source_window || 'unknown window'} · {item.folder || 'No folder'} · {item.created_at}</small>
          <div className="clip-actions"><button onClick={() => patch(item.id, { pinned: !item.pinned })}>{item.pinned ? 'Unpin' : 'Pin'}</button><button onClick={() => setEditing(item)}>Edit</button><button onClick={() => copyToWindowsClipboard(item)}>Copy via AHK</button>{item.deleted ? <button onClick={() => restore(item.id)}>Restore</button> : <button onClick={() => remove(item.id)}>Soft delete</button>}</div>
        </article>)}
        {!items.length && <div className="tm-empty">No clipboard records match the current filters.</div>}
      </div>
      <aside className="clip-inspector">
        <h2>Inspector</h2><p>{duplicates.length} duplicate groups detected by content hash.</p>{duplicates.slice(0, 5).map((dupe) => <code key={dupe.content_hash}>{dupe.duplicate_count}× {dupe.content_hash.slice(0, 12)}</code>)}
        <h3>Retention</h3><label>Days<input type="number" min="1" max="3650" value={retention.days} onChange={(e) => setRetention({ ...retention, days: Number(e.target.value) })} /></label><label><input type="checkbox" checked={retention.include_pinned} onChange={(e) => setRetention({ ...retention, include_pinned: e.target.checked })} /> Include pinned in retention pruning</label><button onClick={saveRetention}>Save retention</button>
        <h3>Import JSON</h3><textarea value={importText} onChange={(e) => setImportText(e.target.value)} placeholder='[{"body":"clip","tags":"project"}]' /><button onClick={importItems}>Import</button>
      </aside>
    </div>
    {editing && <div className="modal-backdrop"><div className="clip-editor"><h2>Edit clipboard #{editing.id}</h2>{editing.secret_warning && <div className="tm-warning">This entry may contain secrets. Avoid broadcasting it unless intentional.</div>}<textarea value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} /><input value={editing.folder || ''} onChange={(e) => setEditing({ ...editing, folder: e.target.value })} placeholder="Folder" /><input value={editing.tags || ''} onChange={(e) => setEditing({ ...editing, tags: e.target.value })} placeholder="tag,tag" /><div className="inline"><button className="tm-primary" onClick={() => { patch(editing.id, { body: editing.body, folder: editing.folder, tags: editing.tags }); setEditing(null); }}>Save</button><button onClick={() => setEditing(null)}>Cancel</button></div></div></div>}
  </section>;
}
