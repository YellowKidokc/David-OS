## Global watcher and external inspect-call bridge

- Main folder: `file-intelligence-system/watchers/global-watcher/`
- Use this for "file watcher goes through every folder" + "files and folders inventory".
- It emits inspect jobs to `jobs/incoming` and accepts manual requests through:
  - `jobs/inspect_requests` (written by `request_file_inspect.py` or `.bat`)
- Continuous and low-resource by default (event dedupe + timed scans).
