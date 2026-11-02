import hashlib
import re
from pathlib import Path

import pytest
from notifications_utils import email_assets
from notifications_utils.email_assets import (
    EMAIL_ASSETS_DIR,
    SUPPORTED_EXTENSIONS,
    email_asset_urls,
    versioned_filenames,
)

JINJA_TEMPLATES_DIR = Path(email_assets.__file__).parent / "jinja_templates"


def test_includes_default_branding_images():
    assert set(versioned_filenames()) >= {"gc-logo-en.png", "gc-logo-fr.png", "canada-logo.png", "1x1-ffffff.png"}


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


def test_every_asset_has_an_extension_terraform_uploads():
    for name in versioned_filenames():
        # terraform's fileset() pattern is case-sensitive
        assert Path(name).suffix in SUPPORTED_EXTENSIONS, name


def test_versioned_filenames_match_terraform_naming():
    # Must match the key terraform computes in notification-terraform aws/common/uploadS3Assets.tf:
    # "${regex("^(.+)\\.([^.]+)$", file)[0]}-${substr(filesha256(file), 0, 10)}.${regex(...)[1]}"
    for name, versioned in versioned_filenames().items():
        match = re.fullmatch(r"(.+)\.([^.]+)", name)
        assert match, name
        stem, extension = match.groups()
        digest = hashlib.sha256((EMAIL_ASSETS_DIR / name).read_bytes()).hexdigest()[:10]
        assert versioned == f"{stem}-{digest}.{extension}"
