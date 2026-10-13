"""Shared synchronous and background installed-skill counts."""
import os
import threading
import time
from pathlib import Path

# In-process skill-count cache. Counting walks every skill's sub-tree (~4 fs calls per
# skill); ``list_profiles`` counts EVERY profile, and its two remaining Desktop callers
# (``GET /api/profiles``, ``profiles.list``) are POLLED every few seconds. Keyed by skills
# dir; a walk is repeated only when the tree signature changes (skill add/remove) or after
# the TTL (deep edits). Polled callers never walk: ``lazy_skill_count`` serves the last known
# value and refreshes stale entries on a background thread, at most once per recheck window
# per profile — the TTL is decoupled from the poll rate (#114041).
_SKILL_COUNT_CACHE: dict[str, tuple[float, float, int]] = {}
_SKILL_COUNT_TTL_SECONDS = 600.0
_SKILL_COUNT_RECHECK_SECONDS = 60.0
_SKILL_COUNT_NEXT_CHECK: dict[str, float] = {}
_SKILL_COUNT_LOCK = threading.Lock()
# One scan lock per skills dir so concurrent cold scans of the SAME profile share one walk
# while different profiles' scans still run in parallel.
_SKILL_COUNT_SCAN_LOCKS: dict[str, threading.Lock] = {}


def _skills_dir_signature(skills_dir: Path) -> float:
    """Max mtime of ``skills_dir`` and its immediate children (adding/removing a category
    bumps the root, a skill bumps its category). One scandir: O(#categories), not O(#files)."""
    try:
        sig = skills_dir.stat().st_mtime
    except OSError:
        return 0.0
    try:
        with os.scandir(skills_dir) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        sig = max(sig, entry.stat(follow_symlinks=False).st_mtime)
                except OSError:
                    continue
    except OSError:
        pass
    return sig


def _walk_skill_count(skills_dir: Path) -> int:
    """One ``os.walk`` over the skills tree (prunes ``.git``/``node_modules``/support dirs
    instead of statting them). Best-effort: a subtree that vanishes mid-walk (a concurrent
    skill install/update) is skipped, never raised — ``os.walk`` (``onerror=None``) swallows
    scandir errors itself, so one profile's churn cannot abort the whole enumeration."""
    from agent.skill_utils import iter_skill_index_files
    return sum(1 for _ in iter_skill_index_files(skills_dir, "SKILL.md"))


def count_skills(profile_dir: Path) -> int:
    """Count installed skills in a profile (cached by skills-dir signature + TTL). Walks
    synchronously when stale — detail surfaces (``hermes profile info``, ``profiles.describe``)
    want the fresh number; polled lists go through :func:`cached_skill_count`."""
    skills_dir = profile_dir / "skills"
    if not skills_dir.is_dir():
        return 0
    key = str(skills_dir)
    signature = _skills_dir_signature(skills_dir)
    cached = _SKILL_COUNT_CACHE.get(key)
    if cached is not None and cached[0] == signature and (time.time() - cached[1]) < _SKILL_COUNT_TTL_SECONDS:
        return cached[2]
    with _SKILL_COUNT_LOCK:
        scan_lock = _SKILL_COUNT_SCAN_LOCKS.setdefault(key, threading.Lock())
    with scan_lock:
        # Re-check under the lock: a concurrent caller may have just finished this walk.
        signature = _skills_dir_signature(skills_dir)
        cached = _SKILL_COUNT_CACHE.get(key)
        if cached is not None and cached[0] == signature and (time.time() - cached[1]) < _SKILL_COUNT_TTL_SECONDS:
            return cached[2]
        count = _walk_skill_count(skills_dir)
        # Stamp AFTER the walk: a scan longer than the TTL must not publish an already-expired entry.
        _SKILL_COUNT_CACHE[key] = (signature, time.time(), count)
        return count


def cached_skill_count(profile_dir: Path) -> int:
    """Last known skill count with ZERO skill-tree I/O on the calling thread. A never-counted
    or aged entry schedules one background :func:`count_skills` per profile per recheck
    window (which itself re-walks only on signature change / TTL); the next poll picks the
    result up. ``0`` until the first refresh lands."""
    key = str(profile_dir / "skills")
    now = time.time()
    with _SKILL_COUNT_LOCK:
        due = _SKILL_COUNT_NEXT_CHECK.get(key, 0.0) <= now
        if due:
            _SKILL_COUNT_NEXT_CHECK[key] = now + _SKILL_COUNT_RECHECK_SECONDS
    if due:
        from agent.memory_provider import spawn_context_thread
        spawn_context_thread(target=count_skills, args=(profile_dir,),
                             name="hermes-skill-count", daemon=True).start()
    cached = _SKILL_COUNT_CACHE.get(key)
    return cached[2] if cached is not None else 0


