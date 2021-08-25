from tidylib import tidy_document
from typing import Dict


def check_if_string_contains_valid_html(content: str) -> list:
    """
    Check if html snippet is valid - returns [] if html is valid.
    This is only a partial document, so we expect the Doctype and title to be missing.
    """

    allowed_errors = [
        "Warning: missing <!DOCTYPE> declaration",
        "Warning: inserting missing 'title' element",
    ]

    # the content can contain markdown as well as html - wrap the content in a div so it has a chance of being valid html
    content_in_div = f"<div>{content}</div>"
    document, errors = tidy_document(content_in_div, options={"numeric-entities": 1})

    # tidy_document returns errors that are concatenated together in a string, but we need them as a list
    error_list = errors.split("\n")[:-1]

    allowed_error_dict: Dict[str, bool] = {}
    for error in error_list:
        allowed_error_dict[error] = False
        for allowed_error in allowed_errors:
            if allowed_error in error:
                allowed_error_dict[error] = True

    significant_errors = [error for error, allowed in allowed_error_dict.items() if not allowed]
    return significant_errors
