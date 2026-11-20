"""Live acceptance for the reviewed Reliquary build on a native CI runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from hermes_yaml import safe_load


ROOT = Path(__file__).resolve().parents[2]
RELEASE_COMMIT = "0ad300940c0d6d77d39ad0078ab0a8674dd421b5"
HOST_PATH = "host/reliquary-hermes-host"
HOST_SHA256 = {
    "linux-amd64": "b4ebf060cb5c86cbe4551ebd05692f3b65b9f4b9ae3c369036e3d047a4e467e1",
    "linux-arm64": "9e72056bb3c80337a8dc8f75770be9cfe9b4bce5ff6c556b82190fac5f750bab",
    "macos-amd64": "bd73963a150cf6fe11711f5c3a83bb11e1a909fdbce539367e0bd10c0f7711a0",
    "macos-arm64": "b11ca4ea35b0959be4aca6dc173c3ee235fcbecb6e3e356159ac64897cce6546",
}


def seed_catalog(entry_path: Path, profile: Path) -> dict:
    reviewed = safe_load(entry_path.read_text(encoding="utf-8"))
    if (reviewed["name"], reviewed["version"], reviewed["sha"]) != ("reliquary", "0.3.0", RELEASE_COMMIT):
        raise SystemExit("The proof requires the prepared Reliquary v0.3.0 catalog entry.")
    if reviewed["native_assets"]["destination"] != HOST_PATH:
        raise SystemExit("The prepared entry differs from Reliquary's expected host location.")

    catalog_dir = profile.parent / "catalog"
    catalog_dir.mkdir()
    shutil.copyfile(entry_path, catalog_dir / "reliquary.yaml")
    cache = profile / "cache"
    subprocess.run(
        [sys.executable, str(ROOT / "website" / "scripts" / "extract-plugins.py"),
         "--catalog-dir", str(catalog_dir), "--output-dir", str(cache)],
        check=True,
    )
    cache_file = cache / "plugin-catalog.json"
    snapshot = json.loads(cache_file.read_text(encoding="utf-8"))
    if snapshot["entries"] != [reviewed]:
        raise SystemExit("The catalog publisher changed or dropped the prepared entry.")
    # This checkout implements native assets before Hermes has a release with the feature.
    snapshot["entries"][0]["requires_hermes"] = ">=0.23.0"
    cache_file.write_text(json.dumps(snapshot), encoding="utf-8")
    return reviewed


def desktop_install() -> None:
    from tui_gateway import server

    result = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "plugins.manage",
        "params": {
            "action": "install",
            "catalog_name": "reliquary",
            "inspected_sha": RELEASE_COMMIT,
            "enable": False,
        },
    })
    if not result or not result.get("result", {}).get("ok"):
        raise SystemExit(f"Desktop catalog install failed: {result}")


def verify_install(profile: Path, entry: dict, target: str) -> None:
    plugins = profile / "plugins"
    installed = plugins / "reliquary"
    receipt = json.loads((plugins / ".install-metadata.json").read_text(encoding="utf-8"))["reliquary"]
    revision = subprocess.check_output(["git", "-C", str(installed), "rev-parse", "HEAD"], text=True).strip()
    if revision != RELEASE_COMMIT or receipt["revision"] != RELEASE_COMMIT:
        raise SystemExit("The catalog install did not use the reviewed source commit.")
    expected_asset = {
        "target": target,
        "sha256": entry["native_assets"]["targets"][target]["sha256"],
        "path": HOST_PATH,
    }
    if receipt["catalog"]["native_asset"] != expected_asset:
        raise SystemExit(f"The installer did not record the reviewed archive for {target}.")
    host = installed / HOST_PATH
    with host.open("rb") as stream:
        installed_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    if installed_hash != HOST_SHA256[target] or not os.access(host, os.X_OK):
        raise SystemExit(f"The installed host is not the published executable for {target}.")

    subprocess.run(
        [sys.executable, str(installed / "tests" / "smoke_packaged_host.py"), str(profile)],
        check=True, timeout=120,
    )
    print(f"Catalog install verified on {target} using the published Reliquary v0.3.0 archive.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", type=Path, help="path to the prepared Reliquary v0.3.0 catalog YAML")
    parser.add_argument("target", choices=HOST_SHA256)
    parser.add_argument("--desktop", action="store_true", help="install via the Desktop backend")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="hermes-native-catalog-") as scratch:
        profile = Path(scratch).resolve() / "profile"
        os.environ["HERMES_HOME"] = str(profile)
        entry = seed_catalog(args.entry, profile)
        if args.desktop:
            desktop_install()
        else:
            subprocess.run(
                [sys.executable, "-m", "hermes_cli.main", "plugins", "install",
                 "reliquary", "--no-enable", "--yes-deps"],
                cwd=ROOT, check=True, timeout=480,
            )
        verify_install(profile, entry, args.target)


if __name__ == "__main__":
    main()
