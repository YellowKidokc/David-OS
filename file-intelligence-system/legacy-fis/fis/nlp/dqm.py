"""Data Quality Matrix — deterministic quality tier from K, E, C.

Inputs:  K, E, C ∈ {0..3}  (quantized from semantic vector)
Output:  quality_tier, confidence, flags

Tiers (priority order — first match wins):
  GOLD   K=3 ∧ E=0 ∧ C=3       canonical, publication-ready
  SOLID  K≥2 ∧ E≤1 ∧ C≥2      good, usable
  DRAFT  K≥1 ∧ E≥2 ∧ C≥1      needs work
  NOISE  E≥2 ∧ C≤1 ∧ K≤1      mostly noise
  DEAD   K=0 ∧ E≥2 ∧ C=0       no signal, purge candidate
"""

TIERS = ('GOLD', 'SOLID', 'DRAFT', 'NOISE', 'DEAD')


def _quantize(score: float) -> int:
    """Convert 0.0-3.0 float score to 0-3 int."""
    if score < 0.75: return 0
    if score < 1.50: return 1
    if score < 2.25: return 2
    return 3


def dqm(k_raw, e_raw, c_raw) -> tuple[str, int, list[str]]:
    """Evaluate data quality from K, E, C scores.

    Accepts either int (0-3) or float (0.0-3.0) scores.
    Returns (quality_tier, confidence_0_to_100, flags_list).
    """
    k = _quantize(k_raw) if isinstance(k_raw, float) else int(k_raw)
    e = _quantize(e_raw) if isinstance(e_raw, float) else int(e_raw)
    c = _quantize(c_raw) if isinstance(c_raw, float) else int(c_raw)

    # Tier evaluation — strict, priority order
    if k == 3 and e == 0 and c == 3:
        q = 'GOLD'
    elif k >= 2 and e <= 1 and c >= 2:
        q = 'SOLID'
    elif k >= 1 and e >= 2 and c >= 1:
        q = 'DRAFT'
    elif e >= 2 and c <= 1 and k <= 1:
        q = 'NOISE'
    elif k == 0 and e >= 2 and c == 0:
        q = 'DEAD'
    else:
        # Fallback by nearest priority
        if k >= 2 and c >= 2:    q = 'SOLID'
        elif e >= 2:              q = 'NOISE'
        else:                     q = 'DRAFT'

    # Confidence
    conf = 100 - 15 * e + 10 * k + 10 * c
    conf = max(0, min(100, conf))

    # Flags
    flags = []
    if e >= 2:                      flags.append('HIGH_ENTROPY')
    if c <= 1:                      flags.append('LOW_COHERENCE')
    if k <= 1:                      flags.append('LOW_KNOWLEDGE')
    if k == 3 and c == 3 and e == 0: flags.append('CANONICAL')

    return q, conf, flags


def dqm_from_vector(vector: list[float]) -> tuple[str, int, list[str]]:
    """Run DQM directly from a 10-variable float vector.
    Vector order: G M E S T K R Q F C
    """
    # K=index 5, E=index 2, C=index 9
    return dqm(vector[5], vector[2], vector[9])


def dqm_label(quality: str, confidence: int, flags: list[str]) -> str:
    """Single-line human label for display."""
    flag_str = f" [{','.join(flags)}]" if flags else ''
    return f"{quality}({confidence}){flag_str}"


if __name__ == '__main__':
    # Self-test
    tests = [
        ((3, 0, 3), ('GOLD',   100, ['CANONICAL'])),
        ((2, 1, 2), ('SOLID',   95, [])),
        ((1, 2, 1), ('DRAFT',   60, ['HIGH_ENTROPY'])),
        ((1, 2, 0), ('NOISE',   50, ['HIGH_ENTROPY','LOW_COHERENCE'])),
        ((0, 2, 0), ('DEAD',    40, ['HIGH_ENTROPY','LOW_COHERENCE','LOW_KNOWLEDGE'])),
    ]
    passed = 0
    for (k,e,c), (exp_q, exp_c, exp_f) in tests:
        q, conf, flags = dqm(k, e, c)
        ok = q == exp_q and conf == exp_c and set(flags) == set(exp_f)
        print(f"  {'OK' if ok else 'FAIL'} K={k} E={e} C={c} -> {q}({conf}) {flags}")
        if ok: passed += 1
    print(f"\n{passed}/{len(tests)} passed")
