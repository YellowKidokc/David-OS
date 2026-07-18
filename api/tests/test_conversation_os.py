def test_conversation_os_invite_branch_reentry_and_arrivals(tmp_path, monkeypatch):
    db_path = tmp_path / "conversation.sqlite3"
    monkeypatch.setenv("FIHUB_DB_PATH", str(db_path))
    monkeypatch.delenv("FIHUB_API_TOKEN", raising=False)

    from file_intelligence_hub.api import routes_conversation_os

    routes_conversation_os.DEFAULT_DB_PATH = db_path

    state = routes_conversation_os.upsert_state(routes_conversation_os.ConversationStateRequest(
        conversation_id="main",
        active_project="Grace Boundary Theorem",
        current_objective="Audit possible contradiction",
        canonical_definitions=[{"term": "grace", "definition": "accepted boundary condition"}],
        accepted_decisions=["Do not default invited agents to full history"],
        rejected_options=["Free-for-all multi-agent replies"],
        unresolved_questions=["Does entropy claim contradict theorem?"],
        recent_summary="Primary is conducting the conversation.",
        required_next_action="Preview Claude before inviting.",
    ))["state"]
    assert state["active_project"] == "Grace Boundary Theorem"

    arrival = routes_conversation_os.create_arrival(routes_conversation_os.ArrivalRequest(
        agent_id="claude",
        topic="Grace Boundary Theorem",
        contribution_type="possible_contradiction",
        priority="high",
        novelty=0.88,
        summary="Claude has a possible contradiction.",
    ))["arrival"]
    assert arrival["state"] == "NEW"
    assert routes_conversation_os.set_arrival_state(arrival["id"], routes_conversation_os.ArrivalStateRequest(state="PREVIEWED"))["arrival"]["state"] == "PREVIEWED"

    membership = routes_conversation_os.invite_agent(routes_conversation_os.InviteRequest(agent_id="claude"))["membership"]
    assert membership["context_scope"] == "recent_context"
    assert membership["response_mode"] == "silent_advisor"
    assert membership["permissions"]["can_read_prior_history"] is False
    assert membership["permissions"]["can_invite_other_agents"] is False
    assert membership["permissions"]["requires_approval"] is True

    grant = routes_conversation_os.create_context_grant(routes_conversation_os.ContextGrantRequest(agent_id="claude", scope="selected_context", sources=[{"type": "message", "id": 42}]))["grant"]
    assert grant["sources"] == [{"type": "message", "id": 42}]

    branch = routes_conversation_os.create_branch(routes_conversation_os.BranchRequest(title="Physics audit of entropy claim", participants=["david", "primary", "claude"]))["branch"]
    assert branch["parent_conversation_id"] == "main"
    assert branch["merge_back_policy"] == "manual"
    assert "claude" in branch["participants"]

    proposal = routes_conversation_os.create_proposal(routes_conversation_os.ProposalRequest(agent_id="claude", body="Internal contradiction analysis."))["proposal"]
    assert proposal["state"] == "INTERNAL"

    decision = routes_conversation_os.create_decision(routes_conversation_os.DecisionRequest(title="Use silent advisor by default"))["decision"]
    assert decision["status"] == "accepted"

    packet = routes_conversation_os.create_reentry_packet(routes_conversation_os.ReentryRequest(agent_id="claude", inactive_hours=13))["packet"]
    assert packet["level"] == "full_packet"
    assert "Current project: Grace Boundary Theorem" in packet["template"]

    assert routes_conversation_os.list_arrivals()["arrivals"]
    assert routes_conversation_os.list_memberships()["memberships"][0]["agent_id"] == "claude"
    assert routes_conversation_os.list_branches()["branches"][0]["branch_id"].startswith("branch-")
