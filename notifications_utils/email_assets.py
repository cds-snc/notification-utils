"""Static images used by the default GC Notify email templates (FIP signature, wordmark, etc.).

The source files live in ``notifications_utils/static/email``. notification-terraform uploads them
to each environment's asset bucket (served from ``assets.<domain>``) under content-addressed names,
e.g. ``email-assets/gc-logo-en-1a2b3c4d5e.png`` (see ``aws/common/uploadS3Assets.tf``). Terraform
computes the same names, so the naming scheme here must stay in sync with it.

Because the name includes a hash of the file contents, changing an image automatically changes
its URL: no manual cache busting is needed, already-sent emails keep pointing at the image they
were sent with, and an environment only starts using a new image once it runs a version of this
package that references it.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

EMAIL_ASSETS_DIR = Path(__file__).resolve().parent / "static" / "email"
EMAIL_ASSETS_PREFIX = "email-assets"
DEFAULT_ASSET_DOMAIN = "assets.notification.canada.ca"
HASH_LENGTH = 10
# Terraform only uploads these extensions.
SUPPORTED_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg"}


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
