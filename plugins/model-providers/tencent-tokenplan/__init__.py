"""Tencent TokenPlan provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

tencent_tokenplan = ProviderProfile(
    name="tencent-tokenplan",
    aliases=("tokenplan", "tencent-lkeap"),
    display_name="Tencent TokenPlan",
    api_mode="anthropic_messages",
    env_vars=("TOKENPLAN_API_KEY",),
    base_url="https://api.lkeap.cloud.tencent.com/plan/anthropic",
    base_url_env_var="TOKENPLAN_BASE_URL",
)

register_provider(tencent_tokenplan)
