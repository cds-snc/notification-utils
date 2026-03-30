import re
from typing import Any, Callable, Dict, List, Literal, Optional

from flask import Markup
from ordered_set import OrderedSet

from notifications_utils.columns import Columns
from notifications_utils.formatters import (
    escape_html,
    strip_dvla_markup,
    strip_html,
    unescaped_formatted_list,
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
    # Matches multi-line conditional blocks where the closing )) is on its own line.
    # Group 1: condition name, Group 2: conditional body content.
    # Example: ((show_section??\n((variable_1))\n((variable_2))\n))
    multiline_conditional_pattern = re.compile(r"\(\(([^?\n)(]+)\?\?\n([\s\S]*?)\n[ \t]*\)\)")
    placeholder_pattern_for_link_url = re.compile(
        r"(?<=\]\()"  # Lookbehind for markdown link URL pattern
        r"\({2}"  # Match opening double parentheses
        r"(?!\()"  # Negative lookahead to enforce consumption of late parenthesis and not early ones
        r"([\s\S]+?)"  # Body of placeholder - potentially standard or conditional
        r"\){2}"  # Match closing double parentheses
    )

    placeholder_tag = "<mark class='placeholder'>(({}))</mark>"
    conditional_placeholder_tag = "<mark class='placeholder-conditional'><span class='condition'>(({}??</span>{}))</mark>"
    conditional_placeholder_tag_block = "<div class='placeholder-conditional'><span class='condition'>(({}??</span>{}))</div>"
    placeholder_tag_translated = "<span class='placeholder-no-brackets'>[{}]</span>"
    placeholder_tag_redacted = "<mark class='placeholder-redacted'>[hidden]</mark>"

    def __init__(
        self,
        content: str,
        values: Optional[Dict[str, Any]] = None,
        html: HtmlSanitizers = "strip",
        markdown_lists: bool = False,
        redact_missing_personalisation: bool = False,
        translated: bool = False,
        markdown_renderer: Optional[Callable] = None,
    ):
        self.content = content
        self.values = values
        self.markdown_lists = markdown_lists
        self.markdown_renderer = markdown_renderer
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

    def _replace_multiline_conditional_match(self, match):
        """Replacement callback for multi-line conditional blocks in the `replaced` pass."""
        name = match.group(1).strip()
        body = match.group(2)
        replacement = self.values.get(name)

        if replacement is None:
            # Value not provided — format as a placeholder block
            body_formatted = re.sub(self.placeholder_pattern, self.format_match, body)
            return self.conditional_placeholder_tag_block.format(self.sanitizer(name), body_formatted) + "\n"

        if str2bool(replacement):
            return re.sub(self.placeholder_pattern, self.replace_match, body)
        return ""

    def _format_multiline_conditional_match(self, match):
        """Replacement callback for multi-line conditional blocks in the `formatted` pass."""
        name = match.group(1).strip()
        body = match.group(2)
        if self.redact_missing_personalisation:
            return self.placeholder_tag_redacted
        body_formatted = re.sub(self.placeholder_pattern, self.format_match, body)
        return self.conditional_placeholder_tag_block.format(self.sanitizer(name), body_formatted) + "\n"

    def format_match_in_link_url(self, match):
        placeholder = Placeholder.from_match(match)
        return placeholder.name

    def format_match(self, match):
        placeholder = Placeholder.from_match(match)

        if self.redact_missing_personalisation:
            return self.placeholder_tag_redacted

        if placeholder.is_conditional():
            conditional_text = self.sanitizer(placeholder.conditional_text)
            sanitized_name = self.sanitizer(placeholder.name)

            if "\n" in conditional_text and self.markdown_renderer:
                # Multi-line conditional: pre-render markdown so lists, links, etc.
                # display correctly. Use a block-level <div> wrapper so the outer
                # mistune pass treats it as an HTML block and won't break it apart.
                stripped = conditional_text.strip()
                rendered = self.markdown_renderer(stripped).strip() if stripped else ""
                return self.conditional_placeholder_tag_block.format(sanitized_name, rendered) + "\n"
            elif "\n" in conditional_text:
                # Multi-line but no renderer available: convert newlines to <br>
                conditional_text = conditional_text.strip("\n").replace("\n", "<br>")

            return self.conditional_placeholder_tag.format(sanitized_name, conditional_text)

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
        _sanitized_content = self.sanitizer(self.content)
        sanitized_content = re.sub(self.placeholder_pattern_for_link_url, self.format_match_in_link_url, _sanitized_content)
        content = re.sub(self.multiline_conditional_pattern, self._format_multiline_conditional_match, sanitized_content)
        return re.sub(self.placeholder_pattern, self.format_match, content)

    @property
    def formatted(self):
        return Markup(self._raw_formatted)

    @property
    def placeholders(self):
        result = OrderedSet()
        # Collect condition names and inner variables from multi-line conditional blocks
        for mc_match in self.multiline_conditional_pattern.finditer(self.content):
            result.add(mc_match.group(1).strip())
            for body in re.findall(self.placeholder_pattern, mc_match.group(2)):
                result.add(Placeholder(body).name)
        # Collect placeholders from content outside multi-line conditional blocks
        remaining = re.sub(self.multiline_conditional_pattern, "", self.content)
        for body in re.findall(self.placeholder_pattern, remaining):
            result.add(Placeholder(body).name)
        return result

    @property
    def placeholders_meta(self):
        meta = {}

        # Handle multi-line conditional blocks: the condition name is conditional (boolean),
        # and variables inside the body are regular (non-conditional) placeholders.
        for mc_match in self.multiline_conditional_pattern.finditer(self.content):
            name = mc_match.group(1).strip()
            if name not in meta:
                meta[name] = {"is_conditional": True}
            for body in re.findall(self.placeholder_pattern, mc_match.group(2)):
                inner_name = Placeholder(body).name
                if inner_name not in meta:
                    meta[inner_name] = {"is_conditional": False}
                if Placeholder(body).is_conditional():
                    meta[inner_name] = {"is_conditional": True}

        # This loop iterates over each instance in the template where a variable is used.
        # The same variable will be hit multiple times if it appears more than
        # once.
        remaining = re.sub(self.multiline_conditional_pattern, "", self.content)
        for body in re.findall(self.placeholder_pattern, remaining):
            if Placeholder(body).name not in meta:
                # never let a False overwrite a True
                meta[Placeholder(body).name] = {"is_conditional": False}

            # If the variable appears in a conditional statement in the template,
            # we consider it a conditional variable and encourage the user to set it to a
            # boolean value
            if Placeholder(body).is_conditional():
                meta[Placeholder(body).name] = {"is_conditional": True}

        return meta

    @property
    def replaced(self):
        content = self.sanitizer(self.content)
        content = re.sub(self.multiline_conditional_pattern, self._replace_multiline_conditional_match, content)
        return re.sub(self.placeholder_pattern, self.replace_match, content)


def str2bool(value):
    if not value:
        return False
    return str(value).lower() in ("yes", "y", "true", "t", "1", "include", "show", "oui", "vrai", "inclure", "afficher")
