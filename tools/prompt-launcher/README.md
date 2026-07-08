# David-OS Prompt Launcher

Purpose: keep online-coding prompts, Deep Research prompts, push targets, and launch steps in one repeatable place.
Date: 2026-07-07
Owner: codex
Status: TESTED by clipboard path only; Playwright path depends on your online coding page.

## Quick Start

From `D:\GitHub\David-OS`:

```bat
tools\prompt-launcher\launch_prompt.bat 001-deep-research
```

```bat
tools\prompt-launcher\launch_prompt.bat 002-watchers-control-plane
```

That copies the prompt to your clipboard and prints the target metadata.

To also open/fill the online page with Playwright:

```bat
tools\prompt-launcher\launch_prompt.bat 002-watchers-control-plane --playwright
```

The Playwright path reads `config.example.json`. Copy it to `config.local.json` and set URLs/selectors for each target:

- `coding`: online coding agent URL and selectors
- `research`: Deep Research URL and selectors

The launcher never submits automatically unless you pass `--submit`.

## Gemini Deep Research Export

Capture the completed Gemini Deep Research page and copy the visible report text:

```bat
tools\prompt-launcher\export_gemini_research.bat https://gemini.google.com/app/5066cf74c5e36b8d
```

It writes local files under `tools\prompt-launcher\research_exports\`:

- `gemini_research_capture.txt`
- `gemini_research_page.html`
- `gemini_research_page.png`
- `metadata.json`

To also attempt Share / Export to Google Docs:

```bat
tools\prompt-launcher\export_gemini_research.bat https://gemini.google.com/app/5066cf74c5e36b8d --docs
```

The Docs export depends on Gemini's current UI labels, so if it cannot find the button, it still leaves the captured text on the clipboard.

## Publish Latest Research Capture To GitHub

After a successful Gemini capture, publish the newest capture to a clean GitHub branch:

```bat
tools\prompt-launcher\publish_latest_research_to_github.bat
```

Default branch:

```text
codex/deep-research-captures
```

This copies the latest capture into `docs\research-captures\...`, commits it, and pushes it. Browser profiles, local config, `node_modules`, and raw working captures stay out of GitHub.

To prepare the commit without pushing:

```bat
tools\prompt-launcher\publish_latest_research_to_github.bat -NoPush
```

## Rule

Every coding prompt should include the exact push instruction. David should only need to track the prompt name, not the Git branch mechanics.
