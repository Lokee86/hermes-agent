"""Small cached profile values shared by CLI and runtime discovery."""
from pathlib import Path
from profiles.metadata import _cached_profile_read, _load_yaml_dict

def read_distribution_meta(profile_dir: Path) -> tuple:
    """``(name, version, source)`` from ``distribution.yaml``; ``(None, None, None)`` if absent."""
    def _read() -> tuple:
        data = _load_yaml_dict(profile_dir / "distribution.yaml")
        if data is None:
            return None, None, None
        return data.get("name"), data.get("version"), data.get("source")

    return _cached_profile_read(profile_dir / "distribution.yaml", "distribution", _read)


def read_config_model(profile_dir: Path) -> tuple:
    """Read model/provider from a profile's config.yaml. Returns (model, provider)."""
    config_path = profile_dir / "config.yaml"
    if not config_path.exists():
        return None, None

    def _read() -> tuple:
        model_cfg = (_load_yaml_dict(config_path) or {}).get("model", {})
        if isinstance(model_cfg, str):
            return model_cfg, None
        if isinstance(model_cfg, dict):
            return model_cfg.get("default") or model_cfg.get("model"), model_cfg.get("provider")
        return None, None

    return _cached_profile_read(config_path, "config-model", _read)


