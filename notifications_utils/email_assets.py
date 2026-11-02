"""Static images used by the default GC Notify email templates (FIP signature, wordmark, etc.).

The source files live in ``notifications_utils/static/email``. They are published to each
environment's asset bucket (served from ``assets.<domain>``) under content-addressed names, e.g.
``email-assets/gc-logo-en-1a2b3c4d5e.png``, by the ``Publish email assets`` GitHub workflow.

Because the name includes a hash of the file contents, changing an image automatically changes
its URL: no manual cache busting is needed, already-sent emails keep pointing at the image they
were sent with, and an environment only starts using a new image once it runs a version of this
package that references it.

This module only uses the standard library so it can be run as a script from CI without
installing the package dependencies:

    python notifications_utils/email_assets.py <output_dir>
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from functools import lru_cache
from pathlib import Path

EMAIL_ASSETS_DIR = Path(__file__).resolve().parent / "static" / "email"
EMAIL_ASSETS_PREFIX = "email-assets"
DEFAULT_ASSET_DOMAIN = "assets.notification.canada.ca"
HASH_LENGTH = 10


@lru_cache(maxsize=1)
def versioned_filenames() -> dict[str, str]:
    """Map each source filename to its content-addressed name, e.g. ``gc-logo-en.png`` -> ``gc-logo-en-1a2b3c4d5e.png``."""
    filenames = {}
    for path in sorted(EMAIL_ASSETS_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:HASH_LENGTH]
        filenames[path.name] = f"{path.stem}-{digest}{path.suffix}"
    return filenames


def email_asset_urls(asset_domain: str | None = None) -> dict[str, str]:
    """Map each source filename to its public URL on ``asset_domain``."""
    domain = asset_domain or DEFAULT_ASSET_DOMAIN
    return {name: f"https://{domain}/{EMAIL_ASSETS_PREFIX}/{versioned}" for name, versioned in versioned_filenames().items()}


def build(output_dir: Path) -> list[Path]:
    """Copy the assets into ``output_dir`` using their content-addressed names, ready to sync to S3."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, versioned in versioned_filenames().items():
        destination = output_dir / versioned
        shutil.copyfile(EMAIL_ASSETS_DIR / name, destination)
        written.append(destination)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build content-addressed email assets for upload to S3.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    for path in build(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
