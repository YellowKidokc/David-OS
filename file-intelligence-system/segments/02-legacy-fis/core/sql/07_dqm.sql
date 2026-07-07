
-- =============================================================
-- DATA QUALITY MATRIX — drop-in addition to file_identity
-- Deterministic quality tier from K, E, C only.
-- =============================================================
CREATE TYPE data_quality_enum AS ENUM ('GOLD','SOLID','DRAFT','NOISE','DEAD');

ALTER TABLE file_identity
    ADD COLUMN IF NOT EXISTS dqm_quality    data_quality_enum,
    ADD COLUMN IF NOT EXISTS dqm_confidence SMALLINT CHECK (dqm_confidence BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS dqm_flags      TEXT[];

CREATE INDEX IF NOT EXISTS idx_fi_dqm_quality ON file_identity(dqm_quality);
CREATE INDEX IF NOT EXISTS idx_fi_dqm_flags   ON file_identity USING GIN (dqm_flags);

-- Same for scoring.file_score
ALTER TABLE scoring.file_score
    ADD COLUMN IF NOT EXISTS dqm_quality    data_quality_enum,
    ADD COLUMN IF NOT EXISTS dqm_confidence SMALLINT,
    ADD COLUMN IF NOT EXISTS dqm_flags      TEXT[];

-- Useful filter views
CREATE OR REPLACE VIEW v_gold_files AS
    SELECT * FROM file_identity WHERE dqm_quality = 'GOLD' ORDER BY classified_at DESC;

CREATE OR REPLACE VIEW v_needs_work AS
    SELECT identity_id, file_name, coord_hash_full, dqm_quality, dqm_confidence, dqm_flags, source_path
    FROM file_identity
    WHERE dqm_quality IN ('DRAFT','NOISE','DEAD')
       OR 'HIGH_ENTROPY' = ANY(dqm_flags)
    ORDER BY dqm_confidence ASC;

CREATE OR REPLACE VIEW v_purge_candidates AS
    SELECT identity_id, file_name, size_bytes, source_path, dqm_confidence
    FROM file_identity
    WHERE dqm_quality = 'DEAD'
    ORDER BY size_bytes DESC;
