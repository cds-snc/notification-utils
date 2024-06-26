from collections import OrderedDict
from functools import lru_cache


class Columns(dict):
    def __init__(self, row_dict):
        super().__init__({Columns.make_key(key): value for key, value in row_dict.items()})

    @classmethod
    def from_keys(cls, keys):
        return cls({key: key for key in keys})

    def __getitem__(self, key):
        return super().get(Columns.make_key(key))

    def __contains__(self, key):
        return Columns.make_key(key) in super().copy()

    def get(self, key, default=None):
        return self[key] if self[key] is not None else default

    def copy(self):
        return Columns(super().copy())

    def as_dict_with_keys(self, keys):
        return {key: self.get(key) for key in keys}

    @staticmethod
    @lru_cache(maxsize=32, typed=False)
    def make_key(original_key):
        if original_key is None:
            return None
        return "".join(character.lower() for character in original_key if character not in " _-")


class Row(Columns):
    message_too_long = False

    def __init__(
        self,
        row_dict,
        index,
        error_fn,
        recipient_column_headers,
        placeholders,
        template,
        template_type=None,
    ):
        self.index = index
        self.recipient_column_headers = recipient_column_headers
        self.placeholders = placeholders
        if template_type:
            self.template_type = template_type
        else:
            self.template_type = template.template_type if template else None
        self.recipient_column_hearders_lang_check = (
            ["email address", "adresse courriel", "to"]
            if self.template_type == "email"
            else ["phone number", "numéro de téléphone", "to"]
        )

        # This won't mark a row as too long in all cases. A message can be too long if
        # placeholder content is added by a user that exceeds the limit when added to
        # the template's content.
        if template:
            template.values = row_dict
            self.message_too_long = template.is_message_too_long()

        super().__init__(OrderedDict((key, Cell(key, value, error_fn, self.placeholders)) for key, value in row_dict.items()))

    def __getitem__(self, key):
        return super().__getitem__(key) or Cell()

    def get(self, key, default=None):
        if self[key] == Cell() and default is not None:
            return default
        return self[key]

    @property
    def has_error(self):
        return self.message_too_long or any(cell.error for cell in self.values())

    @property
    def has_bad_recipient(self):
        """
        If the column has an error in the recipient field we want
        to return True, otherwise False

        The recipient field is the first column in the csv.
        """
        for column in self.recipient_column_hearders_lang_check:
            if self.get(column).recipient_error is True:
                return True
        return False

    @property
    def has_missing_data(self):
        return any(cell.error == Cell.missing_field_error for cell in self.values())

    @property
    def recipient(self):
        """
        We want to return the recipient from the first column in the csv
        The reason we use self.recipient_column_hearders_lang_check is because
        we want to check for the column name in both english and french.

        The recipient field is the first column in the csv. The column name
        might be in english even though we are in french context and vice versa.
        This is why we need to check both languages.
        """
        for column in self.recipient_column_hearders_lang_check:
            if self.get(column).data is not None:
                return self.get(column).data

    @property
    def personalisation(self):
        return Columns({key: cell.data for key, cell in self.items() if key in self.placeholders})

    @property
    def recipient_and_personalisation(self):
        return Columns({key: cell.data for key, cell in self.items()})


class Cell:
    missing_field_error = "Missing"

    def __init__(self, key=None, value=None, error_fn=None, placeholders=None):
        self.data = value
        self.error = error_fn(key, value) if error_fn else None
        self.ignore = Columns.make_key(key) not in (placeholders or [])

    def __eq__(self, other):
        if not other.__class__ == self.__class__:
            return False
        return all(
            (
                self.data == other.data,
                self.error == other.error,
                self.ignore == other.ignore,
            )
        )

    @property
    def recipient_error(self):
        # TODO: This is a bandaid solution. We need to establish why we are calling this Cell property on
        #       Cells that do not represent a recipient value.
        if self.error is not None and "Some messages may be too long due to custom content." in self.error:
            return False

        return self.error not in {None, self.missing_field_error}
