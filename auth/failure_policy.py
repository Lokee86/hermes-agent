"""Runtime authentication failure classification."""

from auth.errors import AuthError
from auth.constants import CODEX_RATE_LIMITED_CODE


def is_rate_limited_auth_error(error: Exception) -> bool:
    """True when an :class:`AuthError` is upstream rate-limiting / quota: transient, and
    re-authenticating cannot fix it, so callers should say "retry later", not ``hermes auth``."""
    return (isinstance(error, AuthError) and not error.relogin_required
            and error.code == CODEX_RATE_LIMITED_CODE)
