"""Seed Top of Mind sources, post the Master Equation, and call Ollama for analysis."""
import json, httpx, sys

HUB = "http://localhost:8100"
OLLAMA = "http://localhost:11434"
MODEL = "llama3.2:3b"

SOURCES = [
    {"source_id": "ollama", "label": "Ollama llama3.2 3b", "kind": "ai", "priority": 5},
    {"source_id": "claude-opus", "label": "Claude Opus", "kind": "ai", "priority": 8},
    {"source_id": "kimi-cli", "label": "Kimi CLI", "kind": "ai", "priority": 6},
    {"source_id": "codex", "label": "Codex", "kind": "ai", "priority": 7},
    {"source_id": "gpt", "label": "GPT", "kind": "ai", "priority": 5},
    {"source_id": "gemini-jim", "label": "Gemini Jim", "kind": "ai", "priority": 7},
]

MASTER_EQ = r"""
# THE THEOPHYSICS MASTER EQUATION
