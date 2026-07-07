"""Hash Codec — Universal Semantic Address Encoder/Decoder.

The FIS coordinate hash is NOT a cryptographic hash.
It is a LOCALITY-PRESERVING, DECODABLE coordinate in 10D meaning-space.

DESIGN
------
  - 2 bits per variable × 10 variables = 20 bits total
  - Bit mapping (MSB → LSB):  G M E S T K R Q F C
  - 4-char Crockford base-32 (5 bits/char, no I/L/O/U confusion)
  - Similar files produce similar hashes (nearby in space = nearby in hash)

2-BIT QUANTIZATION
------------------
  Score 0.00 – 0.74  → 0 (absent)
  Score 0.75 – 1.49  → 1 (low)
  Score 1.50 – 2.24  → 2 (medium)
  Score 2.25 – 3.00  → 3 (high / defining)

BIT LAYOUT (20 bits, MSB first)
--------------------------------
  Char 0 (bits 19-15): G[1] G[0] M[1] M[0] E[1]
  Char 1 (bits 14-10): E[0] S[1] S[0] T[1] T[0]
  Char 2 (bits  9- 5): K[1] K[0] R[1] R[0] Q[1]
  Char 3 (bits  4- 0): Q[0] F[1] F[0] C[1] C[0]

FULL SEMANTIC ADDRESS FORMAT
-----------------------------
  [DOMINANT_VARS]-[coord_hash_raw]-[MAGNITUDE][STATE]
  Examples:
    GKC-3K5A-3F   (Authority+Knowledge+Coherence, comprehensive, final)
    MK-0A2B-2W    (Mechanism+Knowledge, substantial, working)
    E-0000-1X     (Entropy dominant, fragment, incomplete)
    RQFC-8NTV-3F  (complex multi-variable, final)
"""

VAR_NAMES = ['G', 'M', 'E', 'S', 'T', 'K', 'R', 'Q', 'F', 'C']

# Crockford base-32 alphabet (no I, L, O, U)
B32_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
B32_DECODE   = {c: i for i, c in enumerate(B32_ALPHABET)}



def _score_to_bits(score: float) -> int:
    """Quantize a 0.0-3.0 score to 2 bits.
    0.00-0.74 -> 0 (absent)
    0.75-1.49 -> 1 (low)
    1.50-2.24 -> 2 (medium)
    2.25-3.00 -> 3 (high)
    """
    if score < 0.75: return 0
    if score < 1.50: return 1
    if score < 2.25: return 2
    return 3


def _bits_to_score(bits: int) -> float:
    """Dequantize 2 bits back to a representative score."""
    return [0.0, 1.0, 1.75, 2.75][bits & 0b11]


def encode_hash(vector: list[float], magnitude: int, state: str,
                dominant: list[str]) -> dict:
    """Encode a 10-variable vector into the full semantic address.

    Returns dict with:
      coord_hash_raw:  4-char Crockford base-32 (all 10 vars, decodable)
      coord_hash_full: human-readable address
                       Format: [DOMINANT]-[RAW]-[MAGNITUDE][STATE]
                       Example: GKC-3K5A-3F

    Bit layout (MSB to LSB, 20 bits):
      bits 19-18: G   bits 17-16: M   bits 15-14: E   bits 13-12: S
      bits 11-10: T   bits  9- 8: K   bits  7- 6: R   bits  5- 4: Q
      bits  3- 2: F   bits  1- 0: C

    Encoding:  4 chars × 5 bits = 20 bits (Crockford base-32)
      char[0]: bits 19-15  (G[1] G[0] M[1] M[0] E[1])
      char[1]: bits 14-10  (E[0] S[1] S[0] T[1] T[0])
      char[2]: bits  9- 5  (K[1] K[0] R[1] R[0] Q[1])
      char[3]: bits  4- 0  (Q[0] F[1] F[0] C[1] C[0])
    """
    g, m, e, s, t, k, r, q, f, c = [_score_to_bits(v) for v in vector]

    bits = (
        (g << 18) | (m << 16) | (e << 14) | (s << 12) |
        (t << 10) | (k <<  8) | (r <<  6) | (q <<  4) |
        (f <<  2) | (c <<  0)
    )

    raw = ''.join(
        B32_ALPHABET[(bits >> (15 - i * 5)) & 0x1F]
        for i in range(4)
    )

    dom_label = ''.join(dominant) if dominant else 'E'
    full = f"{dom_label}-{raw}-{magnitude}{state}"

    return {'coord_hash_raw': raw, 'coord_hash_full': full}



def decode_hash(coord_hash_full: str) -> dict:
    """Decode a full semantic address back to its components.

    'GKC-3K5A-3F' ->
      dominant: ['G','K','C']
      coord_hash_raw: '3K5A'
      magnitude: 3
      state: 'F'
      vector_approx: {G:2.75, M:0.0, E:0.0, ..., K:2.75, ..., C:2.75}

    Also accepts raw 4-char hash: '3K5A' (magnitude/state not decoded)
    """
    result = {
        'dominant': [], 'coord_hash_raw': '',
        'magnitude': 0, 'state': 'W',
        'vector_approx': {v: 0.0 for v in VAR_NAMES},
        'readable': ''
    }

    parts = coord_hash_full.split('-')

    if len(parts) == 3:
        dom_str, raw, ms = parts
        result['dominant'] = list(dom_str)
        result['coord_hash_raw'] = raw
        if len(ms) >= 2:
            try:
                result['magnitude'] = int(ms[0])
            except ValueError:
                pass
            result['state'] = ms[1] if len(ms) > 1 else 'W'
    elif len(parts) == 1 and len(parts[0]) == 4:
        raw = parts[0]
        result['coord_hash_raw'] = raw
    else:
        return result

    raw = result['coord_hash_raw'].upper()
    if len(raw) != 4 or not all(c in B32_DECODE for c in raw):
        return result

    # Decode 4 chars -> 20 bits
    bits = 0
    for ch in raw:
        bits = (bits << 5) | B32_DECODE[ch]

    scores = [(bits >> (18 - i*2)) & 0b11 for i in range(10)]
    result['vector_approx'] = {
        VAR_NAMES[i]: _bits_to_score(scores[i]) for i in range(10)
    }

    # Human-readable interpretation
    dominant = result['dominant'] or [
        VAR_NAMES[i] for i, s in enumerate(scores) if s >= 2
    ]
    state_map = {'D':'Draft','W':'Working','F':'Final','X':'Fragment'}
    mag_map   = {0:'empty',1:'fragment',2:'substantial',3:'comprehensive'}
    result['readable'] = (
        f"{'|'.join(dominant)}-dominant, "
        f"{mag_map.get(result['magnitude'],'?')}, "
        f"{state_map.get(result['state'],'?')}"
    )

    return result


def human_score_string(vector: list[float]) -> str:
    """Full decodable score string in Bible-coordinate style.

    G3|M0|E0|S0|T1|K3|R1|Q0|F0|C3

    Every segment is VARIABLE_NAME + QUANTIZED_SCORE (0-3).
    The order is canonical: G M E S T K R Q F C — never changes.
    A human who knows the variable order can decode any value.
    """
    parts = [f"{VAR_NAMES[i]}{_score_to_bits(v)}" for i, v in enumerate(vector)]
    return '|'.join(parts)


def parse_human_score_string(s: str) -> list[float]:
    """Reverse of human_score_string.

    'G3|M0|E0|S0|T1|K3|R1|Q0|F0|C3' -> [2.75, 0.0, 0.0, 0.0, 1.0, 2.75, 1.0, 0.0, 0.0, 2.75]
    """
    parts = s.split('|')
    if len(parts) != 10:
        raise ValueError(f"Expected 10 segments, got {len(parts)}: {s}")
    result = []
    for part in parts:
        var = part[0]
        bits = int(part[1])
        if var not in VAR_NAMES:
            raise ValueError(f"Unknown variable: {var}")
        result.append(_bits_to_score(bits))
    return result


if __name__ == '__main__':
    # Quick self-test
    test_vector = [2.9, 0.1, 0.0, 0.2, 1.1, 2.8, 0.9, 0.1, 0.2, 2.7]
    dominant = ['G', 'K', 'C']

    encoded = encode_hash(test_vector, magnitude=3, state='F', dominant=dominant)
    print(f"Encoded:   {encoded['coord_hash_full']}")

    decoded = decode_hash(encoded['coord_hash_full'])
    print(f"Decoded:   {decoded['readable']}")
    print(f"Vec approx: {decoded['vector_approx']}")

    score_str = human_score_string(test_vector)
    print(f"Score str: {score_str}")
    roundtrip = parse_human_score_string(score_str)
    print(f"Roundtrip: {roundtrip}")
    print("PASS" if len(roundtrip) == 10 else "FAIL")
