import base64
from email.header import decode_header

import pytest
from notifications_utils.email_headers import (
    MAX_FROM_HEADER_LENGTH,
    build_from_header,
    encode_display_name,
    from_header_length,
    is_from_header_too_long,
    truncate_display_name_to_fit,
)

STAGING_DOMAIN = "staging.notification.cdssandbox.xyz"

# Example from issue #3494 "Service name too long creates Tech error when sending email"
ISSUE_NAME = (
    "Accès et mise à jour des renseignements relatifs à la paye des fonctionnaires fédéraux, "
    "mesures à prendre en cas de problèmes de paye, changements dans les situations de travail "
    "et votre paye, nouvelles"
)
ISSUE_EMAIL_FROM = "acces_et_mise_a_jour"


@pytest.mark.parametrize(
    "display_name, expected",
    [
        ("Sample service", '"Sample service"'),
        ('Say "hi"', '"Say \\"hi\\""'),
        ("back\\slash", '"back\\\\slash"'),
        ("Jöhn Döe", '"=?utf-8?B?SsO2aG4gRMO2ZQ==?="'),
        ("line\nbreak", '"=?utf-8?B?bGluZQpicmVhaw==?="'),
    ],
)
def test_encode_display_name(display_name, expected):
    assert encode_display_name(display_name) == expected


def test_encode_display_name_non_ascii_round_trips():
    encoded = encode_display_name(ISSUE_NAME).strip('"')
    assert encoded.startswith("=?utf-8?B?") and encoded.endswith("?=")
    assert base64.b64decode(encoded[len("=?utf-8?B?") : -2]).decode("utf-8") == ISSUE_NAME
    [(decoded, charset)] = decode_header(encoded)
    assert (decoded.decode(charset), charset) == (ISSUE_NAME, "utf-8")


@pytest.mark.parametrize(
    "display_name, expected",
    [
        ("Sample service", '"Sample service" <sample.service@notification.canada.ca>'),
        ("Jöhn Döe", '"=?utf-8?B?SsO2aG4gRMO2ZQ==?=" <sample.service@notification.canada.ca>'),
        ("", "sample.service@notification.canada.ca"),
    ],
)
def test_build_from_header(display_name, expected):
    assert build_from_header(display_name, "sample.service", "notification.canada.ca") == expected


def test_from_header_length_matches_built_header():
    header = build_from_header(ISSUE_NAME, ISSUE_EMAIL_FROM, STAGING_DOMAIN)
    assert from_header_length(ISSUE_NAME, ISSUE_EMAIL_FROM, STAGING_DOMAIN) == len(header)


def test_issue_example_is_too_long():
    # Base64 makes this 202 character name ~270 characters long once encoded
    assert from_header_length(ISSUE_NAME, ISSUE_EMAIL_FROM, STAGING_DOMAIN) == 353
    assert is_from_header_too_long(ISSUE_NAME, ISSUE_EMAIL_FROM, STAGING_DOMAIN)


def test_long_ascii_name_is_not_base64_encoded():
    name = "a" * 255
    assert from_header_length(name, "abc", STAGING_DOMAIN) == 255 + 2 + len(" <abc@>") + len(STAGING_DOMAIN)
    assert not is_from_header_too_long(name, "abc", STAGING_DOMAIN)


def test_is_from_header_too_long_boundary():
    email_from, domain = "abc", "example.com"
    overhead = from_header_length("x", email_from, domain) - 1
    fits = "x" * (MAX_FROM_HEADER_LENGTH - overhead)
    assert from_header_length(fits, email_from, domain) == MAX_FROM_HEADER_LENGTH
    assert not is_from_header_too_long(fits, email_from, domain)
    assert is_from_header_too_long(fits + "x", email_from, domain)


def test_truncate_display_name_to_fit_returns_name_unchanged_when_it_fits():
    assert truncate_display_name_to_fit("Sample service", "sample.service", STAGING_DOMAIN) == "Sample service"


def test_truncate_display_name_to_fit_returns_longest_fitting_prefix():
    truncated = truncate_display_name_to_fit(ISSUE_NAME, ISSUE_EMAIL_FROM, STAGING_DOMAIN)

    assert ISSUE_NAME.startswith(truncated)
    assert truncated == truncated.rstrip()
    assert not is_from_header_too_long(truncated, ISSUE_EMAIL_FROM, STAGING_DOMAIN)
    next_char_index = len(truncated)
    while ISSUE_NAME[next_char_index] == " ":
        next_char_index += 1
    assert is_from_header_too_long(ISSUE_NAME[: next_char_index + 1], ISSUE_EMAIL_FROM, STAGING_DOMAIN)


def test_truncate_display_name_to_fit_never_splits_multibyte_characters():
    truncated = truncate_display_name_to_fit("é" * 300, "abc", STAGING_DOMAIN)
    assert truncated and set(truncated) == {"é"}
    assert not is_from_header_too_long(truncated, "abc", STAGING_DOMAIN)


def test_truncate_display_name_to_fit_returns_empty_string_when_address_alone_is_too_long():
    assert truncate_display_name_to_fit("Sample service", "a" * MAX_FROM_HEADER_LENGTH, STAGING_DOMAIN) == ""
