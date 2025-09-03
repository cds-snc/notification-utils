import re
import string
import urllib
from itertools import count
from typing import List

import bleach
import mistune
import smartypants
from flask import Markup

from notifications_utils.sanitise_text import SanitiseSMS

from . import email_with_smart_quotes_regex

LINK_STYLE = "word-wrap: break-word;"

OBSCURE_WHITESPACE = (
    "\u180e"  # Mongolian vowel separator
    "\u200b"  # zero width space
    "\u200c"  # zero width non-joiner
    "\u200d"  # zero width joiner
    "\u2060"  # word joiner
    "\ufeff"  # zero width non-breaking space
)

EMAIL_P_OPEN_TAG = '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
EMAIL_P_CLOSE_TAG = "</p>"

FR_OPEN = r"\[\[fr\]\]"  # matches [[fr]]
FR_CLOSE = r"\[\[/fr\]\]"  # matches [[/fr]]
EN_OPEN = r"\[\[en\]\]"  # matches [[en]]
EN_CLOSE = r"\[\[/en\]\]"  # matches [[/en]]
RTL_OPEN = r"\[\[rtl\]\]"  # matches [[rtl]]
RTL_CLOSE = r"\[\[/rtl\]\]"  # matches [[/rtl]]
FR_OPEN_LITERAL = "[[fr]]"
FR_CLOSE_LITERAL = "[[/fr]]"
EN_OPEN_LITERAL = "[[en]]"
EN_CLOSE_LITERAL = "[[/en]]"
RTL_OPEN_LITERAL = "[[rtl]]"
RTL_CLOSE_LITERAL = "[[/rtl]]"
BR_TAG = r"<br\s?/>"


mistune._block_quote_leading_pattern = re.compile(r"^ *\^ ?", flags=re.M)
mistune.BlockGrammar.block_quote = re.compile(r"^( *\^[^\n]+(\n[^\n]+)*\n*)+")
mistune.BlockGrammar.list_block = re.compile(
    r"^( *)([•*-]|\d+\.) ([^*]|[*]{2})[\s\S]+?"
    r"(?:"
    r"\n+(?=\1?(?:[-*_] *){3,}(?:\n+|$))"  # hrule
    r"|\n+(?=%s)"  # def links
    r"|\n+(?=%s)"  # def footnotes
    r"|\n{2,}"
    r"(?! )"
    r"(?!\1(?:[•*-]|\d+\.) )\n*"
    r"|"
    r"\s*$)"
    % (
        mistune._pure_pattern(mistune.BlockGrammar.def_links),
        mistune._pure_pattern(mistune.BlockGrammar.def_footnotes),
    )
)
mistune.BlockGrammar.list_item = re.compile(r"^(( *)(?:[•*-]|\d+\.) [^\n]*" r"(?:\n(?!\2(?:[•*-]|\d+\.))[^\n]*)*)", flags=re.M)
mistune.BlockGrammar.list_bullet = re.compile(r"^ *(?:[•*-]|\d+\.)")
mistune.InlineGrammar.url = re.compile(r"""^(https?:\/\/[^\s<]+[^<.,:"')\]\s])""")

govuk_not_a_link = re.compile(r"(?<!\.|\/)(GOV)\.(UK)(?!\/|\?)", re.IGNORECASE)

dvla_markup_tags = re.compile(
    str("|".join("<{}>".format(tag) for tag in {"cr", "h1", "h2", "p", "normal", "op", "np", "bul", "tab"})),
    re.IGNORECASE,
)

smartypants.tags_to_skip = smartypants.tags_to_skip + ["a"]

whitespace_before_punctuation = re.compile(r"[ \t]+([,\.])")

hyphens_surrounded_by_spaces = re.compile(r"\s+[-–—]{1,3}\s+")

multiple_newlines = re.compile(r"((\n)\2{2,})")

MAGIC_SEQUENCE = "🇬🇧🐦✉️"

magic_sequence_regex = re.compile(MAGIC_SEQUENCE)

# The Mistune URL regex only matches URLs at the start of a string,
# using `^`, so we slice that off and recompile
url = re.compile(mistune.InlineGrammar.url.pattern[1:])


def unlink_govuk_escaped(message):
    return re.sub(govuk_not_a_link, r"\1" + ".\u200b" + r"\2", message)  # Unicode zero-width space


def nl2br(value):
    return re.sub(r"\n|\r", "<br>", value.strip())


def nl2li(value):
    return "<ul><li>{}</li></ul>".format("</li><li>".join(value.strip().split("\n")))


def add_prefix(body, prefix=None):
    if prefix:
        return "{}: {}".format(prefix.strip(), body)
    return body


def autolink_sms(body):
    return url.sub(
        lambda match: '<a style="{}" href="{}">{}</a>'.format(
            LINK_STYLE,
            match.group(1),
            match.group(1),
        ),
        body,
    )


def prepend_subject(body, subject):
    return "# {}\n\n{}".format(subject, body)


def remove_empty_lines(lines):
    return "\n".join(filter(None, str(lines).split("\n")))


def sms_encode(content):
    return SanitiseSMS.encode(content)


def strip_html(value):
    return bleach.clean(value, tags=[], strip=True)


def escape_html(value):
    if not value:
        return value
    value = str(value).replace("<", "&lt;")
    return bleach.clean(value, tags=[], strip=False)


def strip_dvla_markup(value):
    return re.sub(dvla_markup_tags, "", value)


def url_encode_full_stops(value):
    return value.replace(".", "%2E")


def unescaped_formatted_list(
    items,
    conjunction="and",
    before_each="‘",
    after_each="’",
    separator=", ",
    prefix="",
    prefix_plural="",
):
    if prefix:
        prefix += " "
    if prefix_plural:
        prefix_plural += " "

    if len(items) == 1:
        return "{prefix}{before_each}{items[0]}{after_each}".format(**locals())
    elif items:
        formatted_items = ["{}{}{}".format(before_each, item, after_each) for item in items]

        first_items = separator.join(formatted_items[:-1])
        last_item = formatted_items[-1]
        return ("{prefix_plural}{first_items} {conjunction} {last_item}").format(**locals())


def formatted_list(
    items,
    conjunction="and",
    before_each="‘",
    after_each="’",
    separator=", ",
    prefix="",
    prefix_plural="",
):
    return Markup(
        unescaped_formatted_list(
            [escape_html(x) for x in items],
            conjunction,
            before_each,
            after_each,
            separator,
            prefix,
            prefix_plural,
        )
    )


def fix_extra_newlines_in_dvla_lists(dvla_markup):
    return dvla_markup.replace(
        "<cr><cr><cr><op>",
        "<cr><op>",
    )


def strip_pipes(value):
    return value.replace("|", "")


def remove_whitespace_before_punctuation(value):
    return re.sub(whitespace_before_punctuation, lambda match: match.group(1), value)


def make_quotes_smart(value):
    return smartypants.smartypants(value, smartypants.Attr.q | smartypants.Attr.u)


def replace_hyphens_with_en_dashes(value):
    return re.sub(
        hyphens_surrounded_by_spaces,
        (" " "\u2013" " "),  # space  # en dash  # space
        value,
    )


def replace_hyphens_with_non_breaking_hyphens(value):
    return value.replace(
        "-",
        "\u2011",  # non-breaking hyphen
    )


def normalise_newlines(value):
    return "\n".join(value.splitlines())


def strip_leading_whitespace(value):
    return value.lstrip()


def add_trailing_newline(value):
    return "{}\n".format(value)


def is_valid_index(index: int, lines: List[str]):
    return index >= 0 and index < len(lines)


def insert_newline_after(lines: List[str], tag_index: int):
    # no need to insert newlines at the end of the file
    if tag_index == len(lines) - 1:
        return
    if not is_valid_index(tag_index + 1, lines):
        return
    if lines[tag_index + 1] == "":
        return

    lines.insert(tag_index + 1, "")  # insert 1 newline


def insert_newline_before(lines: List[str], tag_index: int):
    # no need to insert newlines at the beginning of the file
    if tag_index == 0:
        return
    if not is_valid_index(tag_index - 1, lines):
        return
    if lines[tag_index - 1] == "":
        return

    lines.insert(tag_index, "")  # insert 1 newline


def add_newlines_around_lang_tags(content: str) -> str:
    lines = content.splitlines()
    all_tags = ["[[fr]]", "[[/fr]]", "[[en]]", "[[/en]]"]
    for tag in all_tags:
        # strip whitespace
        for index, line in enumerate(lines):
            if tag in line and line.strip() == tag:
                lines[index] = line.strip()

        if tag not in lines:
            continue

        tag_index = lines.index(tag)

        insert_newline_before(lines, tag_index)
        new_tag_index = lines.index(tag)
        insert_newline_after(lines, new_tag_index)
    new_content = "\n".join(lines)
    return new_content


def tweak_dvla_list_markup(value):
    return value.replace("<cr><cr><np>", "<cr><np>").replace("<p><cr><p><cr>", "<p><cr>")


def remove_smart_quotes_from_email_addresses(value):
    def remove_smart_quotes(match):
        value = match.group(0)
        for character in "‘’":
            value = value.replace(character, "'")
        return value

    return email_with_smart_quotes_regex.sub(
        remove_smart_quotes,
        value,
    )


def strip_whitespace(value, extra_characters=""):
    if value is not None and hasattr(value, "strip"):
        return value.strip(string.whitespace + OBSCURE_WHITESPACE + extra_characters)
    return value


def strip_and_remove_obscure_whitespace(value):
    for character in OBSCURE_WHITESPACE:
        value = value.replace(character, "")

    return value.strip(string.whitespace)


def strip_unsupported_characters(value):
    return value.replace("\u2028", "")


def normalise_whitespace(value):
    # leading and trailing whitespace removed, all inner whitespace becomes a single space
    return " ".join(strip_and_remove_obscure_whitespace(value).split())


class NotifyLetterMarkdownPreviewRenderer(mistune.Renderer):
    def block_code(self, code, language=None):
        return code

    def block_quote(self, text):
        return text

    def header(self, text, level, raw=None):
        if level == 1:
            return super().header(text, 2)
        return self.paragraph(text)

    def hrule(self):
        return '<div class="page-break">&nbsp;</div>'

    def paragraph(self, text):
        if text.strip():
            return "<p>{}</p>".format(text)
        return ""

    def table(self, header, body):
        return ""

    def autolink(self, link, is_email=False):
        return "<strong>{}</strong>".format(link.replace("http://", "").replace("https://", ""))

    def codespan(self, text):
        return text

    def double_emphasis(self, text):
        return text

    def emphasis(self, text):
        return text

    def image(self, src, title, alt_text):
        return ""

    def linebreak(self):
        return "<br>"

    def newline(self):
        return self.linebreak()

    def list_item(self, text):
        return "<li>{}</li>\n".format(text.strip())

    def link(self, link, title, content):
        return "{}: {}".format(content, self.autolink(link))

    def strikethrough(self, text):
        return text

    def footnote_ref(self, key, index):
        return ""

    def footnote_item(self, key, text):
        return text

    def footnotes(self, text):
        return text


class NotifyEmailMarkdownRenderer(NotifyLetterMarkdownPreviewRenderer):
    def header(self, text, level, raw=None):
        if level == 1:
            return (
                '<h2 style="Margin: 0 0 20px 0; padding: 0; '
                'font-size: 27px; line-height: 35px; font-weight: bold; color: #0B0C0C;">'
                f"{text}"
                "</h2>"
            )
        elif level == 2:
            return (
                '<h3 style="Margin: 0 0 15px 0; padding: 0; line-height: 26px; color: #0B0C0C;'
                'font-size: 24px; font-weight: bold;">'
                f"{text}"
                "</h3>"
            )
        return self.paragraph(text)

    def hrule(self):
        return '<hr style="border: 0; height: 1px; background: #BFC1C3; Margin: 30px 0 30px 0;">'

    def linebreak(self):
        return "<br />"

    def list(self, body, ordered=True):
        return (
            (
                '<table role="presentation" style="padding: 0 0 20px 0;">'
                "<tr>"
                '<td style="font-family: Helvetica, Arial, sans-serif;">'
                '<ol style="margin: 0; padding: 0; list-style-type: decimal; margin-inline-start: 20px;">'
                "{}"
                "</ol>"
                "</td>"
                "</tr>"
                "</table>"
            ).format(body)
            if ordered
            else (
                '<table role="presentation" style="padding: 0 0 20px 0;">'
                "<tr>"
                '<td style="font-family: Helvetica, Arial, sans-serif;">'
                '<ul style="margin: 0; padding: 0; list-style-type: disc; margin-inline-start: 20px;">'
                "{}"
                "</ul>"
                "</td>"
                "</tr>"
                "</table>"
            ).format(body)
        )

    def list_item(self, text):
        return (
            '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 19px; '
            'line-height: 25px; color: #0B0C0C; text-align:start;">'
            "{}"
            "</li>"
        ).format(text.strip())

    def paragraph(self, text):
        if text.strip():
            return f"{EMAIL_P_OPEN_TAG}{text}{EMAIL_P_CLOSE_TAG}"
        return ""

    def block_quote(self, text):
        return (
            "<blockquote "
            'style="Margin: 0 0 20px 0; border-left: 10px solid #BFC1C3;'
            'padding: 15px 0 0.1px 15px; font-size: 19px; line-height: 25px;"'
            ">"
            "{}"
            "</blockquote>"
        ).format(text)

    def link(self, link, title, content):
        return ('<a style="{}"{}{}>{}</a>').format(
            LINK_STYLE,
            ' href="{}"'.format(link),
            ' title="{}"'.format(title) if title else "",
            content,
        )

    def autolink(self, link, is_email=False):
        if is_email:
            return link
        return '<a style="{}" href="{}">{}</a>'.format(
            LINK_STYLE,
            urllib.parse.quote(urllib.parse.unquote(link), safe=":/?#=&;"),
            link,
        )

    def double_emphasis(self, text):
        return f"<strong>{text}</strong>"

    def emphasis(self, text):
        return f"<em>{text}</em>"


class NotifyPlainTextEmailMarkdownRenderer(NotifyEmailMarkdownRenderer):
    COLUMN_WIDTH = 65

    def header(self, text, level, raw=None):
        if level == 1:
            return "".join(
                (
                    self.linebreak() * 3,
                    text,
                    self.linebreak(),
                    "-" * self.COLUMN_WIDTH,
                )
            )
        elif level == 2:
            return "".join((self.linebreak() * 2, text, self.linebreak(), "-" * self.COLUMN_WIDTH))
        return self.paragraph(text)

    def hrule(self):
        return self.paragraph("=" * self.COLUMN_WIDTH)

    def linebreak(self):
        return "\n"

    def list(self, body, ordered=True):
        def _get_list_marker():
            decimal = count(1)
            return lambda _: "{}.".format(next(decimal)) if ordered else "•"

        return "".join(
            (
                self.linebreak(),
                re.sub(
                    magic_sequence_regex,
                    _get_list_marker(),
                    body,
                ),
            )
        )

    def list_item(self, text):
        return "".join(
            (
                self.linebreak(),
                MAGIC_SEQUENCE,
                " ",
                text.strip(),
            )
        )

    def paragraph(self, text):
        if text.strip():
            return "".join(
                (
                    self.linebreak() * 2,
                    text,
                )
            )
        return ""

    def block_quote(self, text):
        return text

    def link(self, link, title, content):
        return "".join(
            (
                content,
                " ({})".format(title) if title else "",
                ": ",
                link,
            )
        )

    def autolink(self, link, is_email=False):
        return link

    def double_emphasis(self, text):
        return f"**{text}**"

    def emphasis(self, text):
        return f"_{text}_"


class NotifyEmailPreheaderMarkdownRenderer(NotifyPlainTextEmailMarkdownRenderer):
    def header(self, text, level, raw=None):
        return self.paragraph(text)

    def hrule(self):
        return ""

    def link(self, link, title, content):
        return "".join(
            (
                content,
                " ({})".format(title) if title else "",
            )
        )


notify_email_markdown = mistune.Markdown(
    renderer=NotifyEmailMarkdownRenderer(),
    hard_wrap=True,
    use_xhtml=False,
)
notify_plain_text_email_markdown = mistune.Markdown(
    renderer=NotifyPlainTextEmailMarkdownRenderer(),
    hard_wrap=True,
)
notify_email_preheader_markdown = mistune.Markdown(
    renderer=NotifyEmailPreheaderMarkdownRenderer(),
    hard_wrap=True,
)
notify_letter_preview_markdown = mistune.Markdown(
    renderer=NotifyLetterMarkdownPreviewRenderer(),
    hard_wrap=True,
    use_xhtml=False,
)


def escape_lang_tags(_content: str) -> str:
    """
    Escape language tags into code tags in the content so mistune doesn't put them inside p tags.  This makes it simple
    to replace them afterwards, and avoids creating invalid HTML in the process
    """

    # check to ensure we have the same number of opening and closing tags before escaping tags
    if (_content.count(EN_OPEN_LITERAL) == _content.count(EN_CLOSE_LITERAL)) and (
        _content.count(FR_OPEN_LITERAL) == _content.count(FR_CLOSE_LITERAL)
    ):
        _content = _content.replace(FR_OPEN_LITERAL, f"\n```\n{FR_OPEN_LITERAL}\n```\n")
        _content = _content.replace(FR_CLOSE_LITERAL, f"\n```\n{FR_CLOSE_LITERAL}\n```\n")
        _content = _content.replace(EN_OPEN_LITERAL, f"```\n{EN_OPEN_LITERAL}\n```\n")
        _content = _content.replace(EN_CLOSE_LITERAL, f"\n```\n{EN_CLOSE_LITERAL}\n```\n")

    return _content


def escape_rtl_tags(_content: str) -> str:
    """
    Escape RTL tags into code tags in the content so mistune doesn't put them inside p tags.  This makes it simple
    to replace them afterwards, and avoids creating invalid HTML in the process
    """

    # check to ensure we have the same number of opening and closing tags before escaping tags
    if _content.count(RTL_OPEN_LITERAL) == _content.count(RTL_CLOSE_LITERAL):
        _content = _content.replace(RTL_OPEN_LITERAL, f"\n```\n{RTL_OPEN_LITERAL}\n```\n")
        _content = _content.replace(RTL_CLOSE_LITERAL, f"\n```\n{RTL_CLOSE_LITERAL}\n```\n")

    return _content


def add_language_divs(_content: str) -> str:
    """
    Custom parser to add the language divs.

    String replace language tags in-place
    """

    # check to ensure we have the same number of opening and closing tags before escaping tags
    if (_content.count(EN_OPEN_LITERAL) == _content.count(EN_CLOSE_LITERAL)) and (
        _content.count(FR_OPEN_LITERAL) == _content.count(FR_CLOSE_LITERAL)
    ):
        _content = _content.replace(FR_OPEN_LITERAL, '<div lang="fr-ca">')
        _content = _content.replace(FR_CLOSE_LITERAL, "</div>")
        _content = _content.replace(EN_OPEN_LITERAL, '<div lang="en-ca">')
        _content = _content.replace(EN_CLOSE_LITERAL, "</div>")

    return _content


def remove_language_divs(_content: str) -> str:
    """Remove the tags from content. This fn is for use in the email
    preheader, since this is plain text not html"""
    return remove_tags(_content, FR_OPEN, FR_CLOSE, EN_OPEN, EN_CLOSE)


def add_rtl_divs(_content: str) -> str:
    """
    Custom parser to add the language divs.

    String replace language tags in-place
    """

    # check to ensure we have the same number of opening and closing tags before escaping tags
    if _content.count(RTL_OPEN_LITERAL) == _content.count(RTL_CLOSE_LITERAL):
        _content = _content.replace(RTL_OPEN_LITERAL, '<div dir="rtl">')
        _content = _content.replace(RTL_CLOSE_LITERAL, "</div>")

    return _content


def remove_rtl_divs(_content: str) -> str:
    """Remove the tags from content. This fn is for use in the email
    preheader, since this is plain text not html"""
    return remove_tags(_content, RTL_OPEN, RTL_CLOSE)


def remove_tags(_content: str, *tags) -> str:
    """Remove the tags in parameters from content.

    This function is for use in the email preheader, since this is plain text
    not html."""
    content = _content
    for tag in tags:
        content = re.compile(tag).sub("", content)
    return content


def remove_nested_list_padding(_content: str) -> str:
    """Remove bottom padding from nested lists.
    Lists that are nested inside <li> elements should not have the 20px bottom
    padding. This function finds table elements that contain lists and are
    nested inside list items, and removes their padding.
    """
    if not _content:
        return _content

    # Use regex for the replacement to preserve all formatting including quotes
    import re

    # Find all table tags with the specific attributes we want to modify
    pattern = r'<table\s+role\s*=\s*["\']presentation["\']\s+style\s*=\s*["\']padding:\s*0\s+0\s+20px\s+0\s*;["\'][^>]*>'

    def replace_if_nested(match):
        # Check if this table is inside an <li> by parsing content up to this point
        content_before = _content[: match.start()]
        li_depth = content_before.count("<li") - content_before.count("</li>")

        if li_depth > 0:
            # Replace the padding value while preserving quotes and spacing
            return re.sub(r"padding:\s*0\s+0\s+20px\s+0\s*;", "padding: 0;", match.group(0))
        return match.group(0)

    return re.sub(pattern, replace_if_nested, _content, flags=re.IGNORECASE)
