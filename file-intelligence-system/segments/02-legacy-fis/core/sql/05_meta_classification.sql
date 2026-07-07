-- =============================================================
-- META CLASSIFICATION LAYER — Schema
-- CONTEXT -> DOMAIN -> FUNCTION -> STATE
-- These enums are FROZEN. Do not add categories.
-- Anything more specific belongs in relational_context (key-value).
-- =============================================================

CREATE TYPE context_enum AS ENUM ('PERSONAL', 'BUSINESS');

CREATE TYPE domain_enum AS ENUM (
    'IDENTITY',     -- who you are / self-definition
    'EMOTION',      -- felt states, moods, psychological content
    'RELATIONSHIP', -- interpersonal bonds, contracts, correspondence
    'HEALTH',       -- physical/mental wellbeing, clinical records
    'FINANCE',      -- money, budgets, transactions, trading
    'WORK',         -- professional output, projects, deliverables
    'LEARNING',     -- knowledge acquisition, research, study
    'CREATION',     -- creative output: writing, art, frameworks
    'SPIRITUAL',    -- faith, theology, meaning, transcendence
    'LIFESTYLE'     -- habits, time, logistics, household
);

CREATE TYPE function_enum AS ENUM (
    'CAPTURE',   -- raw input, notes, clips, recordings
    'PLAN',      -- goals, outlines, roadmaps, schedules
    'ACT',       -- execution artifacts: code, tasks, procedures
    'TRACK',     -- logs, metrics, status records, journals
    'ANALYZE',   -- analysis, evaluation, comparison, audit
    'DECIDE',    -- decisions, policies, judgments, conclusions
    'DOCUMENT'   -- final records, references, canonical outputs
);

CREATE TYPE state_enum AS ENUM (
    'ACTIVE',    -- in use, being worked on
    'PENDING',   -- waiting for input or action
    'COMPLETE',  -- done, finalized
    'ARCHIVED'   -- historical, no longer active
);


-- =============================================================
-- META CLASSIFICATION TABLE
-- =============================================================
CREATE TABLE IF NOT EXISTS meta_classification (
    meta_id         SERIAL PRIMARY KEY,
    identity_id     INT REFERENCES file_identity(identity_id) ON DELETE CASCADE,
    sha256          TEXT NOT NULL,

    -- The four locked axes
    context         context_enum NOT NULL,
    domain          domain_enum  NOT NULL,
    function        function_enum NOT NULL,
    state           state_enum   NOT NULL,

    -- Confidence per axis (0-1): how certain was the mapper?
    context_confidence  REAL DEFAULT 0,
    domain_confidence   REAL DEFAULT 0,
    function_confidence REAL DEFAULT 0,
    state_confidence    REAL DEFAULT 0,

    -- Override support: human can correct any axis
    context_override  context_enum,
    domain_override   domain_enum,
    function_override function_enum,
    state_override    state_enum,
    override_at       TIMESTAMP,

    -- Which rule fired for each axis (for debugging / training)
    context_rule  TEXT,
    domain_rule   TEXT,
    function_rule TEXT,
    state_rule    TEXT,

    auto_classified  BOOLEAN NOT NULL DEFAULT TRUE,
    classified_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_meta_sha256 UNIQUE (sha256)
);

CREATE INDEX IF NOT EXISTS idx_mc_sha256   ON meta_classification(sha256);
CREATE INDEX IF NOT EXISTS idx_mc_context  ON meta_classification(context);
CREATE INDEX IF NOT EXISTS idx_mc_domain   ON meta_classification(domain);
CREATE INDEX IF NOT EXISTS idx_mc_function ON meta_classification(function);
CREATE INDEX IF NOT EXISTS idx_mc_state    ON meta_classification(state);


-- =============================================================
-- RELATIONAL CONTEXT TABLE
-- Infinite flexibility. Any org-specific or personal metadata.
-- Nothing here is a category. Everything here is a tag.
-- =============================================================
CREATE TABLE IF NOT EXISTS relational_context (
    rc_id       SERIAL PRIMARY KEY,
    sha256      TEXT NOT NULL,
    key         TEXT NOT NULL,   -- 'project','client','matter','owner','source','subdomain'
    value       TEXT NOT NULL,   -- 'theophysics','smith-v-jones','acme','david','email','legal'
    confidence  REAL DEFAULT 1.0,
    source      TEXT DEFAULT 'user',  -- 'user','path_inference','auto','api'
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_rc_key UNIQUE (sha256, key, value)
);

CREATE INDEX IF NOT EXISTS idx_rc_sha256 ON relational_context(sha256);
CREATE INDEX IF NOT EXISTS idx_rc_key    ON relational_context(key);
CREATE INDEX IF NOT EXISTS idx_rc_value  ON relational_context(value);
CREATE INDEX IF NOT EXISTS idx_rc_kv     ON relational_context(key, value);

-- =============================================================
-- MAPPING RULES TABLE
-- Auditable rules that drive auto-classification.
-- Rules fire in priority order. First match wins per axis.
-- =============================================================
CREATE TABLE IF NOT EXISTS mapping_rules (
    rule_id     SERIAL PRIMARY KEY,
    axis        TEXT NOT NULL CHECK (axis IN ('context','domain','function','state')),
    rule_name   TEXT NOT NULL UNIQUE,
    priority    SMALLINT NOT NULL DEFAULT 50,  -- lower = higher priority

    -- Conditions (all conditions in a rule must be true = AND logic)
    -- Vector thresholds: variable >= min_score
    cond_vec_G_gte  REAL, cond_vec_M_gte REAL, cond_vec_E_gte REAL,
    cond_vec_S_gte  REAL, cond_vec_T_gte REAL, cond_vec_K_gte REAL,
    cond_vec_R_gte  REAL, cond_vec_Q_gte REAL, cond_vec_F_gte REAL,
    cond_vec_C_gte  REAL,
    -- Dominant variable must be IN this list (JSON array)
    cond_dominant_in    TEXT,   -- e.g. '["G","GK","GKC","GKR"]'
    -- File state must be one of these
    cond_state_in       TEXT,   -- e.g. '["F","W"]'
    -- Extension must be one of these
    cond_extension_in   TEXT,   -- e.g. '[".py",".bat",".sh"]'
    -- Magnitude threshold
    cond_magnitude_gte  SMALLINT,

    -- Output: what value to assign if this rule fires
    output_value    TEXT NOT NULL,  -- 'PERSONAL', 'WORK', 'CAPTURE', etc.
    output_confidence REAL DEFAULT 0.8,

    description TEXT,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);


-- =============================================================
-- SEED: MAPPING RULES
-- These are the first-pass rules derived from the blind test
-- and the 90% convergence results.
-- Rules fire in priority order (lower number = higher priority).
-- All thresholds are on the 0.0-3.0 scale.
-- =============================================================

-- ---- CONTEXT RULES ----
INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_S_gte,cond_vec_Q_gte,output_value,output_confidence,description)
VALUES ('context','personal_strong_SQ',10,2.0,2.0,'PERSONAL',0.95,'High self + qualia = personal document');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_S_gte,output_value,output_confidence,description)
VALUES ('context','personal_S_dominant',20,2.5,'PERSONAL',0.85,'Strong self/personhood = personal');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_M_gte,cond_vec_K_gte,output_value,output_confidence,description)
VALUES ('context','business_MK',30,2.0,1.5,'BUSINESS',0.85,'Mechanism + knowledge = business tool/doc');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_F_gte,cond_vec_G_gte,output_value,output_confidence,description)
VALUES ('context','spiritual_GF',35,2.0,2.0,'PERSONAL',0.80,'Faith + authority = spiritual/personal');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_extension_in,output_value,output_confidence,description)
VALUES ('context','code_is_business',25,'[".py",".js",".bat",".sh",".ps1",".ts",".sql"]','BUSINESS',0.90,'Code files are business/work artifacts');

INSERT INTO mapping_rules (axis,rule_name,priority,output_value,output_confidence,description)
VALUES ('context','default_business',100,'BUSINESS',0.50,'Default fallback');

-- ---- DOMAIN RULES ----
INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_G_gte,cond_vec_F_gte,output_value,output_confidence,description)
VALUES ('domain','spiritual_GF',10,2.0,2.0,'SPIRITUAL',0.90,'Authority + faith = spiritual domain');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_S_gte,cond_vec_Q_gte,output_value,output_confidence,description)
VALUES ('domain','identity_SQ',15,2.0,1.5,'IDENTITY',0.85,'Self + qualia = identity documents');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_Q_gte,output_value,output_confidence,description)
VALUES ('domain','emotion_Q',20,2.5,'EMOTION',0.80,'Dominant qualia = emotional content');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_R_gte,cond_vec_K_gte,output_value,output_confidence,description)
VALUES ('domain','relationship_RK',25,2.0,1.0,'RELATIONSHIP',0.85,'Relation + knowledge = correspondence/contracts');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_T_gte,cond_vec_M_gte,output_value,output_confidence,description)
VALUES ('domain','finance_KTM',30,2.0,1.5,1.5,'FINANCE',0.85,'Knowledge + time + mechanism = finance tracking');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_M_gte,cond_vec_K_gte,output_value,output_confidence,description)
VALUES ('domain','work_MK',35,2.0,1.5,'WORK',0.80,'Mechanism + knowledge = work output');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_G_gte,cond_vec_K_gte,cond_vec_C_gte,output_value,output_confidence,description)
VALUES ('domain','creation_GKC',40,1.5,2.0,2.0,'CREATION',0.85,'Authority + knowledge + coherence = framework creation');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_G_gte,output_value,output_confidence,description)
VALUES ('domain','learning_KG',45,2.0,1.0,'LEARNING',0.75,'Knowledge + some authority = learning/research');

INSERT INTO mapping_rules (axis,rule_name,priority,output_value,output_confidence,description)
VALUES ('domain','default_work',100,'WORK',0.45,'Default fallback');


-- ---- FUNCTION RULES ----
INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_E_gte,cond_magnitude_gte,output_value,output_confidence,description)
VALUES ('function','capture_entropy',10,1.5,NULL,'CAPTURE',0.90,'High entropy = raw capture, unprocessed input');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_M_gte,cond_extension_in,output_value,output_confidence,description)
VALUES ('function','act_code',15,2.0,'[".py",".js",".bat",".sh",".ps1",".ts"]','ACT',0.95,'Code with mechanism = execution/action');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_T_gte,output_value,output_confidence,description)
VALUES ('function','track_KT',20,2.0,2.0,'TRACK',0.85,'Knowledge + time = tracking/logging');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_G_gte,cond_vec_K_gte,cond_vec_C_gte,cond_state_in,output_value,output_confidence,description)
VALUES ('function','decide_GKC_final',25,2.0,2.0,2.0,'["F"]','DECIDE',0.90,'Authority+knowledge+coherence, final = decision/policy');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_C_gte,cond_state_in,output_value,output_confidence,description)
VALUES ('function','document_KC_final',30,2.0,1.5,'["F"]','DOCUMENT',0.85,'Knowledge+coherence, final = canonical document');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_C_gte,output_value,output_confidence,description)
VALUES ('function','analyze_KC',35,2.0,1.5,'ANALYZE',0.80,'Knowledge+coherence, not final = analysis');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_K_gte,cond_vec_T_gte,cond_state_in,output_value,output_confidence,description)
VALUES ('function','plan_KT_draft',40,1.5,1.0,'["D","W"]','PLAN',0.80,'Knowledge+time, draft = plan/roadmap');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_vec_M_gte,output_value,output_confidence,description)
VALUES ('function','act_mechanism',45,2.0,'ACT',0.75,'Mechanism dominant = action/procedure');

INSERT INTO mapping_rules (axis,rule_name,priority,output_value,output_confidence,description)
VALUES ('function','default_capture',100,'CAPTURE',0.40,'Default fallback');

-- ---- STATE RULES ----
INSERT INTO mapping_rules (axis,rule_name,priority,cond_state_in,output_value,output_confidence,description)
VALUES ('state','complete_from_F',10,'["F"]','COMPLETE',0.95,'File state Final = COMPLETE');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_state_in,output_value,output_confidence,description)
VALUES ('state','active_from_W',20,'["W"]','ACTIVE',0.90,'File state Working = ACTIVE');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_state_in,output_value,output_confidence,description)
VALUES ('state','pending_from_D',30,'["D"]','PENDING',0.85,'File state Draft = PENDING');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_state_in,cond_vec_E_gte,output_value,output_confidence,description)
VALUES ('state','archived_fragment',40,'["X"]',1.5,'ARCHIVED',0.80,'Fragment + entropy = archived/junk');

INSERT INTO mapping_rules (axis,rule_name,priority,cond_state_in,output_value,output_confidence,description)
VALUES ('state','pending_fragment',50,'["X"]','PENDING',0.60,'Fragment without entropy = pending (incomplete not junk)');

INSERT INTO mapping_rules (axis,rule_name,priority,output_value,output_confidence,description)
VALUES ('state','default_active',100,'ACTIVE',0.40,'Default fallback');

-- =============================================================
-- UNIFIED SEARCH VIEW
-- One query to find any file by any combination of axes.
-- The law firm search + the researcher search converge here.
-- =============================================================
CREATE OR REPLACE VIEW v_full_address AS
SELECT
    fi.sha256,
    fi.file_name,
    fi.extension,
    fi.coord_hash_full                        AS semantic_address,
    array_to_string(fi.dominant_vars,'')      AS dominant,
    fi.vec_G, fi.vec_M, fi.vec_E, fi.vec_S, fi.vec_T,
    fi.vec_K, fi.vec_R, fi.vec_Q, fi.vec_F, fi.vec_C,
    fi.magnitude, fi.state,
    mc.context, mc.domain, mc.function, mc.state   AS lifecycle,
    fi.name_active,
    fi.source_path,
    fi.size_bytes,
    fi.created_at, fi.modified_at,
    fi.tier, fi.human_override,
    fi.classified_at
FROM file_identity fi
LEFT JOIN meta_classification mc ON fi.sha256 = mc.sha256;

-- Relational context is queried separately by sha256 join
-- e.g. SELECT * FROM relational_context WHERE sha256 = '...' AND key = 'project';

