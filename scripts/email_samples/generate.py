"""
Render sample GC Notify emails so they can be reviewed in different email clients.

For each sample in `samples.SAMPLES` this writes:

- `<name>.html`: the exact HTML body that notification-api sends
- `<name>.eml`: a multipart email (plain text + HTML), which can be opened in
  desktop clients such as Outlook or Apple Mail, or uploaded to screenshot tools
- `index.html`: a gallery showing every sample at desktop and mobile widths
- `lint-report.md` / `lint-report.json`: HTML and CSS features the samples use that
  some email clients don't support, based on https://www.caniemail.com data
  (requires Node.js, run via `npx doiuse-email`)

Usage, from the repository root:

    poetry run python -m scripts.email_samples.generate [--output-dir DIR] [--no-lint]
"""

import argparse
import html
import json
import re
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path

from notifications_utils.template import HTMLEmailTemplate, PlainTextEmailTemplate

from scripts.email_samples.samples import (
    BRANDINGS,
    CONTENTS,
    DEFAULT_BRAND_COLOUR,
    DEFAULT_LOGO_URL,
    PERSONALISATION,
    SAMPLES,
    Sample,
)

DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"
DOIUSE_EMAIL_VERSION = "0.4.1"
DEFAULT_EMAIL_CLIENTS = [
    "outlook.*",
    "gmail.*",
    "apple-mail.*",
    "yahoo.*",
    "samsung-email.*",
    "thunderbird.*",
]
# Fixed so that output is identical between runs, which makes it easy to diff two branches.
EML_DATE = "Thu, 01 Oct 2026 12:00:00 -0400"

NOT_SUPPORTED_RE = re.compile(r"^`(?P<feature>.+)` is not supported by `(?P<client>[^`]+)`")
PARTIALLY_SUPPORTED_RE = re.compile(r"^`(?P<feature>.+)` is only partially supported by `(?P<client>[^`]+)`")
NOTE_RE = re.compile(r"^Note about `(?P<feature>.+)` support for `(?P<client>[^`]+)`: (?P<note>.*)$")


@dataclass(frozen=True)
class RenderedSample:
    sample: Sample
    subject: str
    html: str
    text: str

    @property
    def name(self) -> str:
        return self.sample.name


@dataclass
class FeatureFindings:
    not_supported: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    partially_supported: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    notes: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


def render_sample(sample: Sample, logo_url: str = DEFAULT_LOGO_URL, brand_colour: str = DEFAULT_BRAND_COLOUR) -> RenderedSample:
    content = CONTENTS[sample.content]
    branding = BRANDINGS[sample.branding]
    template = {
        "content": content.body,
        "subject": content.subject,
        "template_type": "email",
        "text_direction_rtl": content.text_direction_rtl,
    }
    options = dict(branding.options)
    if branding.uses_logo:
        options["brand_logo"] = logo_url
    if branding.uses_colour:
        options["brand_colour"] = brand_colour

    plain_text = PlainTextEmailTemplate(template, PERSONALISATION)
    return RenderedSample(
        sample=sample,
        subject=str(plain_text.subject),
        html=str(HTMLEmailTemplate(template, PERSONALISATION, **options)),
        text=str(plain_text),
    )


def build_eml(rendered: RenderedSample) -> bytes:
    message = EmailMessage()
    message["Subject"] = rendered.subject
    message["From"] = "Example Department <example.department@notification.canada.ca>"
    message["To"] = "recipient@example.com"
    message["Date"] = EML_DATE
    message.set_content(rendered.text)
    message.add_alternative(rendered.html, subtype="html")
    message.set_boundary("gc-notify-email-sample")
    return message.as_bytes()


def write_samples(output_dir: Path, rendered_samples: list[RenderedSample]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for rendered in rendered_samples:
        (output_dir / f"{rendered.name}.html").write_text(rendered.html, encoding="utf-8")
        (output_dir / f"{rendered.name}.eml").write_bytes(build_eml(rendered))
    (output_dir / "index.html").write_text(build_index(rendered_samples), encoding="utf-8")


def build_index(rendered_samples: list[RenderedSample]) -> str:
    sections = []
    for rendered in rendered_samples:
        name = html.escape(rendered.name)
        sections.append(
            f"""
<section id="{name}">
  <h2>{name}</h2>
  <p>
    Content: <strong>{html.escape(rendered.sample.content)}</strong> ·
    Branding: <strong>{html.escape(BRANDINGS[rendered.sample.branding].description)}</strong> ·
    Subject: <em>{html.escape(rendered.subject)}</em>
  </p>
  <p><a href="{name}.html">Open HTML</a> · <a href="{name}.eml">Download .eml</a></p>
  <div class="frames">
    <figure><figcaption>Desktop (800px)</figcaption><iframe src="{name}.html" width="800" loading="lazy"></iframe></figure>
    <figure><figcaption>Mobile (375px)</figcaption><iframe src="{name}.html" width="375" loading="lazy"></iframe></figure>
  </div>
</section>"""
        )
    toc = "".join(f'<li><a href="#{html.escape(r.name)}">{html.escape(r.name)}</a></li>' for r in rendered_samples)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GC Notify email samples</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f3f3f3; }}
    section {{ background: #fff; padding: 1rem 1.5rem; margin-bottom: 2rem; border-radius: 6px; }}
    .frames {{ display: flex; gap: 2rem; align-items: flex-start; flex-wrap: wrap; }}
    figure {{ margin: 0; }}
    iframe {{ height: 900px; border: 1px solid #ccc; background: #fff; }}
  </style>
</head>
<body>
  <h1>GC Notify email samples</h1>
  <p>
    Browser rendering only. Email clients (especially Outlook for Windows and Gmail) render
    differently, so check the .eml files in real clients or a screenshot service.
    See <a href="lint-report.md">lint-report.md</a> for features with known client support gaps.
  </p>
  <ul>{toc}</ul>
  {"".join(sections)}
</body>
</html>
"""


def lint_html(path: Path, email_clients: list[str]) -> dict:
    # The package's bin script has no shebang, so it has to be run through node explicitly.
    command = 'node "$(command -v doiuse-email)" --email-clients {} {}'.format(
        shlex.quote(",".join(email_clients)),
        shlex.quote(str(path)),
    )
    result = subprocess.run(
        ["npx", "--yes", "-p", f"doiuse-email@{DOIUSE_EMAIL_VERSION}", "-c", command],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def collect_findings(lint_results: dict[str, dict]) -> dict[str, FeatureFindings]:
    findings: dict[str, FeatureFindings] = defaultdict(FeatureFindings)
    for sample_name, result in lint_results.items():
        for message in result.get("errors", []):
            if match := NOT_SUPPORTED_RE.match(message):
                findings[match["feature"]].not_supported[match["client"]].add(sample_name)
        for message in result.get("warnings", []):
            if match := PARTIALLY_SUPPORTED_RE.match(message):
                findings[match["feature"]].partially_supported[match["client"]].add(sample_name)
        for message in result.get("notes", []):
            if match := NOTE_RE.match(message):
                findings[match["feature"]].notes[match["note"]].add(match["client"])
    return findings


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _samples_cell(samples: set[str], all_samples: set[str]) -> str:
    if samples == all_samples:
        return "all"
    missing = all_samples - samples
    if len(missing) < len(samples):
        return "all except " + ", ".join(sorted(missing))
    return ", ".join(sorted(samples))


def build_lint_report(findings: dict[str, FeatureFindings], all_samples: set[str], email_clients: list[str]) -> str:
    lines = [
        "# Email client compatibility report",
        "",
        f"Static analysis by [doiuse-email](https://github.com/leondreamed/doiuse-email) {DOIUSE_EMAIL_VERSION}, "
        "using its bundled [caniemail.com](https://www.caniemail.com) data (which may lag the live site).",
        f"Clients checked: `{', '.join(email_clients)}`.",
        "",
        "This only lists features that a client is *known* not to support. It can't tell whether the "
        "email still looks acceptable, and it misses features caniemail has no data for. "
        "Confirm findings in real clients.",
        "",
    ]
    for title, attribute in (("Not supported", "not_supported"), ("Partially supported", "partially_supported")):
        rows = [(feature, getattr(f, attribute)) for feature, f in findings.items() if getattr(f, attribute)]
        rows.sort(key=lambda row: (-len(row[1]), row[0].lower()))
        lines += [f"## {title}", ""]
        if not rows:
            lines += ["None.", ""]
            continue
        lines += ["| Feature | Clients | Samples |", "| --- | --- | --- |"]
        for feature, clients in rows:
            samples = set().union(*clients.values())
            lines.append(
                f"| `{_cell(feature)}` | {_cell(', '.join(sorted(clients)))} | {_cell(_samples_cell(samples, all_samples))} |"
            )
        lines.append("")

    noted = sorted((feature, f.notes) for feature, f in findings.items() if f.notes)
    if noted:
        lines += ["## Notes from caniemail", ""]
        for feature, notes in noted:
            lines.append(f"### `{feature}`")
            lines.append("")
            for note, clients in sorted(notes.items()):
                lines.append(f"- {', '.join(sorted(clients))}: {note}")
            lines.append("")
    return "\n".join(lines)


def run_lint(output_dir: Path, rendered_samples: list[RenderedSample], email_clients: list[str]) -> dict[str, FeatureFindings]:
    lint_results = {}
    for rendered in rendered_samples:
        lint_results[rendered.name] = lint_html(output_dir / f"{rendered.name}.html", email_clients)
    findings = collect_findings(lint_results)
    all_samples = {rendered.name for rendered in rendered_samples}
    (output_dir / "lint-report.json").write_text(json.dumps(lint_results, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "lint-report.md").write_text(build_lint_report(findings, all_samples, email_clients), encoding="utf-8")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=f"default: {DEFAULT_OUTPUT_DIR}")
    parser.add_argument("--logo-url", default=DEFAULT_LOGO_URL, help="logo used by custom branding samples")
    parser.add_argument("--brand-colour", default=DEFAULT_BRAND_COLOUR, help="colour used by custom branding samples")
    parser.add_argument(
        "--email-clients",
        default=",".join(DEFAULT_EMAIL_CLIENTS),
        help="comma separated caniemail client globs to lint against (default: %(default)s)",
    )
    parser.add_argument("--no-lint", action="store_true", help="skip the caniemail compatibility check")
    args = parser.parse_args(argv)

    rendered_samples = [render_sample(sample, args.logo_url, args.brand_colour) for sample in SAMPLES]
    write_samples(args.output_dir, rendered_samples)
    print(f"Wrote {len(rendered_samples)} samples to {args.output_dir}")
    print(f"Gallery: {args.output_dir / 'index.html'}")

    if args.no_lint:
        return 0
    if shutil.which("npx") is None:
        print("npx not found, skipping compatibility check (install Node.js or pass --no-lint)", file=sys.stderr)
        return 1

    email_clients = [client.strip() for client in args.email_clients.split(",") if client.strip()]
    findings = run_lint(args.output_dir, rendered_samples, email_clients)
    not_supported = sorted(feature for feature, f in findings.items() if f.not_supported)
    print(f"Compatibility report: {args.output_dir / 'lint-report.md'}")
    print(f"Features not supported by at least one client: {', '.join(not_supported) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
