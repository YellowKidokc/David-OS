import React, { useEffect, useMemo, useState } from 'react';
import { topOfMindApi } from '../lib/api/topOfMindApi';

const contextScopes = [
  ['current_message', 'Current message only'],
  ['from_join_forward', 'From invitation forward'],
  ['recent_context', 'Current state + last 10 relevant messages'],
  ['full_branch', 'Full branch'],
  ['selected_context', 'Selected context only'],
  ['canonical_context', 'Canonical state only'],
];
const responseModes = [
  ['silent_advisor', 'Silent advisory'],
  ['named_contribution', 'Named contribution'],
  ['roundtable', 'Roundtable'],
  ['free_conversation', 'Free conversation'],
  ['turn_queue', 'Turn queue'],
];
const defaultPermissions = {
  can_read_current_conversation: true,
  can_read_prior_history: false,
  can_read_files: false,
  can_call_apis: false,
  can_send_visible_responses: false,
  can_advise_silently: true,
  can_invite_other_agents: false,
  can_create_branches: false,
  can_modify_files: false,
  can_issue_commands: false,
  requires_approval: true,
};

export function ConversationOSPanel({ sources, messages, onCopyToComposer, setNotice }) {
  const [arrivals, setArrivals] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [branches, setBranches] = useState([]);
  const [state, setState] = useState({ active_project: '', current_objective: '', unresolved_questions: [], recent_summary: '', required_next_action: '' });
  const [selectedArrival, setSelectedArrival] = useState(null);
  const [inviteDraft, setInviteDraft] = useState({ context_scope: 'recent_context', response_mode: 'silent_advisor', permissions: defaultPermissions });
  const [error, setError] = useState('');

  const activeAgents = useMemo(() => memberships.map((member) => member.agent_id), [memberships]);
  const latestMessage = messages?.[0] || messages?.[messages.length - 1];

  const load = async () => {
    setError('');
    try {
      const [arrivalResponse, membershipResponse, branchResponse, stateResponse] = await Promise.all([
        topOfMindApi.getAgentArrivals({ conversation_id: 'main' }),
        topOfMindApi.getAgentMemberships('main'),
        topOfMindApi.getConversationBranches('main'),
        topOfMindApi.getConversationState('main'),
      ]);
      setArrivals(arrivalResponse.arrivals || []);
      setMemberships(membershipResponse.memberships || []);
      setBranches(branchResponse.branches || []);
      setState(stateResponse.state || state);
    } catch (err) {
      setError(err.message || 'Conversation OS routes unavailable');
    }
  };

  useEffect(() => { load(); }, []);

  const markArrival = async (arrival, nextState) => {
    try {
      const response = await topOfMindApi.updateAgentArrival(arrival.id, { state: nextState });
      setArrivals((current) => current.map((item) => item.id === arrival.id ? response.arrival : item));
    } catch (err) { setError(err.message); }
  };

  const invite = async (arrival = selectedArrival, overrides = {}) => {
    if (!arrival) return;
    try {
      const response = await topOfMindApi.inviteAgentToConversation({
        conversation_id: 'main',
        agent_id: arrival.agent_id,
        joined_at_message_id: latestMessage?.id || latestMessage?.message_id || null,
        context_scope: inviteDraft.context_scope,
        response_mode: inviteDraft.response_mode,
        permissions: inviteDraft.permissions,
        ...overrides,
      });
      setMemberships((current) => [...current.filter((member) => member.agent_id !== arrival.agent_id), response.membership]);
      await markArrival(arrival, overrides.response_mode === 'silent_advisor' ? 'INTERNAL' : 'INVITED');
      setNotice?.(`${arrival.agent_id} joined with ${response.membership.context_scope} / ${response.membership.response_mode}.`);
    } catch (err) { setError(err.message); }
  };

  const branch = async (arrival = selectedArrival) => {
    if (!arrival) return;
    try {
      const response = await topOfMindApi.createConversationBranch({
        parent_conversation_id: 'main',
        branched_from_message_id: latestMessage?.id || latestMessage?.message_id || null,
        title: arrival.topic || `${arrival.agent_id} branch`,
        participants: ['david', 'primary', arrival.agent_id],
        shared_state_mode: 'snapshot',
        merge_back_policy: 'manual',
      });
      setBranches((current) => [response.branch, ...current]);
      await markArrival(arrival, 'BRANCHED');
      setNotice?.(`Created ${response.branch.branch_id} for ${arrival.topic}.`);
    } catch (err) { setError(err.message); }
  };

  const createDemoArrival = async () => {
    const source = sources?.find((item) => item.id !== 'clipboard') || sources?.[0] || { id: 'claude', name: 'Claude' };
    try {
      const response = await topOfMindApi.createAgentArrival({
        conversation_id: 'main',
        agent_id: source.id || source.source_id || source.name || 'agent',
        topic: state.current_objective || 'New contribution',
        contribution_type: 'possible_contradiction',
        priority: 'high',
        novelty: 0.88,
        summary: 'Agent has a contribution waiting for preview instead of interrupting the current thread.',
      });
      setArrivals((current) => [response.arrival, ...current]);
    } catch (err) { setError(err.message); }
  };

  const saveState = async () => {
    try {
      const response = await topOfMindApi.saveConversationState({ conversation_id: 'main', ...state });
      setState(response.state);
      setNotice?.('Conversation state saved for re-entry packets.');
    } catch (err) { setError(err.message); }
  };

  const reentry = async (agentId, hours) => {
    try {
      const response = await topOfMindApi.createReentryPacket({ conversation_id: 'main', agent_id: agentId, inactive_hours: hours, last_message_count: 10 });
      onCopyToComposer?.(response.packet.template);
      setNotice?.(`Prepared ${response.packet.level} re-entry packet for ${agentId}.`);
    } catch (err) { setError(err.message); }
  };

  const togglePermission = (key) => setInviteDraft((draft) => ({ ...draft, permissions: { ...draft.permissions, [key]: !draft.permissions[key] } }));

  return <aside className="conversation-os-panel">
    <div className="conv-head"><b>Conversation OS</b><button onClick={load}>↻</button></div>
    {error && <div className="tm-error">{error}</div>}
    <div className="conv-section"><h3>Participants</h3>{memberships.length ? memberships.map((member) => <div key={member.agent_id} className="participant-pill"><b>{member.agent_id}</b><span>{member.response_mode}</span><small>{member.context_scope} · {member.status}</small><button onClick={() => reentry(member.agent_id, 13)}>Re-entry</button></div>) : <p className="conv-muted">Primary only. Invited agents default to silent, limited context.</p>}</div>
    <div className="conv-section"><h3>Arrivals</h3><button className="tm-secondary" onClick={createDemoArrival}>＋ Simulate arrival</button>{arrivals.map((arrival) => <article key={arrival.id} className={`arrival-card ${selectedArrival?.id === arrival.id ? 'selected' : ''}`} onClick={() => setSelectedArrival(arrival)}><b>{arrival.agent_id}</b><span>{arrival.topic}</span><small>{arrival.type} · {arrival.priority} · novelty {arrival.novelty}</small><em>{arrival.state}</em><p>{arrival.summary}</p><div><button onClick={(e) => { e.stopPropagation(); markArrival(arrival, 'PREVIEWED'); }}>Preview</button><button onClick={(e) => { e.stopPropagation(); invite(arrival); }}>Invite</button><button onClick={(e) => { e.stopPropagation(); invite(arrival, { response_mode: 'silent_advisor' }); }}>Ask silently</button><button onClick={(e) => { e.stopPropagation(); branch(arrival); }}>Branch</button><button onClick={(e) => { e.stopPropagation(); markArrival(arrival, 'DEFERRED'); }}>Later</button><button onClick={(e) => { e.stopPropagation(); markArrival(arrival, 'DISMISSED'); }}>Dismiss</button></div></article>)}</div>
    <div className="conv-section"><h3>Invitation contract</h3><label>Context scope<select value={inviteDraft.context_scope} onChange={(e) => setInviteDraft({ ...inviteDraft, context_scope: e.target.value })}>{contextScopes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Response mode<select value={inviteDraft.response_mode} onChange={(e) => setInviteDraft({ ...inviteDraft, response_mode: e.target.value })}>{responseModes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><div className="permission-grid">{Object.keys(defaultPermissions).map((key) => <label key={key}><input type="checkbox" checked={Boolean(inviteDraft.permissions[key])} onChange={() => togglePermission(key)} />{key.replaceAll('_', ' ')}</label>)}</div></div>
    <div className="conv-section"><h3>Branch tabs</h3>{branches.length ? branches.map((item) => <button key={item.branch_id} onClick={() => setNotice?.(`${item.branch_id}: ${item.merge_back_policy}`)}>{item.title}<small>{item.branch_id}</small></button>) : <p className="conv-muted">No child branches yet.</p>}</div>
    <div className="conv-section"><h3>Conversation state</h3><input value={state.active_project || ''} onChange={(e) => setState({ ...state, active_project: e.target.value })} placeholder="Current project" /><input value={state.current_objective || ''} onChange={(e) => setState({ ...state, current_objective: e.target.value })} placeholder="Current objective" /><textarea value={state.recent_summary || ''} onChange={(e) => setState({ ...state, recent_summary: e.target.value })} placeholder="Current state summary" /><textarea value={state.required_next_action || ''} onChange={(e) => setState({ ...state, required_next_action: e.target.value })} placeholder="Required next action" /><button className="tm-primary" onClick={saveState}>Save state</button></div>
    <div className="conv-foot">Default: summary + last 10 relevant messages + invitation-forward access. Full history is never automatic.</div>
  </aside>;
}
