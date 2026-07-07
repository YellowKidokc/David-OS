"""Bulk review — dump pending files for Claude to classify."""
from fis.db.models import get_pending_files

files = get_pending_files(limit=200)
print(f"Pending: {len(files)}")
print()
print(f"{'ID':>4} | {'Conf':>5} | {'Dom':>3} | {'Original':<50} | {'Proposed':<55}")
print("-" * 130)
for f in sorted(files, key=lambda x: x.get("confidence", 0), reverse=True):
    orig = (f["original_name"] or "")[:50]
    prop = (f["proposed_name"] or "")[:55]
    dom = f["domain"] or "??"
    conf = f["confidence"] or 0
    fid = f["file_id"]
    print(f"{fid:>4} | {conf:>4.0f}% | {dom:>3} | {orig:<50} | {prop:<55}")
