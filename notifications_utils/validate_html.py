from py_w3c.validators.html.validator import HTMLValidator


def check_if_string_contains_valid_html(content: str) -> list:
    """
    Check if html snippet is valid - returns [] if html is valid.
    This is only a partial document, so we expect the Doctype and title to be missing.
    """

    allowed_errors = [
        "Start tag seen without seeing a doctype first. Expected “<!DOCTYPE html>”.",
        "Element “head” is missing a required instance of child element “title”.",
    ]

    # the content can contain markdown as well as html - wrap the content in a div so it has a chance of being valid html
    content_in_div = f"<div>{content}</div>"

    val = HTMLValidator()
    val.validate_fragment(content_in_div)

    significant_errors = []
    for error in val.errors:
        if error["message"] in allowed_errors:
            continue
        significant_errors.append(error)

    return significant_errors
