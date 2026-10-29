from email import message_from_bytes, policy
from email.message import EmailMessage

import pytest
from scripts.email_samples.generate import (
    build_eml,
    build_lint_report,
    collect_findings,
    main,
    render_sample,
)
from scripts.email_samples.samples import BRANDINGS, CONTENTS, SAMPLES, Sample


def test_samples_cover_every_content_and_branding():
    assert {sample.content for sample in SAMPLES} == set(CONTENTS)
    assert {sample.branding for sample in SAMPLES} == set(BRANDINGS)
    assert len({sample.name for sample in SAMPLES}) == len(SAMPLES)


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda sample: sample.name)
def test_render_sample_fills_in_personalisation(sample):
    rendered = render_sample(sample)

    assert rendered.html.startswith("\n<!DOCTYPE html")
    assert "((" not in rendered.html
    assert "((" not in rendered.text
    assert "((" not in rendered.subject


@pytest.mark.parametrize(
    "branding, expected, unexpected",
    [
        ("fip_en", ["gc-logo-en.png", "canada-logo.png"], ["gc-logo-fr.png", "https://logo.test/logo.png"]),
        ("fip_fr", ["gc-logo-fr.png", "canada-logo.png"], ["gc-logo-en.png"]),
        ("both_english", ["gc-logo-en.png", "https://logo.test/logo.png"], ["#123456"]),
        ("both_french", ["gc-logo-fr.png", "https://logo.test/logo.png"], ["#123456"]),
        ("custom_logo", ["https://logo.test/logo.png"], ["gc-logo-en.png", "canada-logo.png"]),
        ("custom_logo_with_text", ["https://logo.test/logo.png", "border-left: solid 2px #123456"], ["gc-logo-en.png"]),
        ("custom_logo_with_background_colour", ["https://logo.test/logo.png", 'bgcolor="#123456"'], ["gc-logo-en.png"]),
        ("no_branding", [], ["gc-logo-en.png", "gc-logo-fr.png", "canada-logo.png", "<img"]),
    ],
)
def test_render_sample_applies_branding(branding, expected, unexpected):
    rendered = render_sample(Sample("plain", branding), logo_url="https://logo.test/logo.png", brand_colour="#123456")

    for value in expected:
        assert value in rendered.html
    for value in unexpected:
        assert value not in rendered.html


def test_render_sample_sets_template_direction():
    rendered = render_sample(Sample("rtl_template", "fip_en"))

    assert 'dir="rtl"' in rendered.html


def test_build_eml_is_multipart_alternative():
    rendered = render_sample(Sample("bilingual", "fip_en"))

    message = message_from_bytes(build_eml(rendered), policy=policy.default)

    assert isinstance(message, EmailMessage)
    assert message.get_content_type() == "multipart/alternative"
    assert message["Subject"] == rendered.subject
    plain_part = message.get_body(("plain",))
    html_part = message.get_body(("html",))
    assert isinstance(plain_part, EmailMessage)
    assert isinstance(html_part, EmailMessage)
    assert plain_part.get_content() == rendered.text
    assert html_part.get_content() == rendered.html


def test_build_eml_is_deterministic():
    rendered = render_sample(Sample("plain", "fip_en"))

    assert build_eml(rendered) == build_eml(rendered)


def test_main_writes_samples_and_gallery_without_lint(tmp_path):
    assert main(["--output-dir", str(tmp_path), "--no-lint"]) == 0

    for sample in SAMPLES:
        assert (tmp_path / f"{sample.name}.html").exists()
        assert (tmp_path / f"{sample.name}.eml").exists()
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    for sample in SAMPLES:
        assert f'src="{sample.name}.html"' in index
    assert not (tmp_path / "lint-report.md").exists()


def test_collect_findings_and_build_lint_report():
    lint_results = {
        "a": {
            "errors": [
                "`@media` is not supported by `outlook.windows`",
                "`<body> element` is not supported by `outlook.ios`",
            ],
            "warnings": ["`max-width` is only partially supported by `outlook.windows`"],
            "notes": ["Note about `max-width` support for `outlook.windows`: Partial. Not supported on tables."],
        },
        "b": {
            "errors": ["`@media` is not supported by `outlook.windows`"],
            "warnings": [],
            "notes": [],
        },
    }

    findings = collect_findings(lint_results)

    assert findings["@media"].not_supported == {"outlook.windows": {"a", "b"}}
    assert findings["<body> element"].not_supported == {"outlook.ios": {"a"}}
    assert findings["max-width"].partially_supported == {"outlook.windows": {"a"}}
    assert findings["max-width"].notes == {"Partial. Not supported on tables.": {"outlook.windows"}}

    report = build_lint_report(findings, {"a", "b"}, ["outlook.*"])

    assert "| `@media` | outlook.windows | all |" in report
    assert "| `<body> element` | outlook.ios | a |" in report
    assert "| `max-width` | outlook.windows | a |" in report
    assert "- outlook.windows: Partial. Not supported on tables." in report
