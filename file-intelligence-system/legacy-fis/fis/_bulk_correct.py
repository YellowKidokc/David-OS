"""Bulk corrections from Claude's review."""
from fis.db.models import update_file_status, insert_correction
from fis.db.connection import get_connection
import json

conn = get_connection()
cur = conn.cursor()

corrections = [
    # (file_id, correct_domain, correct_subjects, action, reason)
    (862, "TP", ["RO", "RS"], "approve", "I.xlsx is vague but domain is right"),
    (858, "TP", ["LG"], "approve_edited", "HOW_TO_ANALYZE papers — TP.LG is right, slug should be analyze-papers"),
    (911, "TP", ["CO", "MR"], "approve_edited", "Architecture of Coherence — slug should be architecture-coherence not div-class"),
    (903, "SY", ["CF", "ST"], "wrong_domain", "README_SETUP is system/config, not Theophysics"),
    (882, "SY", ["CF"], "wrong_domain", "OPENAI features doc is system/config"),
    (876, "TP", ["MR"], "approve_edited", "Moral Decay Release Plan — TP.MR is right, slug should be moral-decay-plan"),
    (856, "TP", ["AX", "RS"], "wrong_domain", "GEMINI_CLAIMS is Theophysics research extraction, not day trading"),
    (846, "SY", ["CF"], "wrong_domain", "ENGINE_AUDIT is system audit, not day trading"),
    (907, "TP", ["LG"], "approve_edited", "START_HERE — TP is right, slug should be start-here"),
    (883, "SY", ["CF"], "wrong_domain", "OPENAI quickstart is system config"),
    (881, "CB", ["OB", "SY"], "wrong_domain", "obsidian_postgres_sync is codebase, not day trading"),
    (816, "CB", ["SY"], "wrong_domain", "Audit_Explainer.py is code, not day trading"),
    (805, "SY", ["GN"], "skip", "exclude is a git file, skip"),
    (801, "SY", ["GN"], "skip", "HEAD is a git file, skip"),
    (897, "TP", ["JS", "RS"], "approve", "prophecy RSS urls — TP.JS is right"),
    (896, "TP", ["JS", "RS"], "approve", "prophecy RSS core — TP.JS is right"),
    (891, "SY", ["GN"], "wrong_domain", "Print.txt is a system file, not Theophysics"),
    (890, "SY", ["GN"], "wrong_domain", "Print.txt is a system file, not day trading"),
    (885, "SY", ["CF"], "wrong_domain", "OPENAI_TOOLS is system config, not Theophysics"),
    (863, "SY", ["CF"], "wrong_domain", "install bat is system config"),
]

for fid, domain, subjects, action, reason in corrections:
    # Get current file data
    cur.execute("SELECT * FROM files WHERE file_id = %s", (fid,))
    f = cur.fetchone()
    if not f:
        print(f"  SKIP {fid} — not found")
        continue

    old_domain = f["domain"] or ""
    old_subjects = f["subject_codes"] or []
    old_slug = f["slug"] or ""

    # Log the correction
    insert_correction(fid,
        {"domain": old_domain, "subjects": old_subjects, "slug": old_slug},
        {"domain": domain, "subjects": subjects, "slug": old_slug})

    # Log to bil_events
    rating = 5 if action == "approve" else (3 if "edited" in action else 1)
    cur.execute("""
        INSERT INTO bil_events (model_name, features, signal)
        VALUES ('file_feedback', %s, %s)
    """, (json.dumps({
        "file_id": fid, "action": action, "reason": reason,
        "old_domain": old_domain, "new_domain": domain,
        "old_subjects": old_subjects, "new_subjects": subjects,
    }), float(rating) / 5.0))

    # Update the file record
    if action == "skip":
        update_file_status(fid, "skipped")
        print(f"  SKIP {fid} {f['original_name']}")
    else:
        cur.execute("UPDATE files SET domain = %s, subject_codes = %s, status = 'corrected', updated_at = NOW() WHERE file_id = %s",
                    (domain, subjects, fid))
        print(f"  FIX  {fid} {f['original_name']:<45} {old_domain}->{domain} {old_subjects}->{subjects}")

conn.commit()
conn.close()
print("\nDone — 20 corrections applied.")
