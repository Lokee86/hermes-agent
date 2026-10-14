"""Canonical metadata for built-in auxiliary LLM tasks.

This module is import-light and owns the task identities shared by runtime policy,
plugin routing, CLI setup, and observability. UI code may decorate these entries but
must not maintain a separate Python-side identity registry.
"""

from __future__ import annotations


BUILTIN_AUX_TASKS: tuple[tuple[str, str, str], ...] = (
    ("vision", "Vision", "image/screenshot analysis"),
    ("compression", "Compression", "context summarization"),
    ("approval", "Approval", "smart command approval"),
    ("mcp", "MCP", "MCP tool reasoning"),
    ("title_generation", "Title generation", "session titles"),
    ("review", "Review", "/review reviewer subagent"),
    ("memory_query_rewrite", "Memory query rewrite", "memory retrieval queries"),
    ("tts_audio_tags", "TTS audio tags", "Gemini TTS tag insertion"),
    ("voice_chat", "Voice chat", "spoken voice-mode replies"),
    ("skills_hub", "Skills hub", "skills search/install"),
    ("triage_specifier", "Triage specifier", "kanban spec fleshing"),
    ("kanban_decomposer", "Kanban decomposer", "task decomposition"),
    ("profile_describer", "Profile describer", "auto profile descriptions"),
    ("curator", "Curator", "skill-usage review pass"),
)


def builtin_auxiliary_task_keys() -> frozenset[str]:
    return frozenset(key for key, _name, _description in BUILTIN_AUX_TASKS)


__all__ = ["BUILTIN_AUX_TASKS", "builtin_auxiliary_task_keys"]
