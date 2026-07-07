"""Phase 1 hash audit: compare file_intelligence_hub package copies across repos."""
import hashlib, os, json

COPIES = {
    "A_original_FIH":        r"D:\GitHub\File-intelligent-hub\file-intelligence-hub\file_intelligence_hub",
    "B_davidos_fihub":       r"D:\GitHub\David-OS\file-intelligence-system\fihub-source\file_intelligence_hub",
    "C_davidos_seg01":       r"D:\GitHub\David-OS\file-intelligence-system\segments\01-core-intelligence-hub\core\file_intelligence_hub",
    "D_tomapi_head":         r"D:\GitHub\tom_fis_api\apps\api\file_intelligence_hub",
    "E_topofmindapi":        r"D:\GitHub\Top-of-Mind-API\apps\api\file_intelligence_hub",
    "F_synology_stage":      r"D:\GitHub\Top-of-Mind-API\deploy\synology\.package-stage\apps\api\file_intelligence_hub",
    "G_topaifis_head":       r"D:\GitHub\TOP AI FIS\apps\api\file_intelligence_hub",
    "H_topaifis_vendored":   r"D:\GitHub\TOP AI FIS\integrations\file-intelligent-hub-source\file_intelligence_hub",
    "I_topaifis_tomapi_v":   r"D:\GitHub\TOP AI FIS\integrations\top-of-mind-api-source\apps\api\file_intelligence_hub",
}

def tree_hashes(root):
    out = {}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            h = hashlib.md5(open(p, "rb").read()).hexdigest()
            out[rel] = h
    return out

trees = {k: tree_hashes(v) for k, v in COPIES.items() if os.path.isdir(v)}
allfiles = sorted(set().union(*[set(t) for t in trees.values()]))

# Whole-tree identity groups
sig = {k: hashlib.md5(json.dumps(sorted(t.items())).encode()).hexdigest()[:10] for k, t in trees.items()}
groups = {}
for k, s in sig.items():
    groups.setdefault(s, []).append(k)
print("== IDENTITY GROUPS (identical trees share a group) ==")
for s, ks in groups.items():
    print(f"  {s}: {', '.join(ks)}")

# Unique files per copy (exist here, nowhere else)
print("\n== UNIQUE FILES PER COPY ==")
for k, t in trees.items():
    uniq = [f for f in t if sum(1 for t2 in trees.values() if f in t2) == 1]
    if uniq:
        print(f"  {k}: {', '.join(sorted(uniq))}")

# Divergent shared files among the three heads
heads = ["D_tomapi_head", "E_topofmindapi", "F_synology_stage", "G_topaifis_head"]
print("\n== SHARED-BUT-DIVERGENT FILES AMONG HEADS ==")
for f in allfiles:
    present = {h: trees[h][f] for h in heads if h in trees and f in trees[h]}
    if len(present) >= 2 and len(set(present.values())) > 1:
        print(f"  {f}: " + "; ".join(f"{h}={v[:8]}" for h, v in present.items()))
