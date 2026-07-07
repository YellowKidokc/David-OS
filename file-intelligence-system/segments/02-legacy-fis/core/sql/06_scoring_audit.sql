-- =============================================================
-- FIS SCORING + AUDIT LAYER — Schema v1
-- The NLP learning loop. Every suggestion. Every correction.
-- Every pattern the system got right or wrong.
--
-- Principle: the NLP never loses context.
-- Run AFTER 01-05.
-- =============================================================

CREATE SCHEMA IF NOT EXISTS scoring;

-- =============================================================
-- SESSION — one per run / batch
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.session (
    session_id      SERIAL PRIMARY KEY,
    session_name    TEXT,                       -- 'desktop_stay_20260421', 'github_scan', etc.
    root_path       TEXT NOT NULL,
    run_mode        TEXT NOT NULL DEFAULT 'dry_run'
                    CHECK (run_mode IN ('dry_run','tier1','tier2','tier3')),
    files_total     INT DEFAULT 0,
    files_scored    INT DEFAULT 0,
    files_accepted  INT DEFAULT 0,
    files_rejected  INT DEFAULT 0,
    files_modified  INT DEFAULT 0,
    files_errored   INT DEFAULT 0,
    avg_confidence  REAL,
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP,
    notes           TEXT
);

-- =============================================================
-- FILE SCORE — the canonical scoring record for each file
-- Stores BOTH what NLP suggested AND what the user ended up with
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.file_score (
    score_id        SERIAL PRIMARY KEY,
    session_id      INT REFERENCES scoring.session(session_id) ON DELETE CASCADE,
    sha256          TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    file_path       TEXT,
    extension       TEXT,
    size_bytes      BIGINT,

    -- ORIGINAL STATE (frozen at time of scoring — never changes)
    orig_name       TEXT,
    orig_path       TEXT,

    -- NLP SUGGESTION (what the system proposed)
    nlp_vec_G       REAL, nlp_vec_M REAL, nlp_vec_E REAL,
    nlp_vec_S       REAL, nlp_vec_T REAL, nlp_vec_K REAL,
    nlp_vec_R       REAL, nlp_vec_Q REAL, nlp_vec_F REAL,
    nlp_vec_C       REAL,
    nlp_dominant    TEXT[],
    nlp_magnitude   SMALLINT,
    nlp_state       CHAR(1),
    nlp_hash_full   TEXT,                       -- GKC-3K5A-3F
    nlp_canonical   TEXT,                       -- G3|M0|E0|S0|T1|K3|R1|Q0|F0|C3
    nlp_context     TEXT,
    nlp_domain      TEXT,
    nlp_function    TEXT,
    nlp_lifecycle   TEXT,
    nlp_confidence  REAL,                       -- overall 0-1

    -- FINAL STATE (what was actually accepted — may differ from NLP)
    final_dominant  TEXT[],
    final_hash_full TEXT,
    final_canonical TEXT,
    final_context   TEXT,
    final_domain    TEXT,
    final_function  TEXT,
    final_lifecycle TEXT,

    -- OUTCOME
    outcome         TEXT DEFAULT 'pending'
                    CHECK (outcome IN ('pending','accepted','rejected','modified','skipped','error')),
    outcome_note    TEXT,

    scored_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMP,

    CONSTRAINT uq_score_session_sha UNIQUE (session_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_fs_session  ON scoring.file_score(session_id);
CREATE INDEX IF NOT EXISTS idx_fs_sha256   ON scoring.file_score(sha256);
CREATE INDEX IF NOT EXISTS idx_fs_outcome  ON scoring.file_score(outcome);
CREATE INDEX IF NOT EXISTS idx_fs_nlp_hash ON scoring.file_score(nlp_hash_full);


-- =============================================================
-- DIMENSION CONFIDENCE — per-variable confidence score
-- Why was the NLP uncertain about G? About C?
-- This is what trains the signal words over time.
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.dimension_confidence (
    dim_id          SERIAL PRIMARY KEY,
    score_id        INT NOT NULL REFERENCES scoring.file_score(score_id) ON DELETE CASCADE,
    sha256          TEXT NOT NULL,

    -- Confidence per variable (0-1): how certain was the scorer?
    conf_G  REAL, conf_M REAL, conf_E REAL,
    conf_S  REAL, conf_T REAL, conf_K REAL,
    conf_R  REAL, conf_Q REAL, conf_F REAL,
    conf_C  REAL,

    -- Signal word counts that fired per variable (diagnostic)
    signals_G INT DEFAULT 0, signals_M INT DEFAULT 0, signals_E INT DEFAULT 0,
    signals_S INT DEFAULT 0, signals_T INT DEFAULT 0, signals_K INT DEFAULT 0,
    signals_R INT DEFAULT 0, signals_Q INT DEFAULT 0, signals_F INT DEFAULT 0,
    signals_C INT DEFAULT 0,

    -- Which signals fired (JSON array of word:weight pairs)
    top_signals     JSONB,

    -- Structural heuristic contributions (JSON)
    heuristic_scores JSONB,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dc_score_id ON scoring.dimension_confidence(score_id);
CREATE INDEX IF NOT EXISTS idx_dc_sha256   ON scoring.dimension_confidence(sha256);

-- =============================================================
-- CHANGE RECORD — every user correction, with reason
-- This is the training signal. Never throw it away.
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.change_record (
    change_id       SERIAL PRIMARY KEY,
    score_id        INT NOT NULL REFERENCES scoring.file_score(score_id) ON DELETE CASCADE,
    sha256          TEXT NOT NULL,
    session_id      INT,

    -- What changed (field name + old value + new value)
    field_changed   TEXT NOT NULL,          -- 'dominant','context','domain','function','lifecycle'
    old_value       TEXT,
    new_value       TEXT,

    -- Why (optional — from popup)
    change_reason   TEXT,                   -- 'wrong_domain','wrong_function','misclassified','override'
    change_source   TEXT NOT NULL DEFAULT 'user'
                    CHECK (change_source IN ('user','batch','api','auto_correction')),

    changed_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cr_score_id  ON scoring.change_record(score_id);
CREATE INDEX IF NOT EXISTS idx_cr_sha256    ON scoring.change_record(sha256);
CREATE INDEX IF NOT EXISTS idx_cr_field     ON scoring.change_record(field_changed);
CREATE INDEX IF NOT EXISTS idx_cr_reason    ON scoring.change_record(change_reason);

-- =============================================================
-- NLP FEEDBACK — structured learning signal
-- When NLP was wrong, what SHOULD it have done?
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.nlp_feedback (
    feedback_id     SERIAL PRIMARY KEY,
    score_id        INT NOT NULL REFERENCES scoring.file_score(score_id) ON DELETE CASCADE,
    sha256          TEXT NOT NULL,

    -- The mistake
    mistake_type    TEXT NOT NULL
                    CHECK (mistake_type IN (
                        'wrong_dominant','wrong_context','wrong_domain',
                        'wrong_function','wrong_lifecycle','wrong_magnitude',
                        'wrong_state','overconfident','underconfident','entropy_miss'
                    )),

    -- The correction
    nlp_said        TEXT,   -- what NLP suggested
    should_be       TEXT,   -- what it should have been

    -- Which signals caused the mistake (if known)
    misleading_signals TEXT[],

    -- Severity: how far off was it?
    severity        SMALLINT DEFAULT 1 CHECK (severity BETWEEN 1 AND 3),
    -- 1 = minor (right neighborhood, wrong exact value)
    -- 2 = moderate (wrong domain/function)
    -- 3 = major (completely wrong quadrant)

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nf_score_id ON scoring.nlp_feedback(score_id);
CREATE INDEX IF NOT EXISTS idx_nf_mistake  ON scoring.nlp_feedback(mistake_type);
CREATE INDEX IF NOT EXISTS idx_nf_severity ON scoring.nlp_feedback(severity);

-- =============================================================
-- BATCH SUMMARY — metrics per session
-- =============================================================
CREATE TABLE IF NOT EXISTS scoring.batch_summary (
    summary_id      SERIAL PRIMARY KEY,
    session_id      INT NOT NULL REFERENCES scoring.session(session_id) ON DELETE CASCADE,

    -- Acceptance metrics
    total_files     INT,
    accepted        INT,
    rejected        INT,
    modified        INT,
    acceptance_rate REAL,           -- accepted / total
    modification_rate REAL,         -- modified / (accepted + modified)

    -- Confidence metrics
    avg_confidence  REAL,
    min_confidence  REAL,
    max_confidence  REAL,
    low_conf_count  INT,            -- files < 0.5 confidence
    high_conf_count INT,            -- files > 0.8 confidence

    -- Domain distribution (JSON: {'WORK': 45, 'CREATION': 30, ...})
    domain_dist     JSONB,
    function_dist   JSONB,
    context_dist    JSONB,
    dominant_dist   JSONB,

    -- Error analysis
    entropy_count   INT,
    error_count     INT,
    top_mistakes    JSONB,          -- ['wrong_domain x12', 'wrong_function x8']

    computed_at     TIMESTAMP NOT NULL DEFAULT NOW()
);


-- =============================================================
-- VIEWS — what the NLP engine reads to understand itself
-- =============================================================

-- Reversibility: original vs final for every file
CREATE OR REPLACE VIEW scoring.v_reversibility AS
SELECT
    fs.session_id, fs.sha256, fs.file_name,
    fs.nlp_hash_full    AS suggested,
    fs.nlp_canonical    AS suggested_vector,
    fs.final_hash_full  AS final,
    fs.final_canonical  AS final_vector,
    fs.outcome,
    fs.nlp_confidence,
    fs.scored_at, fs.resolved_at,
    CASE
        WHEN fs.outcome = 'accepted'  THEN 'NLP was right'
        WHEN fs.outcome = 'rejected'  THEN 'NLP was wrong — user reset'
        WHEN fs.outcome = 'modified'  THEN 'NLP was partially right'
        WHEN fs.outcome = 'pending'   THEN 'Awaiting user review'
        ELSE fs.outcome
    END AS interpretation
FROM scoring.file_score fs;

-- Pattern accuracy: which dominant patterns the NLP gets right most often
CREATE OR REPLACE VIEW scoring.v_pattern_accuracy AS
SELECT
    nlp_hash_full               AS suggested_address,
    array_to_string(nlp_dominant,'') AS suggested_dominant,
    COUNT(*)                    AS total,
    COUNT(*) FILTER (WHERE outcome = 'accepted')  AS accepted,
    COUNT(*) FILTER (WHERE outcome = 'rejected')  AS rejected,
    COUNT(*) FILTER (WHERE outcome = 'modified')  AS modified,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'accepted')::NUMERIC / NULLIF(COUNT(*),0) * 100,
        1
    )                           AS accuracy_pct,
    ROUND(AVG(nlp_confidence)::NUMERIC, 2) AS avg_confidence
FROM scoring.file_score
WHERE outcome != 'pending'
GROUP BY nlp_hash_full, array_to_string(nlp_dominant,'')
ORDER BY total DESC;

-- NLP metrics: overall performance per session
CREATE OR REPLACE VIEW scoring.v_nlp_metrics AS
SELECT
    s.session_id,
    s.session_name,
    s.root_path,
    s.run_mode,
    s.files_total,
    ROUND(
        COUNT(fs.*) FILTER (WHERE fs.outcome='accepted')::NUMERIC
        / NULLIF(COUNT(fs.*) FILTER (WHERE fs.outcome!='pending'), 0) * 100, 1
    ) AS acceptance_pct,
    ROUND(AVG(fs.nlp_confidence)::NUMERIC, 2) AS avg_confidence,
    COUNT(nf.*) AS total_feedback,
    s.started_at,
    s.completed_at
FROM scoring.session s
LEFT JOIN scoring.file_score fs ON s.session_id = fs.session_id
LEFT JOIN scoring.nlp_feedback nf ON fs.score_id = nf.score_id
GROUP BY s.session_id, s.session_name, s.root_path,
         s.run_mode, s.files_total, s.started_at, s.completed_at
ORDER BY s.session_id DESC;

-- =============================================================
-- FUNCTION: export_nlp_context
-- Clean interface: what to give the NLP engine at session start.
-- Summarizes what it got right, what it got wrong, what to watch for.
-- =============================================================
CREATE OR REPLACE FUNCTION scoring.export_nlp_context(p_session_id INT DEFAULT NULL)
RETURNS TABLE (
    category    TEXT,
    key         TEXT,
    value       TEXT
) LANGUAGE sql AS $$

    -- Accuracy by dominant pattern
    SELECT 'pattern_accuracy' AS category,
           suggested_dominant AS key,
           accuracy_pct::TEXT || '% (' || total || ' files)' AS value
    FROM scoring.v_pattern_accuracy
    WHERE total >= 3
    UNION ALL

    -- Common mistakes
    SELECT 'common_mistake',
           mistake_type,
           COUNT(*)::TEXT || ' occurrences, avg severity '
               || ROUND(AVG(severity)::NUMERIC,1)::TEXT
    FROM scoring.nlp_feedback
    GROUP BY mistake_type
    HAVING COUNT(*) >= 2
    ORDER BY COUNT(*) DESC
    UNION ALL

    -- Low confidence patterns (where NLP is unsure)
    SELECT 'low_confidence_pattern',
           array_to_string(nlp_dominant,''),
           'avg confidence ' || ROUND(AVG(nlp_confidence)::NUMERIC,2)::TEXT
    FROM scoring.file_score
    WHERE nlp_confidence < 0.5
    GROUP BY array_to_string(nlp_dominant,'')
    HAVING COUNT(*) >= 2
    UNION ALL

    -- Session summary if provided
    SELECT 'session_summary', key, value
    FROM (
        SELECT 'total_files'     AS key, files_total::TEXT AS value FROM scoring.session WHERE session_id = p_session_id
        UNION ALL
        SELECT 'acceptance_pct', acceptance_pct::TEXT FROM scoring.v_nlp_metrics WHERE session_id = p_session_id
        UNION ALL
        SELECT 'avg_confidence', avg_confidence::TEXT FROM scoring.v_nlp_metrics WHERE session_id = p_session_id
    ) x
    WHERE p_session_id IS NOT NULL;
$$;

