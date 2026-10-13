"""Patching the metadata owner intercepts real profile-domain calls."""
from profiles import metadata


def test_metadata_write_and_read_use_owner_yaml_seams(tmp_path, monkeypatch):
    written = []
    import utils
    real_write = utils.atomic_yaml_write
    def write(path, data, **kwargs):
        written.append((path, dict(data)))
        return real_write(path, data, **kwargs)
    monkeypatch.setattr(utils, "atomic_yaml_write", write)
    metadata.write_profile_meta(tmp_path, display_name="Operator", role=metadata.SETUP_ROLE)
    assert written[0][0] == tmp_path / "profile.yaml"
    assert metadata.read_profile_meta(tmp_path)["display_name"] == "Operator"
    metadata.drop_profile_role(tmp_path)
    assert len(written) == 2
    assert metadata.read_profile_meta(tmp_path)["role"] is None


def test_metadata_reader_returns_independent_previous_names(tmp_path):
    metadata.write_profile_meta(tmp_path, previous_names=["old"])
    first = metadata.read_profile_meta(tmp_path)
    first["previous_names"].append("foreign")
    assert metadata.read_profile_meta(tmp_path)["previous_names"] == ["old"]
