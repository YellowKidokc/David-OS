#!/usr/bin/env python3
import argparse
import json
import uuid
from pathlib import Path

from unified_global_watcher import load_config


def main():
    p = argparse.ArgumentParser(description="Submit a manual inspect request to the global watcher")
    p.add_argument("path")
    p.add_argument("--config", default="config.example.json")
    p.add_argument("--reason", default="manual_request")
    p.add_argument("--priority", default="normal")
    args = p.parse_args()

    cfg = load_config(args.config)
    req_dir = Path(cfg.request_dir)
    req_dir.mkdir(parents=True, exist_ok=True)

    job = {
        "path": args.path,
        "reason": args.reason,
        "priority": args.priority,
    }
    out = req_dir / f"inspect_{uuid.uuid4()}.json"
    out.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()