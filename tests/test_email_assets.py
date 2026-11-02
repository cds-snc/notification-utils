import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest
from notifications_utils import email_assets
from notifications_utils.email_assets import (
    EMAIL_ASSETS_DIR,
    build,
    email_asset_urls,
    versioned_filenames,
)

JINJA_TEMPLATES_DIR = Path(email_assets.__file__).parent / "jinja_templates"


def test_versioned_filenames_include_content_hash():
    filenames = versioned_filenames()

    assert set(filenames) >= {"gc-logo-en.png", "gc-logo-fr.png", "canada-logo.png", "1x1-ffffff.png"}
    for name, versioned in filenames.items():
        digest = hashlib.sha256((EMAIL_ASSETS_DIR / name).read_bytes()).hexdigest()[:10]
        stem, suffix = name.rsplit(".", 1)
        assert versioned == f"{stem}-{digest}.{suffix}"


@pytest.mark.parametrize(
    "asset_domain, expected_domain",
    [
        (None, "assets.notification.canada.ca"),
        ("assets.staging.notification.cdssandbox.xyz", "assets.staging.notification.cdssandbox.xyz"),
    ],
)
def test_email_asset_urls(asset_domain, expected_domain):
    urls = email_asset_urls(asset_domain)

    for name, versioned in versioned_filenames().items():
        assert urls[name] == f"https://{expected_domain}/email-assets/{versioned}"


def test_every_asset_referenced_by_templates_exists():
    referenced = set()
    for template in JINJA_TEMPLATES_DIR.rglob("*.jinja2"):
        referenced |= set(re.findall(r"email_asset_urls\[['\"]([^'\"]+)['\"]\]", template.read_text()))

    assert referenced, "expected the email templates to reference email assets"
    assert referenced <= set(versioned_filenames())


def test_build_writes_content_addressed_copies(tmp_path):
    written = build(tmp_path / "out")

    assert sorted(p.name for p in written) == sorted(versioned_filenames().values())
    for name, versioned in versioned_filenames().items():
        assert (tmp_path / "out" / versioned).read_bytes() == (EMAIL_ASSETS_DIR / name).read_bytes()


def test_script_runs_without_package_dependencies(tmp_path):
    # CI runs this file directly with a bare python, before the package's dependencies are installed
    subprocess.run(
        [sys.executable, "-I", email_assets.__file__, str(tmp_path)],
        check=True,
        capture_output=True,
    )

    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(versioned_filenames().values())
