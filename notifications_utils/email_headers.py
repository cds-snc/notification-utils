"""
Helpers for building the email ``From`` header (aka SES ``Source``).

The API uses these to build the header sent to AWS SES and the Admin uses them to
validate that a service name and email address can actually be used to send email,
so both sides agree on the length of the header.
"""

import base64

# AWS SES rejects a Source / From address longer than this.
MAX_FROM_HEADER_LENGTH = 320


def _is_printable_ascii(value: str) -> bool:
    return all(" " <= char <= "~" for char in value)


def encode_display_name(display_name: str) -> str:
    """
    Returns the display name ("friendly from") as it should appear in the From header.

    Printable ASCII names are sent as an RFC 5322 quoted-string. Anything else (accents,
    control characters, etc.) is encoded using MIME encoded-word syntax, as required by SES:
    https://docs.aws.amazon.com/ses/latest/dg/send-email-raw.html#send-email-mime-encoding-headers
    """
    if _is_printable_ascii(display_name):
        escaped = display_name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    encoded = base64.b64encode(display_name.encode("utf-8")).decode("ascii")
    return f'"=?utf-8?B?{encoded}?="'


def build_from_header(display_name: str, email_from: str, sending_domain: str) -> str:
    """
    Returns the full From header, e.g. ``"My service" <my.service@notification.canada.ca>``.

    email_from and sending_domain are expected to be ASCII.
    """
    address = f"{email_from}@{sending_domain}"
    if not display_name:
        return address
    return f"{encode_display_name(display_name)} <{address}>"


def from_header_length(display_name: str, email_from: str, sending_domain: str) -> int:
    return len(build_from_header(display_name, email_from, sending_domain))


def is_from_header_too_long(display_name: str, email_from: str, sending_domain: str) -> bool:
    return from_header_length(display_name, email_from, sending_domain) > MAX_FROM_HEADER_LENGTH


def truncate_display_name_to_fit(display_name: str, email_from: str, sending_domain: str) -> str:
    """
    Returns the longest prefix of display_name for which the From header fits within
    MAX_FROM_HEADER_LENGTH. Returns an empty string if even the bare address is too long.
    """
    for end in range(len(display_name), 0, -1):
        candidate = display_name[:end].rstrip()
        if candidate and not is_from_header_too_long(candidate, email_from, sending_domain):
            return candidate
    return ""
