"""Meta Classification Mapper.

Reads a SemanticAddress (10-variable vector + state + magnitude)
and fires mapping rules to produce CONTEXT → DOMAIN → FUNCTION → STATE.

Rules are loaded from Postgres mapping_rules table at startup.
First-match-wins per axis, sorted by priority ascending.

Usage:
    from fis.nlp.meta_mapper import MetaMapper
    mapper = MetaMapper(conn)
    result = mapper.classify(address, extension='.py')
    # result.context, result.domain, result.function, result.state
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)

VALID_CONTEXT  = {'PERSONAL', 'BUSINESS'}
VALID_DOMAIN   = {'IDENTITY','EMOTION','RELATIONSHIP','HEALTH','FINANCE',
                  'WORK','LEARNING','CREATION','SPIRITUAL','LIFESTYLE'}
VALID_FUNCTION = {'CAPTURE','PLAN','ACT','TRACK','ANALYZE','DECIDE','DOCUMENT'}
VALID_STATE    = {'ACTIVE','PENDING','COMPLETE','ARCHIVED'}

VAR_NAMES = ['G','M','E','S','T','K','R','Q','F','C']


@dataclass
class MetaResult:
    context:  str
    domain:   str
    function: str
    state:    str
    context_confidence:  float = 0.0
    domain_confidence:   float = 0.0
    function_confidence: float = 0.0
    state_confidence:    float = 0.0
    context_rule:  str = ''
    domain_rule:   str = ''
    function_rule: str = ''
    state_rule:    str = ''

    @property
    def path(self) -> str:
        return f"{self.context}/{self.domain}/{self.function}/{self.state}"


class MetaMapper:
    def __init__(self, conn=None):
        """conn: psycopg2 connection. If None, falls back to hardcoded rules."""
        self._rules = {'context': [], 'domain': [], 'function': [], 'state': []}
        if conn:
            self._load_from_db(conn)
        else:
            self._load_defaults()

    def _load_from_db(self, conn):
        cur = conn.cursor()
        cur.execute("""
            SELECT axis, rule_name, priority,
                   cond_vec_G_gte, cond_vec_M_gte, cond_vec_E_gte,
                   cond_vec_S_gte, cond_vec_T_gte, cond_vec_K_gte,
                   cond_vec_R_gte, cond_vec_Q_gte, cond_vec_F_gte,
                   cond_vec_C_gte, cond_dominant_in, cond_state_in,
                   cond_extension_in, cond_magnitude_gte,
                   output_value, output_confidence
            FROM mapping_rules WHERE active = TRUE
            ORDER BY axis, priority ASC
        """)
        for row in cur.fetchall():
            self._rules[row[0]].append(row)
        log.info(f"Loaded {sum(len(v) for v in self._rules.values())} mapping rules from DB")


    def classify(self, address, extension: str = '') -> MetaResult:
        """Classify a SemanticAddress into the four meta axes.

        address: SemanticAddress from semantic_scorer.py
        extension: file extension including dot (e.g. '.py')
        """
        vec = address.vector   # list[float], index = VAR_NAMES position
        file_state = address.state    # D/W/F/X
        magnitude  = address.magnitude
        dominant   = address.dominant  # list of var names

        ctx,  ctx_conf,  ctx_rule  = self._fire('context',  vec, dominant, file_state, magnitude, extension)
        dom,  dom_conf,  dom_rule  = self._fire('domain',   vec, dominant, file_state, magnitude, extension)
        func, func_conf, func_rule = self._fire('function', vec, dominant, file_state, magnitude, extension)
        st,   st_conf,   st_rule   = self._fire('state',    vec, dominant, file_state, magnitude, extension)

        return MetaResult(
            context=ctx,  domain=dom,  function=func,  state=st,
            context_confidence=ctx_conf,   domain_confidence=dom_conf,
            function_confidence=func_conf, state_confidence=st_conf,
            context_rule=ctx_rule, domain_rule=dom_rule,
            function_rule=func_rule, state_rule=st_rule,
        )

    def _fire(self, axis: str, vec, dominant, file_state, magnitude, ext):
        """Fire rules for one axis. Returns (output_value, confidence, rule_name)."""
        g, m, e, s, t, k, r, q, f, c = vec

        for rule in self._rules[axis]:
            (_, name, _, min_G, min_M, min_E, min_S, min_T, min_K,
             min_R, min_Q, min_F, min_C,
             dom_in_json, state_in_json, ext_in_json,
             mag_gte, output, confidence) = rule

            # Check all conditions (None = don't care = pass)
            if min_G is not None and g < min_G: continue
            if min_M is not None and m < min_M: continue
            if min_E is not None and e < min_E: continue
            if min_S is not None and s < min_S: continue
            if min_T is not None and t < min_T: continue
            if min_K is not None and k < min_K: continue
            if min_R is not None and r < min_R: continue
            if min_Q is not None and q < min_Q: continue
            if min_F is not None and f < min_F: continue
            if min_C is not None and c < min_C: continue
            if mag_gte is not None and magnitude < mag_gte: continue

            if dom_in_json:
                allowed = json.loads(dom_in_json)
                dom_str = ''.join(dominant)
                if not any(dom_str.startswith(d) for d in allowed): continue

            if state_in_json:
                allowed = json.loads(state_in_json)
                if file_state not in allowed: continue

            if ext_in_json:
                allowed = json.loads(ext_in_json)
                if ext.lower() not in allowed: continue

            return output, confidence, name

        return 'WORK', 0.3, 'fallback'   # last resort


    def _load_defaults(self):
        """Hardcoded fallback rules when no DB is available.
        Mirrors the seeded mapping_rules in 05_meta_classification.sql.
        Format: (axis, name, priority, min_G,M,E,S,T,K,R,Q,F,C,
                  dom_in, state_in, ext_in, mag_gte, output, confidence)
        """
        def r(axis, name, pri, output, conf, **kw):
            row = [axis, name, pri]
            for v in ['G','M','E','S','T','K','R','Q','F','C']:
                row.append(kw.get(f'min_{v}'))
            row += [
                kw.get('dom_in'), kw.get('state_in'),
                kw.get('ext_in'), kw.get('mag_gte'),
                output, conf
            ]
            return tuple(row)

        code_ext = '[".py",".js",".bat",".sh",".ps1",".ts",".sql"]'

        self._rules['context'] = [
            r('context','personal_strong_SQ',10,'PERSONAL',0.95, min_S=2.0,min_Q=2.0),
            r('context','personal_S',        20,'PERSONAL',0.85, min_S=2.5),
            r('context','spiritual_GF',      35,'PERSONAL',0.80, min_G=2.0,min_F=2.0),
            r('context','code_is_business',  25,'BUSINESS',0.90, ext_in=code_ext),
            r('context','business_MK',       30,'BUSINESS',0.85, min_M=2.0,min_K=1.5),
            r('context','default_business', 100,'BUSINESS',0.50),
        ]
        self._rules['domain'] = [
            r('domain','spiritual_GF',    10,'SPIRITUAL',    0.90, min_G=2.0,min_F=2.0),
            r('domain','identity_SQ',     15,'IDENTITY',     0.85, min_S=2.0,min_Q=1.5),
            r('domain','emotion_Q',       20,'EMOTION',      0.80, min_Q=2.5),
            r('domain','relationship_RK', 25,'RELATIONSHIP', 0.85, min_R=2.0,min_K=1.0),
            r('domain','finance_KTM',     30,'FINANCE',      0.85, min_K=2.0,min_T=1.5,min_M=1.5),
            r('domain','work_MK',         35,'WORK',         0.80, min_M=2.0,min_K=1.5),
            r('domain','creation_GKC',    40,'CREATION',     0.85, min_G=1.5,min_K=2.0,min_C=2.0),
            r('domain','learning_KG',     45,'LEARNING',     0.75, min_K=2.0,min_G=1.0),
            r('domain','default_work',   100,'WORK',         0.45),
        ]
        self._rules['function'] = [
            r('function','capture_entropy',   10,'CAPTURE',  0.90, min_E=1.5),
            r('function','act_code',          15,'ACT',      0.95, min_M=2.0, ext_in=code_ext),
            r('function','track_KT',          20,'TRACK',    0.85, min_K=2.0,min_T=2.0),
            r('function','decide_GKC_final',  25,'DECIDE',   0.90, min_G=2.0,min_K=2.0,min_C=2.0, state_in='["F"]'),
            r('function','document_KC_final', 30,'DOCUMENT', 0.85, min_K=2.0,min_C=1.5, state_in='["F"]'),
            r('function','analyze_KC',        35,'ANALYZE',  0.80, min_K=2.0,min_C=1.5),
            r('function','plan_KT_draft',     40,'PLAN',     0.80, min_K=1.5,min_T=1.0, state_in='["D","W"]'),
            r('function','act_mechanism',     45,'ACT',      0.75, min_M=2.0),
            r('function','default_capture',  100,'CAPTURE',  0.40),
        ]
        self._rules['state'] = [
            r('state','complete_F',  10,'COMPLETE', 0.95, state_in='["F"]'),
            r('state','active_W',    20,'ACTIVE',   0.90, state_in='["W"]'),
            r('state','pending_D',   30,'PENDING',  0.85, state_in='["D"]'),
            r('state','archived_X',  40,'ARCHIVED', 0.80, state_in='["X"]', min_E=1.5),
            r('state','pending_X',   50,'PENDING',  0.60, state_in='["X"]'),
            r('state','default',    100,'ACTIVE',   0.40),
        ]

        # Sort each axis by priority
        for axis in self._rules:
            self._rules[axis].sort(key=lambda x: x[2])
        log.info("Loaded default hardcoded mapping rules")

