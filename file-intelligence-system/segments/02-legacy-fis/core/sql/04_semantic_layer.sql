-- =============================================================
-- FIS SEMANTIC LAYER — Schema v4
-- Universal Knowledge Coordinate System
-- Run AFTER 01_schema.sql, 02_seed_codes.sql, 03_flexible_codes.sql
--
-- Tables:
--   file_identity       — core vector + hash + names + metadata
--   variable_descriptors — hash region → human description
--   folder_contexts     — Chow/MDL decomposition per folder
--   file_trajectories   — audit trail of address changes
--   naming_templates    — profession-specific naming patterns
-- =============================================================

-- pgvector for nearest-neighbor queries in 10D space
-- Install: https://github.com/pgvector/pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- CORE: file_identity
-- =============================================================
CREATE TABLE IF NOT EXISTS file_identity (
    identity_id     SERIAL PRIMARY KEY,
    file_id         INT REFERENCES files(file_id) ON DELETE SET NULL,
    sha256          TEXT NOT NULL,

    -- SEMANTIC VECTOR (10 chi-variables, 0.0-3.0)
    -- Score the ARTIFACT, not the subject it discusses.
    vec_G  REAL NOT NULL DEFAULT 0,  -- Authority / Grace / Ground
    vec_M  REAL NOT NULL DEFAULT 0,  -- Matter / Mechanism / Mind
    vec_E  REAL NOT NULL DEFAULT 0,  -- Entropy / Noise / Disorder
    vec_S  REAL NOT NULL DEFAULT 0,  -- Spirit / Self / Personhood
    vec_T  REAL NOT NULL DEFAULT 0,  -- Time / Sequence / History
    vec_K  REAL NOT NULL DEFAULT 0,  -- Knowledge / Structure / Data
    vec_R  REAL NOT NULL DEFAULT 0,  -- Relation / Reference / Link
    vec_Q  REAL NOT NULL DEFAULT 0,  -- Qualia / Experience / Felt
    vec_F  REAL NOT NULL DEFAULT 0,  -- Faith / Trust / Commitment
    vec_C  REAL NOT NULL DEFAULT 0,  -- Coherence / Integration / Unity

    -- pgvector column: mirrors vec_G..vec_C as array for ANN queries
    -- e.g. ORDER BY vec_full <-> '[0.9,0,0,0,0,0.9,0,0,0,0.8]' LIMIT 10
    vec_full        VECTOR(10),

    -- COORDINATE HASH
    -- coord_hash_raw: 4-char Crockford base-32, encodes ALL 10 variable scores
    --   at 2 bits each = 20 bits total. Decodable. Locality-preserving.
    --   See hash_codec.py for encode/decode logic.
    -- coord_hash_full: human-readable semantic address
    --   Format: [DOMINANT_VARS]-[coord_hash_raw]-[MAGNITUDE][STATE]
    --   Example: GKC-3K5A-3F, MK-0A2B-2W, E-0000-1X
    coord_hash_raw  TEXT,
    coord_hash_full TEXT,
    dominant_vars   TEXT[] NOT NULL DEFAULT '{}',
    magnitude       SMALLINT NOT NULL DEFAULT 1 CHECK (magnitude BETWEEN 0 AND 3),
    state           CHAR(1)  NOT NULL DEFAULT 'X' CHECK (state IN ('D','W','F','X')),

    -- COMPLETENESS (artifact-level, not subject-level)
    structural_completeness REAL DEFAULT 0,  -- 0-1: has intro/body/conclusion
    reference_density       REAL DEFAULT 0,  -- 0-1: links per paragraph
    vocabulary_richness     REAL DEFAULT 0,  -- 0-1: unique terms / total

    -- PHYSICAL METADATA
    file_name       TEXT NOT NULL,
    extension       TEXT,
    size_bytes      BIGINT,
    created_at      TIMESTAMP,
    modified_at     TIMESTAMP,
    staleness_days  INT GENERATED ALWAYS AS (
        CASE WHEN modified_at IS NOT NULL AND created_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (modified_at - created_at))::INT / 86400
        ELSE NULL END
    ) STORED,

    -- CONTEXTUAL METADATA
    source_path     TEXT,
    folder_context  TEXT,        -- dominant hash of parent folder
    folder_depth    SMALLINT,
    sibling_count   INT,
    link_density    INT,

    -- NAME PROJECTIONS (same vector, 4 surfaces)
    name_personal     TEXT,   -- SLUG_DATE_ID.ext
    name_research     TEXT,   -- PROJECT_SERIES_TOPIC_DATE_STATUS.ext
    name_professional TEXT,   -- DEPT_DOCTYPE_SUBJECT_DATE_VERSION.ext
    name_system       TEXT,   -- FUNCTION_TARGET.ext
    name_active       TEXT,   -- currently on disk
    naming_mode TEXT NOT NULL DEFAULT 'personal'
                CHECK (naming_mode IN ('personal','research','professional','system')),

    -- DOMAIN / SUBJECT BRIDGE (backward compat with old FIS)
    domain        TEXT,
    subject_codes TEXT[],

    -- NLP METADATA
    keywords      TEXT[],
    entities      TEXT[],
    classifier_confidence REAL,
    scores_raw    JSONB,

    -- HUMAN OVERRIDE
    human_override  BOOLEAN NOT NULL DEFAULT FALSE,
    override_reason TEXT,
    overridden_by   TEXT,
    overridden_at   TIMESTAMP,

    -- TIER (user trust level with the system)
    tier SMALLINT NOT NULL DEFAULT 1 CHECK (tier BETWEEN 1 AND 3),
    -- 1=read-only dashboard, 2=suggest+approve popup, 3=full auto

    -- AUDIT
    classified_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_identity_sha256 UNIQUE (sha256)
);

-- Trigger: keep vec_full in sync with individual vec_* columns
CREATE OR REPLACE FUNCTION sync_vec_full()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.vec_full := ARRAY[
        NEW.vec_G, NEW.vec_M, NEW.vec_E, NEW.vec_S, NEW.vec_T,
        NEW.vec_K, NEW.vec_R, NEW.vec_Q, NEW.vec_F, NEW.vec_C
    ]::VECTOR(10);
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_vec_full ON file_identity;
CREATE TRIGGER trg_sync_vec_full
BEFORE INSERT OR UPDATE ON file_identity
FOR EACH ROW EXECUTE FUNCTION sync_vec_full();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fi_sha256       ON file_identity(sha256);
CREATE INDEX IF NOT EXISTS idx_fi_coord_raw    ON file_identity(coord_hash_raw);
CREATE INDEX IF NOT EXISTS idx_fi_coord_full   ON file_identity(coord_hash_full);
CREATE INDEX IF NOT EXISTS idx_fi_dominant     ON file_identity USING GIN (dominant_vars);
CREATE INDEX IF NOT EXISTS idx_fi_domain       ON file_identity(domain);
CREATE INDEX IF NOT EXISTS idx_fi_state        ON file_identity(state);
CREATE INDEX IF NOT EXISTS idx_fi_magnitude    ON file_identity(magnitude);
CREATE INDEX IF NOT EXISTS idx_fi_naming_mode  ON file_identity(naming_mode);
CREATE INDEX IF NOT EXISTS idx_fi_tier         ON file_identity(tier);
CREATE INDEX IF NOT EXISTS idx_fi_source_path  ON file_identity(source_path);
CREATE INDEX IF NOT EXISTS idx_fi_folder       ON file_identity(folder_context);
CREATE INDEX IF NOT EXISTS idx_fi_override     ON file_identity(human_override);

-- ANN vector index (IVFFlat, cosine similarity, 10D)
CREATE INDEX IF NOT EXISTS idx_fi_vec_ivf ON file_identity
    USING ivfflat (vec_full vector_cosine_ops) WITH (lists = 50);


-- =============================================================
-- DESCRIPTOR DICTIONARY
-- "Zip code guide" for the knowledge space.
-- Built from aggregated human filenames per region.
-- =============================================================
CREATE TABLE IF NOT EXISTS variable_descriptors (
    descriptor_id   SERIAL PRIMARY KEY,
    coord_pattern   TEXT NOT NULL,
    pattern_type    TEXT NOT NULL DEFAULT 'dominant'
                    CHECK (pattern_type IN ('dominant','raw_hash','region')),
    label_short     TEXT NOT NULL,
    label_full      TEXT,
    predicted_content TEXT,
    example_files   TEXT[],
    file_count      INT DEFAULT 0,
    avg_magnitude   REAL DEFAULT 0,
    dominant_extension TEXT,
    dominant_state  CHAR(1),
    profession_affinity TEXT[],
    enterprise_label TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_descriptor UNIQUE (coord_pattern, pattern_type)
);

INSERT INTO variable_descriptors
    (coord_pattern, pattern_type, label_short, label_full, predicted_content, profession_affinity)
VALUES
    ('GKC','dominant','Canonical Authority Framework',
     'Formal proofs, canonical specs, foundational constitutions. Grounded authority + dense knowledge + system integration.',
     'Formal proof or canonical framework document. Establishes foundational principles. Arrives at unified conclusion.',
     ARRAY['theology','mathematics','law','academia']),

    ('MK','dominant','Mechanism-Knowledge Tool',
     'Scripts, pipelines, technical specs, configs. High mechanism + structured knowledge.',
     'Functional tool that processes structured information. Clear input/output. May have TODOs.',
     ARRAY['engineering','devops','data-science']),

    ('RQF','dominant','Relational-Experiential-Commitment',
     'Speeches, testimonies, covenants, manifestos. Binds through shared experience.',
     'Document binding the reader through relational appeal and commitment under uncertainty.',
     ARRAY['theology','law','activism','personal']),

    ('GKR','dominant','Authority-Knowledge-Relational',
     'Constitutions, governing contracts, court decisions. Authoritative knowledge in relational context.',
     'Governing document establishing rules between connected parties.',
     ARRAY['law','government','policy']),

    ('KT','dominant','Temporal Knowledge Record',
     'Logs, changelogs, historical records. Structured knowledge anchored in time.',
     'Structured information record organized around timestamps or sequence.',
     ARRAY['devops','research','journalism','finance']),

    ('SQ','dominant','Personal-Experiential Narrative',
     'Diaries, novels, first-person accounts. High personhood + felt experience.',
     'Document expressing subjective experience. Rich in emotional and sensory language.',
     ARRAY['creative','personal','therapeutic']),

    ('E','dominant','Entropy / Unresolved',
     'Noise, fragments, clipboard dumps. Low signal, high ambiguity.',
     'Low-information artifact. Fragment or unfinished thought. Do not rely on without review.',
     ARRAY['any'])
ON CONFLICT (coord_pattern, pattern_type) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_vd_pattern    ON variable_descriptors(coord_pattern);
CREATE INDEX IF NOT EXISTS idx_vd_affinity   ON variable_descriptors USING GIN (profession_affinity);


-- =============================================================
-- FOLDER CONTEXTS  (Chow/MDL decomposition per folder)
-- =============================================================
CREATE TABLE IF NOT EXISTS folder_contexts (
    folder_id       SERIAL PRIMARY KEY,
    folder_path     TEXT NOT NULL UNIQUE,
    folder_name     TEXT,
    pattern_count   SMALLINT NOT NULL DEFAULT 1,
    pattern_type    TEXT NOT NULL DEFAULT 'UNIFORM'
                    CHECK (pattern_type IN ('UNIFORM','SPLIT','MIXED')),
    coverage_score  REAL,
    dominant_hash   TEXT,
    dominant_vars   TEXT[],
    vec_G_avg REAL, vec_M_avg REAL, vec_E_avg REAL, vec_S_avg REAL, vec_T_avg REAL,
    vec_K_avg REAL, vec_R_avg REAL, vec_Q_avg REAL, vec_F_avg REAL, vec_C_avg REAL,
    file_count      INT DEFAULT 0,
    loose_file_count INT DEFAULT 0,
    subfolder_count INT DEFAULT 0,
    outlier_file_ids INT[],
    outlier_count   INT DEFAULT 0,
    mdl_clusters    SMALLINT DEFAULT 1,
    mdl_score       REAL,
    last_scanned    TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fc_path     ON folder_contexts(folder_path);
CREATE INDEX IF NOT EXISTS idx_fc_type     ON folder_contexts(pattern_type);
CREATE INDEX IF NOT EXISTS idx_fc_dominant ON folder_contexts(dominant_hash);

-- =============================================================
-- FILE TRAJECTORIES  (semantic address audit log)
-- Watch ideas develop: E-1X -> KC-2W -> GKC-3F over months.
-- =============================================================
CREATE TABLE IF NOT EXISTS file_trajectories (
    trajectory_id   SERIAL PRIMARY KEY,
    sha256          TEXT NOT NULL,
    identity_id     INT REFERENCES file_identity(identity_id) ON DELETE SET NULL,
    coord_hash_full TEXT NOT NULL,
    dominant_vars   TEXT[],
    magnitude       SMALLINT,
    state           CHAR(1),
    vec_G REAL, vec_M REAL, vec_E REAL, vec_S REAL, vec_T REAL,
    vec_K REAL, vec_R REAL, vec_Q REAL, vec_F REAL, vec_C REAL,
    file_name       TEXT,
    file_path       TEXT,
    size_bytes      BIGINT,
    trigger         TEXT,   -- 'initial','correction','rescan','rename','move'
    triggered_by    TEXT,   -- 'system','user','batch','api'
    note            TEXT,
    recorded_at     TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ft_sha256  ON file_trajectories(sha256);
CREATE INDEX IF NOT EXISTS idx_ft_hash    ON file_trajectories(coord_hash_full);
CREATE INDEX IF NOT EXISTS idx_ft_ts      ON file_trajectories(recorded_at);


-- =============================================================
-- NAMING TEMPLATES  (profession/context-specific name patterns)
-- =============================================================
CREATE TABLE IF NOT EXISTS naming_templates (
    template_id     SERIAL PRIMARY KEY,
    template_name   TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    mode            TEXT NOT NULL CHECK (mode IN ('personal','research','professional','system')),
    -- Tokens: {DEPT} {DOCTYPE} {SUBJECT} {SLUG} {DATE} {VERSION} {STATUS} {SEQ} {EXT}
    pattern         TEXT NOT NULL,
    profession_tags TEXT[],
    preferred_regions TEXT[],   -- dominant var patterns: 'GKC', 'MK', etc.
    example_output  TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO naming_templates
    (template_name, display_name, mode, pattern, profession_tags, preferred_regions, example_output)
VALUES
    ('personal_default','Personal / Creative','personal',
     '{SLUG}_{DATE}_{SEQ}.{EXT}',
     ARRAY['personal','creative','student'],ARRAY['SQ','QF','RF'],
     'master-equation-10-laws_20260411_000001.md'),

    ('research_default','Research / Academic','research',
     '{PROJECT}_{SERIES}_{TOPIC}_{DATE}_{STATUS}.{EXT}',
     ARRAY['academia','science','theology','philosophy'],ARRAY['GKC','KC','GK','GKRC'],
     'THEOPHYSICS_GTQ-01_genesis-information_20260401_final.html'),

    ('legal','Legal / Compliance','professional',
     '{DEPT}_{DOCTYPE}_{SUBJECT}_{DATE}_v{VERSION}.{EXT}',
     ARRAY['law','compliance','government','policy'],ARRAY['GKR','KRF','RF'],
     'LEGAL_brief_smith-v-jones_20260421_v3.docx'),

    ('finance','Finance / Accounting','professional',
     '{DEPT}_{PERIOD}_{DOCTYPE}_{DATE}_v{VERSION}.{EXT}',
     ARRAY['finance','accounting','trading'],ARRAY['KMT','MT','KT'],
     'FINANCE_Q1-2026_revenue-report_20260401_v2.xlsx'),

    ('engineering','Engineering / Technical','professional',
     '{SYSTEM}_{COMPONENT}_{DOCTYPE}_{DATE}_v{VERSION}.{EXT}',
     ARRAY['engineering','devops','architecture'],ARRAY['MK','MKC','MC'],
     'FIS_pipeline_spec_20260421_v3.md'),

    ('system_default','System / Infrastructure','system',
     '{FUNCTION}_{TARGET}.{EXT}',
     ARRAY['devops','system'],ARRAY['M','MK','MT'],
     'pipeline_fis.py'),

    ('theophysics_research','Theophysics Research','research',
     '{PROJECT}_{LAW_OR_SERIES}_{TOPIC}_{DATE}_{STATUS}.{EXT}',
     ARRAY['theophysics','theology','physics','philosophy'],ARRAY['GKC','GKRC','GK'],
     'THEOPHYSICS_LAW-09_moral-conservation_20260416_canonical.md')
ON CONFLICT (template_name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_nt_mode      ON naming_templates(mode);
CREATE INDEX IF NOT EXISTS idx_nt_tags      ON naming_templates USING GIN (profession_tags);
CREATE INDEX IF NOT EXISTS idx_nt_regions   ON naming_templates USING GIN (preferred_regions);


-- =============================================================
-- HELPER VIEWS
-- =============================================================

-- Files with semantic address + region label
CREATE OR REPLACE VIEW v_semantic_files AS
SELECT
    fi.identity_id, fi.sha256, fi.file_name, fi.extension,
    fi.coord_hash_full                        AS address,
    array_to_string(fi.dominant_vars, '')     AS dominant,
    fi.magnitude, fi.state,
    fi.vec_G, fi.vec_M, fi.vec_E, fi.vec_S, fi.vec_T,
    fi.vec_K, fi.vec_R, fi.vec_Q, fi.vec_F, fi.vec_C,
    vd.label_short                            AS region_label,
    fi.name_active, fi.naming_mode, fi.domain,
    fi.classifier_confidence                  AS confidence,
    fi.human_override, fi.tier, fi.source_path, fi.classified_at
FROM file_identity fi
LEFT JOIN variable_descriptors vd
    ON array_to_string(fi.dominant_vars,'') = vd.coord_pattern
    AND vd.pattern_type = 'dominant';

-- Entropy report: files that need attention
CREATE OR REPLACE VIEW v_entropy_report AS
SELECT identity_id, file_name, coord_hash_full, vec_E,
       magnitude, state, source_path, classifier_confidence, classified_at
FROM file_identity
WHERE vec_E >= 1.5
ORDER BY vec_E DESC, magnitude ASC;

-- Cluster summary by dominant variable group
CREATE OR REPLACE VIEW v_cluster_by_dominant AS
SELECT
    array_to_string(dominant_vars,'') AS dominant,
    COUNT(*)                          AS file_count,
    ROUND(AVG(vec_G)::NUMERIC,2)      AS avg_G,
    ROUND(AVG(vec_M)::NUMERIC,2)      AS avg_M,
    ROUND(AVG(vec_E)::NUMERIC,2)      AS avg_E,
    ROUND(AVG(vec_K)::NUMERIC,2)      AS avg_K,
    ROUND(AVG(vec_C)::NUMERIC,2)      AS avg_C,
    ROUND(AVG(magnitude)::NUMERIC,2)  AS avg_magnitude,
    MODE() WITHIN GROUP (ORDER BY state) AS common_state
FROM file_identity
GROUP BY array_to_string(dominant_vars,'')
ORDER BY file_count DESC;

-- File evolution over time
CREATE OR REPLACE VIEW v_file_evolution AS
SELECT sha256, file_name, coord_hash_full, magnitude, state, trigger, recorded_at
FROM file_trajectories
ORDER BY sha256, recorded_at;

-- Nearest neighbors (requires pgvector):
-- Find files semantically similar to sha256 'abc123':
-- SELECT b.file_name, b.coord_hash_full,
--        a.vec_full <-> b.vec_full AS distance
-- FROM file_identity a, file_identity b
-- WHERE a.sha256 = 'abc123' AND b.sha256 != 'abc123'
-- ORDER BY distance LIMIT 10;
