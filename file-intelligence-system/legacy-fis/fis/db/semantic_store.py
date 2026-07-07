from fis.nlp.dqm import dqm_from_vector
"""Semantic Store — DB write layer for the new classification tables.

Writes to: file_identity, meta_classification, relational_context, file_trajectories.
Reads from: existing 'files' table (via file_id / sha256 join).

All functions are safe to call multiple times — upsert semantics throughout.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def upsert_file_identity(conn, sha256: str, path: Path, text: str,
                         address, meta, file_id: Optional[int] = None) -> int:
    """Insert or update file_identity row. Returns identity_id."""
    from fis.nlp.hash_codec import human_score_string

    vec = address.vector
    dom = address.dominant

    # Build all four name projections
    slug = path.stem.lower().replace(' ', '-')[:40]
    date_str = datetime.now().strftime('%Y%m%d')
    ext = path.suffix.lstrip('.')

    name_personal     = f"{slug}_{date_str}.{ext}"
    name_research     = f"FIS_{'-'.join(dom) or 'E'}_{slug}_{date_str}.{ext}"
    name_professional = f"{meta.domain}_{meta.function}_{slug}_{date_str}.{ext}"
    name_system       = f"{''.join(dom) or 'E'}_{path.name}"

    # Detect folder context signal from path
    folder_name = path.parent.name.lower()

    canon_vec = human_score_string(vec)

    sql = """
        INSERT INTO file_identity (
            file_id, sha256,
            vec_G, vec_M, vec_E, vec_S, vec_T,
            vec_K, vec_R, vec_Q, vec_F, vec_C,
            coord_hash_raw, coord_hash_full, dominant_vars,
            magnitude, state,
            file_name, extension, size_bytes,
            created_at, modified_at,
            source_path, folder_context,
            name_personal, name_research, name_professional, name_system,
            name_active, naming_mode,
            domain, keywords,
            classifier_confidence, scores_raw,
            tier, dqm_quality, dqm_confidence, dqm_flags,
            classified_at
        ) VALUES (
            %s, %s,
            %s,%s,%s,%s,%s, %s,%s,%s,%s,%s,
            %s,%s,%s, %s,%s,
            %s,%s,%s, %s,%s,
            %s,%s,
            %s,%s,%s,%s, %s,%s,
            %s,%s,
            %s,%s,
            %s, NOW()
        )
        ON CONFLICT (sha256) DO UPDATE SET
            vec_G=EXCLUDED.vec_G, vec_M=EXCLUDED.vec_M, vec_E=EXCLUDED.vec_E,
            vec_S=EXCLUDED.vec_S, vec_T=EXCLUDED.vec_T, vec_K=EXCLUDED.vec_K,
            vec_R=EXCLUDED.vec_R, vec_Q=EXCLUDED.vec_Q, vec_F=EXCLUDED.vec_F,
            vec_C=EXCLUDED.vec_C,
            coord_hash_raw=EXCLUDED.coord_hash_raw,
            coord_hash_full=EXCLUDED.coord_hash_full,
            dominant_vars=EXCLUDED.dominant_vars,
            magnitude=EXCLUDED.magnitude, state=EXCLUDED.state,
            classifier_confidence=EXCLUDED.classifier_confidence,
            updated_at=NOW()
        RETURNING identity_id
    """

    stat = path.stat() if path.exists() else None
    size = stat.st_size if stat else None
    created = datetime.fromtimestamp(stat.st_ctime) if stat else None
    modified = datetime.fromtimestamp(stat.st_mtime) if stat else None

    from fis.nlp.hash_codec import encode_hash
    hashes = encode_hash(vec, address.magnitude, address.state, dom)

    cur = conn.cursor()
    cur.execute(sql, (
        file_id, sha256,
        vec[0],vec[1],vec[2],vec[3],vec[4],
        vec[5],vec[6],vec[7],vec[8],vec[9],
        hashes['coord_hash_raw'], hashes['coord_hash_full'], dom,
        address.magnitude, address.state,
        path.name, path.suffix.lstrip('.'), size,
        created, modified,
        str(path.resolve()), folder_name,
        name_personal, name_research, name_professional, name_system,
        path.name, 'personal',
        meta.domain if meta else None,
        [],
        address.magnitude / 3.0,
        json.dumps({'canonical': canon_vec}),
        1,
        *dqm_from_vector(vec),
    ))
    row = cur.fetchone()
    conn.commit()
    return row[0]



def upsert_meta_classification(conn, sha256: str, identity_id: int,
                                meta, address) -> None:
    """Upsert meta_classification row."""
    # Map artifact state D/W/F/X → lifecycle state
    state_map = {'F': 'COMPLETE', 'W': 'ACTIVE', 'D': 'PENDING', 'X': 'PENDING'}
    lifecycle = meta.state if meta else state_map.get(address.state, 'ACTIVE')

    sql = """
        INSERT INTO meta_classification (
            identity_id, sha256,
            context, domain, function, state,
            context_confidence, domain_confidence,
            function_confidence, state_confidence,
            context_rule, domain_rule, function_rule, state_rule,
            auto_classified
        ) VALUES (%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s,%s, TRUE)
        ON CONFLICT (sha256) DO UPDATE SET
            context=EXCLUDED.context, domain=EXCLUDED.domain,
            function=EXCLUDED.function, state=EXCLUDED.state,
            context_confidence=EXCLUDED.context_confidence,
            domain_confidence=EXCLUDED.domain_confidence,
            function_confidence=EXCLUDED.function_confidence,
            state_confidence=EXCLUDED.state_confidence,
            updated_at=NOW()
    """
    cur = conn.cursor()
    cur.execute(sql, (
        identity_id, sha256,
        meta.context if meta else 'BUSINESS',
        meta.domain  if meta else 'WORK',
        meta.function if meta else 'CAPTURE',
        lifecycle,
        meta.context_confidence  if meta else 0.5,
        meta.domain_confidence   if meta else 0.5,
        meta.function_confidence if meta else 0.5,
        meta.state_confidence    if meta else 0.5,
        meta.context_rule  if meta else '',
        meta.domain_rule   if meta else '',
        meta.function_rule if meta else '',
        meta.state_rule    if meta else '',
    ))
    conn.commit()


def infer_relational_context(path: Path) -> list[dict]:
    """Infer relational context key-value pairs from the file path.

    Looks at folder names, drive letters, and path patterns.
    Returns list of {'key': str, 'value': str, 'confidence': float, 'source': str}
    """
    parts = [p.lower() for p in path.parts]
    rc = []

    def add(key, value, conf=0.7, src='path_inference'):
        rc.append({'key': key, 'value': value, 'confidence': conf, 'source': src})

    # Drive-level context
    if path.drive.lower() in ('o:', 'z:'):
        add('subdomain', 'theophysics', 0.9)
        add('project', 'theophysics', 0.9)
    elif path.drive.lower() == 'd:':
        if 'github' in parts:
            add('subdomain', 'engineering', 0.9)
            add('context_hint', 'business', 0.9)
    elif path.drive.lower() == 'b:':
        add('source', 'transfer_folder', 0.8)

    # Folder name signals
    folder = path.parent.name.lower()
    project_signals = {
        'gtq': 'gtq_series', 'genesis': 'gtq_series',
        'theophysics': 'theophysics', 'obsidian': 'theophysics',
        'tiktok': 'tiktok_apologetics', 'recon': 'tiktok_apologetics',
        'trading': 'stock_trading', 'stocks': 'stock_trading',
        'rental': 'rental_properties',
        'github': 'engineering', 'code': 'engineering',
        'exports': 'archive', 'export': 'archive',
        'downloads': 'inbox', 'desktop stay': 'inbox',
    }
    for signal, project in project_signals.items():
        if signal in folder:
            add('project', project, 0.75)
            break

    # Moral decline / TikTok recon
    if 'moral decline' in folder or 'moral_decline' in folder:
        add('project', 'tiktok_apologetics', 0.9)
        add('series', 'moral_decline', 0.9)

    # File naming patterns → role inference
    name = path.stem.lower()
    role_signals = {
        'canonical': 'canonical', 'final': 'final_reference',
        'draft': 'draft', 'spec': 'specification',
        'proof': 'formal_proof', 'axiom': 'axiom',
        'law': 'law_document', 'summary': 'summary',
        'template': 'template', 'readme': 'documentation',
        'schema': 'schema', 'config': 'configuration',
        'backup': 'backup', 'log': 'log',
    }
    for signal, role in role_signals.items():
        if signal in name:
            add('role', role, 0.8)
            break

    return rc


def store_relational_context(conn, sha256: str, rc_items: list[dict]) -> None:
    """Store relational context key-value pairs."""
    if not rc_items:
        return
    sql = """
        INSERT INTO relational_context (sha256, key, value, confidence, source)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (sha256, key, value) DO UPDATE SET
            confidence=EXCLUDED.confidence, source=EXCLUDED.source
    """
    cur = conn.cursor()
    for item in rc_items:
        try:
            cur.execute(sql, (
                sha256, item['key'], item['value'],
                item.get('confidence', 0.7), item.get('source', 'path_inference')
            ))
        except Exception as ex:
            log.warning(f"RC insert failed for {item}: {ex}")
    conn.commit()

