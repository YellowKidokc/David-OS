"""Scoring store — writes to the scoring.* audit tables."""

import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)


def create_session(conn, root_path: str, run_mode: str = 'tier1',
                   session_name: str = None) -> int:
    """Create a new scoring session. Returns session_id."""
    if not session_name:
        session_name = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scoring.session (session_name, root_path, run_mode)
        VALUES (%s, %s, %s) RETURNING session_id
    """, (session_name, str(root_path), run_mode))
    sid = cur.fetchone()[0]
    conn.commit()
    log.info(f"Session {sid} created: {session_name}")
    return sid


def write_file_score(conn, session_id: int, sha256: str, path,
                     address, meta) -> int:
    """Write NLP suggestion to scoring.file_score. Returns score_id."""
    from fis.nlp.hash_codec import human_score_string
    vec = address.vector
    canon = human_score_string(vec)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scoring.file_score (
            session_id, sha256, file_name, file_path, extension, size_bytes,
            orig_name, orig_path,
            nlp_vec_G, nlp_vec_M, nlp_vec_E, nlp_vec_S, nlp_vec_T,
            nlp_vec_K, nlp_vec_R, nlp_vec_Q, nlp_vec_F, nlp_vec_C,
            nlp_dominant, nlp_magnitude, nlp_state,
            nlp_hash_full, nlp_canonical,
            nlp_context, nlp_domain, nlp_function, nlp_lifecycle,
            nlp_confidence, outcome
        ) VALUES (
            %s,%s,%s,%s,%s,%s, %s,%s,
            %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,
            %s,%s,%s, %s,%s, %s,%s,%s,%s, %s, 'pending'
        )
        ON CONFLICT (session_id, sha256) DO UPDATE SET
            nlp_hash_full=EXCLUDED.nlp_hash_full,
            nlp_canonical=EXCLUDED.nlp_canonical,
            nlp_confidence=EXCLUDED.nlp_confidence,
            outcome='pending'
        RETURNING score_id
    """, (
        session_id, sha256, path.name, str(path), path.suffix,
        path.stat().st_size if path.exists() else None,
        path.name, str(path),
        vec[0],vec[1],vec[2],vec[3],vec[4],
        vec[5],vec[6],vec[7],vec[8],vec[9],
        address.dominant, address.magnitude, address.state,
        address.coord_hash_full, canon,
        meta.context if meta else 'BUSINESS',
        meta.domain  if meta else 'WORK',
        meta.function if meta else 'CAPTURE',
        meta.state   if meta else 'ACTIVE',
        float(address.magnitude) / 3.0,
    ))
    sid = cur.fetchone()[0]
    conn.commit()
    return sid


def write_dimension_confidence(conn, score_id: int, sha256: str,
                                vec, address) -> None:
    """Write per-variable confidence estimates."""
    # Confidence = normalized score for each variable
    # High score + strong signal = high confidence
    # Low score + weak signal = low confidence
    # Simple proxy: score/3.0 adjusted by whether it's dominant
    dominant_set = set(address.dominant)
    var_names = ['G','M','E','S','T','K','R','Q','F','C']

    confs = []
    for i, name in enumerate(var_names):
        score = vec[i]
        is_dom = name in dominant_set
        conf = min(score / 3.0, 1.0)
        if is_dom:
            conf = min(conf * 1.2, 1.0)  # boost for dominant
        elif score < 0.5:
            conf = 0.9  # confident it's absent
        confs.append(conf)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scoring.dimension_confidence
            (score_id, sha256,
             conf_G, conf_M, conf_E, conf_S, conf_T,
             conf_K, conf_R, conf_Q, conf_F, conf_C)
        VALUES (%s,%s, %s,%s,%s,%s,%s, %s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """, (score_id, sha256, *confs))
    conn.commit()


def finalize_session(conn, session_id: int, stats: dict) -> None:
    """Update session totals and write batch summary."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE scoring.session SET
            files_total   = %s,
            files_scored  = %s,
            files_errored = %s,
            avg_confidence = %s,
            completed_at  = NOW()
        WHERE session_id = %s
    """, (
        stats.get('total', 0),
        stats.get('success', 0),
        stats.get('errors', 0),
        None,  # computed from file_score table
        session_id,
    ))
    cur.execute("""
        INSERT INTO scoring.batch_summary (
            session_id, total_files, error_count,
            domain_dist, function_dist, context_dist, dominant_dist
        ) VALUES (%s,%s,%s, %s,%s,%s,%s)
    """, (
        session_id,
        stats.get('total', 0),
        stats.get('errors', 0),
        json.dumps(stats.get('by_domain', {})),
        json.dumps(stats.get('by_function', {})),
        json.dumps(stats.get('by_context', {})),
        json.dumps(stats.get('by_dominant', {})),
    ))
    conn.commit()
    log.info(f"Session {session_id} finalized")
