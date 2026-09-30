from types import SimpleNamespace

from agent import auxiliary_model_resolution as auxiliary


def test_profile_default_is_the_provider_auxiliary_source(monkeypatch):
    profile = SimpleNamespace(name="provider-x", default_aux_model="cheap-model")
    monkeypatch.setattr("providers.get_provider_profile", lambda _provider: profile)
    assert auxiliary.select_provider_auxiliary_model("provider-x") == "cheap-model"


def test_dynamic_aux_recommendation_is_only_used_for_fast_opt_in(monkeypatch):
    class Profile:
        name = "provider-x"
        default_aux_model = "default-model"

        def resolve_aux_model(self):
            return "dynamic-model"

    monkeypatch.setattr("providers.get_provider_profile", lambda _provider: Profile())
    monkeypatch.setattr(auxiliary, "_fast_catalog_ids", lambda _provider: ())
    assert auxiliary.select_provider_auxiliary_model("provider-x") == "default-model"
    assert (
        auxiliary.select_provider_auxiliary_model("provider-x", prefer_fast=True)
        == "dynamic-model"
    )


def test_nous_policy_rejects_blocked_aux_default(monkeypatch):
    profile = SimpleNamespace(name="nous", default_aux_model="blocked/model")
    monkeypatch.setattr("providers.get_provider_profile", lambda _provider: profile)
    monkeypatch.setattr(auxiliary, "_nous_allowed_ids", lambda: {"allowed/model"})
    assert auxiliary.select_provider_auxiliary_model("nous") == ""


def test_declarative_provider_aux_and_vision_defaults_are_registered():
    from providers import get_provider_profile

    assert get_provider_profile("tencent-tokenhub").default_aux_model == "hy4-preview"
    assert get_provider_profile("tencent-tokenplan").default_aux_model == "hy4-preview"
    assert get_provider_profile("xiaomi").default_vision_model() == "mimo-v2.5"
    assert get_provider_profile("zai").default_vision_model() == "glm-5.3-flash"


def test_kimi_profiles_declare_vision_rejection():
    assert auxiliary.provider_rejects_vision_input("kimi-coding") is True
    assert auxiliary.provider_rejects_vision_input("kimi-coding-cn") is True


def test_declared_vision_default_lookup_does_not_need_live_discovery():
    assert auxiliary.is_declared_vision_default("mimo-v2.5") is True
    assert auxiliary.is_declared_vision_default("glm-5.3-flash") is True
    assert auxiliary.is_declared_vision_default("not-a-default") is False
