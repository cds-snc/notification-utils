import re
from typing import Any, Callable, Dict, List, Literal

from orderedset import OrderedSet
from flask import Markup

from notifications_utils.columns import Columns
from notifications_utils.formatters import (
    unescaped_formatted_list,
    strip_html,
    escape_html,
    strip_dvla_markup,
)


class Placeholder:
    def __init__(self, body):
        # body should not include the (( and )).
        self.body = body.lstrip("((").rstrip("))")

    @classmethod
    def from_match(cls, match):
        return cls(match.group(0))

    def is_conditional(self):
        return "??" in self.body

    @property
    def name(self):
        # for non conditionals, name equals body
        return self.body.split("??")[0]

    @property
    def conditional_text(self):
        if self.is_conditional():
            # ((a?? b??c)) returns " b??c"
            return "??".join(self.body.split("??")[1:])
        else:
            raise ValueError("{} not conditional".format(self))

    def get_conditional_body(self, show_conditional):
        # note: unsanitised/converted
        if self.is_conditional():
            return self.conditional_text if str2bool(show_conditional) else ""
        else:
            raise ValueError("{} not conditional".format(self))

    def __repr__(self):
        return "Placeholder({})".format(self.body)


HtmlSanitizers = Literal["strip", "escape", "passthrough", "strip_dvla_markup"]


class Field:
    # this needs to be made conditional so it works in the (((colour))) -> (blue) case
    # Deconstructed regular expression segments in order:
    # * First segment: opening ((,
    # * negative lookahead assertion to enforce consumption of late parenthesis and not early ones,
    # * body of placeholder - potentially standard or conditional,
    # * closing ))
    placeholder_pattern = re.compile(r"\({2}" r"(?!\()" r"([\s\S]+?)" r"\){2}")
    placeholder_tag = "<span class='placeholder'>(({}))</span>"
    conditional_placeholder_tag = "<span class='placeholder-conditional'>(({}??</span>{}))"
    placeholder_tag_translated = "<span class='placeholder-no-brackets'>[{}]</span>"
    placeholder_tag_redacted = "<span class='placeholder-redacted'>[hidden]</span>"

    def __init__(
        self,
        content: str,
        values: Dict[str, Any] = None,
        html: HtmlSanitizers = "strip",
        markdown_lists: bool = False,
        redact_missing_personalisation: bool = False,
        translated: bool = False,
    ):
        self.content = content
        self.values = values
        self.markdown_lists = markdown_lists
        if translated:
            self.placeholder_tag = self.placeholder_tag_translated

        self.sanitizer = self.get_sanitizer(html)
        self.redact_missing_personalisation = redact_missing_personalisation

    def __str__(self):
        if self.values:
            return self.replaced
        return self.formatted

    def __repr__(self):
        return '{}("{}", {})'.format(self.__class__.__name__, self.content, self.values)  # TODO: more real

    @staticmethod
    def get_sanitizer(html: HtmlSanitizers) -> Callable:
        sanitizers: Dict[str, Callable] = {
            "strip": strip_html,
            "escape": escape_html,
            "passthrough": str,
            "strip_dvla_markup": strip_dvla_markup,
        }
        return sanitizers[html]

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values = Columns(value) if value else {}

    def format_match(self, match):
        placeholder = Placeholder.from_match(match)

        if self.redact_missing_personalisation:
            return self.placeholder_tag_redacted

        if placeholder.is_conditional():
            return self.conditional_placeholder_tag.format(
                self.sanitizer(placeholder.name), self.sanitizer(placeholder.conditional_text)
            )

        return self.placeholder_tag.format(self.sanitizer(placeholder.name))

    def replace_match(self, match):
        placeholder = Placeholder.from_match(match)
        replacement = self.values.get(placeholder.name)

        if placeholder.is_conditional() and replacement is not None:
            return placeholder.get_conditional_body(replacement)

        replaced_value = self.get_replacement(placeholder)
        if replaced_value is not None:
            return self.get_replacement(placeholder)

        return self.format_match(match)

    def get_replacement(self, placeholder):
        replacement = self.values.get(placeholder.name)
        if replacement is None:
            return None

        if isinstance(replacement, list):
            vals: List[Any] = list(filter(None, replacement))
            if not vals:
                return None
            return self.sanitizer(self.get_replacement_as_list(vals))

        return self.sanitizer(str(replacement))

    def get_replacement_as_list(self, replacement):
        if self.markdown_lists:
            return "\n\n" + "\n".join("* {}".format(item) for item in replacement)
        return unescaped_formatted_list(replacement, before_each="", after_each="")

    @property
    def _raw_formatted(self):
        return re.sub(self.placeholder_pattern, self.format_match, self.sanitizer(self.content))

    @property
    def formatted(self):
        return Markup(self._raw_formatted)

    @property
    def placeholders(self):
        return OrderedSet(Placeholder(body).name for body in re.findall(self.placeholder_pattern, self.content))

    @property
    def replaced(self):
        return re.sub(self.placeholder_pattern, self.replace_match, self.sanitizer(self.content))


def str2bool(value):
    if not value:
        return False
    return str(value).lower() in ("yes", "y", "true", "t", "1", "include", "show", "oui", "vrai", "inclure", "afficher")
