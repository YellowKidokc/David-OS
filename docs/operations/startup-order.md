# Startup Order

1. Start the central hub API.
2. Open or create `data/sqlite/fis_hub.sqlite`.
3. Load node config from `config/nodes`.
4. Load folder profiles from `config/folders`.
5. Load rules from `config/rules`.
6. Start local watchers only for enabled profiles.
7. Run node heartbeat every 30-60 seconds.
8. Queue file events.
9. Scan/classify/label through hub jobs.
10. Propose actions; do not execute destructive actions without approval.

