import string
import re
from typing import List
import urllib

import mistune
import bleach
from itertools import count
from flask import Markup
from . import email_with_smart_quotes_regex
from notifications_utils.sanitise_text import SanitiseSMS
import smartypants


LINK_STYLE = "word-wrap: break-word;"

OBSCURE_WHITESPACE = (
    "\u180E"  # Mongolian vowel separator
    "\u200B"  # zero width space
    "\u200C"  # zero width non-joiner
    "\u200D"  # zero width joiner
    "\u2060"  # word joiner
    "\uFEFF"  # zero width non-breaking space
)

EMAIL_P_OPEN_TAG = '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
EMAIL_P_CLOSE_TAG = "</p>"

FR_OPEN = r"\[\[fr\]\]"  # matches [[fr]]
FR_CLOSE = r"\[\[/fr\]\]"  # matches [[/fr]]
EN_OPEN = r"\[\[en\]\]"  # matches [[en]]
EN_CLOSE = r"\[\[/en\]\]"  # matches [[/en]]

TAG_IMG_IRCC_COAT_OF_ARMS = r"\[\[ircc-coat-arms\]\]"  # matches [[ircc-coat-arms]]
TAG_IMG_IRCC_GLOBAL_AFFAIRS = r"\[\[ircc-ga-seal\]\]"  # matches [[ircc-ga-seal]]
TAG_IMG_IRCC_IRCC_SEAL = r"\[\[ircc-seal\]\]"  # matches [[ircc-seal]]
TAG_IMG_IRCC_GC_SEAL = r"\[\[ircc-gc-seal\]\]"  # matches [[ircc-gc-seal]]

mistune._block_quote_leading_pattern = re.compile(r"^ *\^ ?", flags=re.M)
mistune.BlockGrammar.block_quote = re.compile(r"^( *\^[^\n]+(\n[^\n]+)*\n*)+")
mistune.BlockGrammar.list_block = re.compile(
    r"^( *)([•*-]|\d+\.)[^*][\s\S]+?"
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
mistune.BlockGrammar.list_item = re.compile(r"^(( *)(?:[•*-]|\d+\.)[^\n]*" r"(?:\n(?!\2(?:[•*-]|\d+\.))[^\n]*)*)", flags=re.M)
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
    return re.sub(govuk_not_a_link, r"\1" + ".\u200B" + r"\2", message)  # Unicode zero-width space


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
                '<ol style="Margin: 0 0 0 20px; padding: 0; list-style-type: decimal;">'
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
                '<ul style="Margin: 0 0 0 20px; padding: 0; list-style-type: disc;">'
                "{}"
                "</ul>"
                "</td>"
                "</tr>"
                "</table>"
            ).format(body)
        )

    def list_item(self, text):
        return (
            '<li style="Margin: 5px 0 5px; padding: 0 0 0 5px; font-size: 19px;'
            'line-height: 25px; color: #0B0C0C;">'
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


def add_language_divs(_content: str) -> str:
    """
    Custom parser to add the language divs.

    We need to search for and remove the EMAIL_P_OPEN_TAG and EMAIL_P_CLOSE_TAG
    because the mistune parser has already run and put our [[lang]] tags inside
    paragraphs.
    """
    select_anything = r"([\s\S]*)"
    fr_regex = re.compile(
        f"{EMAIL_P_OPEN_TAG}{FR_OPEN}{EMAIL_P_CLOSE_TAG}{select_anything}{EMAIL_P_OPEN_TAG}{FR_CLOSE}{EMAIL_P_CLOSE_TAG}"
    )  # matches <p ...>[[fr]]</p>anything<p ...>[[/fr]]</p>
    content = fr_regex.sub(r'<div lang="fr-ca">\1</div>', _content)  # \1 returns the "anything" content above

    en_regex = re.compile(
        f"{EMAIL_P_OPEN_TAG}{EN_OPEN}{EMAIL_P_CLOSE_TAG}{select_anything}{EMAIL_P_OPEN_TAG}{EN_CLOSE}{EMAIL_P_CLOSE_TAG}"
    )  # matches <p ...>[[en]]</p>anything<p ...>[[/en]]</p>
    content = en_regex.sub(r'<div lang="en-ca">\1</div>', content)  # \1 returns the "anything" content above
    return content


def remove_language_divs(_content: str) -> str:
    """Remove the tags from content. This fn is for use in the email
    preheader, since this is plain text not html"""
    return remove_tags(_content, FR_OPEN, FR_CLOSE, EN_OPEN, EN_CLOSE)


def add_img_tag(_content: str, tag, img_location, alt_text="", height=300, width=300) -> str:
    """
    Custom parser to add custom img in the email.

    This is a custom temporary change not meant to exist for more than a few
    weeks. This should either be removed or upgraded into a full-fledged
    feature.

    TODO: Review, remove/upgrade this functionality.
    """
    tag_regex = re.compile(f"{tag}")  # matches tag
    content = tag_regex.sub(
        r"""<div style="margin: 20px auto 30px auto;">
          <img
            src="{img_loc}"
            alt="{alt}"
            height="{h}"
            width="{w}"
          />
        </div>""".format(
            img_loc=img_location, alt=alt_text, h=str(height), w=str(width)
        ),
        _content,
    )

    return content


def add_ircc_ga_seal(_content: str) -> str:
    """
    Custom parser to add IRCC Global Affairs seal logo.

    This is a custom temporary change not meant to exist for more than a few
    weeks. This should either be removed or upgraded into a full-fledged
    feature.

    TODO: Review, remove/upgrade this functionality.
    """
    img_loc = "https://assets.notification.canada.ca/gc-ircc-ga-seal.png"
    alt_text = "Global Affairs Canada / Affaires mondiales Canada"
    return add_img_tag(_content, TAG_IMG_IRCC_GLOBAL_AFFAIRS, img_loc, alt_text, 295, 281)


def add_ircc_seal(_content: str) -> str:
    """
    Custom parser to add IRCC seal logo.

    This is a custom temporary change not meant to exist for more than a few
    weeks. This should either be removed or upgraded into a full-fledged
    feature.

    TODO: Review, remove/upgrade this functionality.
    """
    img_loc = "https://assets.notification.canada.ca/gc-ircc-seal.png"
    alt_text = "Immigration, Refugees and Citizenship Canada / Immigration, Réfugiés et Citoyenneté Canada"
    return add_img_tag(_content, TAG_IMG_IRCC_IRCC_SEAL, img_loc, alt_text, 295, 281)


def add_ircc_gc_seal(_content: str) -> str:
    """
    Custom parser to add Government of Canada seal logo.

    This is a custom temporary change not meant to exist for more than a few
    weeks. This should either be removed or upgraded into a full-fledged
    feature.

    TODO: Review, remove/upgrade this functionality.
    """
    img_loc = "https://assets.notification.canada.ca/gc-ircc-gc-seal.png"
    alt_text = "Government of Canada / Gouvernement du Canada"
    return add_img_tag(_content, TAG_IMG_IRCC_GC_SEAL, img_loc, alt_text, 295, 281)


def add_ircc_coat_of_arms(_content: str) -> str:
    """
    Custom parser to add IRCC coat of arms logo.

    This is a custom temporary change not meant to exist for more than a few
    weeks. This should either be removed or upgraded into a full-fledged
    feature.

    TODO: Review, remove/upgrade this functionality.
    """
    img_loc = "https://assets.notification.canada.ca/gc-ircc-coat-of-arms.png"
    alt_text = "Arms of Her Majesty The Queen in Right of Canada / Armoiries de Sa Majesté la reine du Canada"
    return add_img_tag(_content, TAG_IMG_IRCC_COAT_OF_ARMS, img_loc, alt_text, 201, 200)


def remove_tags(_content: str, *tags) -> str:
    """Remove the tags in parameters from content.

    This function is for use in the email preheader, since this is plain text
    not html."""
    content = _content
    for tag in tags:
        content = re.compile(tag).sub("", content)
    return content
