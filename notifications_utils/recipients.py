import re
import sys
import csv
import phonenumbers
import os
from io import StringIO
from contextlib import suppress
from functools import lru_cache, partial
from itertools import islice
from collections import OrderedDict, namedtuple
from orderedset import OrderedSet

from flask import current_app

from . import EMAIL_REGEX_PATTERN, hostname_part, tld_part
from notifications_utils.formatters import strip_and_remove_obscure_whitespace, strip_whitespace
from notifications_utils.template import Template
from notifications_utils.columns import Columns, Row, Cell
from notifications_utils.international_billing_rates import (
    INTERNATIONAL_BILLING_RATES,
)


country_code = os.getenv("PHONE_COUNTRY_CODE", "1")
region_code = os.getenv("PHONE_REGION_CODE", "US")

first_column_headings = {
    'email': ['email address'],
    'sms': ['phone number'],
    'letter': [
        'address line 1',
        'address line 2',
        'address line 3',
        'address line 4',
        'address line 5',
        'address line 6',
        'postcode',
    ],
}

optional_address_columns = {
    'address line 3',
    'address line 4',
    'address line 5',
    'address line 6',
}


class RecipientCSV():

    def __init__(
        self,
        file_data,
        template_type=None,
        placeholders=None,
        max_errors_shown=20,
        max_initial_rows_shown=10,
        safelist=None,
        template=None,
        remaining_messages=sys.maxsize,
        international_sms=False,
        max_rows=50000,
    ):
        self.file_data = strip_whitespace(file_data, extra_characters=',')
        self.template_type = template_type
        self.placeholders = placeholders
        self.max_errors_shown = max_errors_shown
        self.max_initial_rows_shown = max_initial_rows_shown
        self.safelist = safelist
        self.template = template if isinstance(template, Template) else None
        self.international_sms = international_sms
        self.remaining_messages = remaining_messages
        self.rows_as_list = None
        self.max_rows = max_rows

    def __len__(self):
        if not hasattr(self, '_len'):
            self._len = len(self.rows)
        return self._len

    def __getitem__(self, requested_index):
        return self.rows[requested_index]

    @property
    def safelist(self):
        return self._safelist

    @safelist.setter
    def safelist(self, value):
        try:
            self._safelist = list(value)
        except TypeError:
            self._safelist = []

    @property
    def placeholders(self):
        return self._placeholders

    @placeholders.setter
    def placeholders(self, value):
        try:
            self._placeholders = list(value) + self.recipient_column_headers
        except TypeError:
            self._placeholders = self.recipient_column_headers
        self.placeholders_as_column_keys = [
            Columns.make_key(placeholder)
            for placeholder in self._placeholders
        ]
        self.recipient_column_headers_as_column_keys = [
            Columns.make_key(placeholder)
            for placeholder in self.recipient_column_headers
        ]

    @property
    def template_type(self):
        return self._template_type

    @template_type.setter
    def template_type(self, value):
        self._template_type = value
        self.recipient_column_headers = first_column_headings[self.template_type]

    @property
    def has_errors(self):
        return bool(
            self.missing_column_headers or
            self.duplicate_recipient_column_headers or
            self.more_rows_than_can_send or
            self.too_many_rows or
            (not self.allowed_to_send_to) or
            any(self.rows_with_errors)
        )  # `or` is 3x faster than using `any()` here

    @property
    def allowed_to_send_to(self):
        if self.template_type == 'letter':
            return True
        if not self.safelist:
            return True
        return all(
            allowed_to_send_to(row.recipient, self.safelist)
            for row in self.rows
        )

    @property
    def rows(self):
        if self.rows_as_list is None:
            self.rows_as_list = list(self.get_rows())
        return self.rows_as_list

    @property
    def _rows(self):
        return csv.reader(
            StringIO(self.file_data.strip()),
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=True,
        )

    def get_rows(self):

        column_headers = self._raw_column_headers  # this is for caching
        length_of_column_headers = len(column_headers)

        rows_as_lists_of_columns = self._rows

        next(rows_as_lists_of_columns, None)  # skip the header row

        for index, row in enumerate(rows_as_lists_of_columns):

            output_dict = OrderedDict()

            for column_name, column_value in zip(column_headers, row):

                column_value = strip_and_remove_obscure_whitespace(column_value)

                if Columns.make_key(column_name) in self.recipient_column_headers_as_column_keys:
                    output_dict[column_name] = column_value or None
                else:
                    insert_or_append_to_dict(output_dict, column_name, column_value or None)

            length_of_row = len(row)

            if length_of_column_headers < length_of_row:
                output_dict[None] = row[length_of_column_headers:]
            elif length_of_column_headers > length_of_row:
                for key in column_headers[length_of_row:]:
                    insert_or_append_to_dict(output_dict, key, None)

            if index < self.max_rows:
                yield Row(
                    output_dict,
                    index=index,
                    error_fn=self._get_error_for_field,
                    recipient_column_headers=self.recipient_column_headers,
                    placeholders=self.placeholders_as_column_keys,
                    template=self.template,
                )
            else:
                yield None

    @property
    def more_rows_than_can_send(self):
        return len(self) > self.remaining_messages

    @property
    def too_many_rows(self):
        return len(self) > self.max_rows

    @property
    def initial_rows(self):
        return islice(self.rows, self.max_initial_rows_shown)

    @property
    def displayed_rows(self):
        if any(self.rows_with_errors) and not self.missing_column_headers:
            return self.initial_rows_with_errors
        return self.initial_rows

    def _filter_rows(self, attr):
        return (row for row in self.rows if row and getattr(row, attr))

    @property
    def rows_with_errors(self):
        return self._filter_rows('has_error')

    @property
    def rows_with_bad_recipients(self):
        return self._filter_rows('has_bad_recipient')

    @property
    def rows_with_missing_data(self):
        return self._filter_rows('has_missing_data')

    @property
    def rows_with_message_too_long(self):
        return self._filter_rows('message_too_long')

    @property
    def initial_rows_with_errors(self):
        return islice(self.rows_with_errors, self.max_errors_shown)

    @property
    def _raw_column_headers(self):
        for row in self._rows:
            return row
        return []

    @property
    def column_headers(self):
        return list(OrderedSet(self._raw_column_headers))

    @property
    def column_headers_as_column_keys(self):
        return Columns.from_keys(self.column_headers).keys()

    @property
    def missing_column_headers(self):
        return set(
            key for key in self.placeholders
            if (
                Columns.make_key(key) not in self.column_headers_as_column_keys and
                not self.is_optional_address_column(key)
            )
        )

    @property
    def duplicate_recipient_column_headers(self):

        raw_recipient_column_headers = [
            Columns.make_key(column_header)
            for column_header in self._raw_column_headers
            if Columns.make_key(column_header) in self.recipient_column_headers_as_column_keys
        ]

        return OrderedSet((
            column_header
            for column_header in self._raw_column_headers
            if raw_recipient_column_headers.count(Columns.make_key(column_header)) > 1
        ))

    def is_optional_address_column(self, key):
        return (
            self.template_type == 'letter'
            and Columns.make_key(key) in Columns.from_keys(optional_address_columns).keys()
        )

    @property
    def has_recipient_columns(self):
        return set(
            Columns.make_key(recipient_column)
            for recipient_column in self.recipient_column_headers
            if not self.is_optional_address_column(recipient_column)
        ) <= self.column_headers_as_column_keys

    def _get_error_for_field(self, key, value):  # noqa: C901

        if self.is_optional_address_column(key):
            return

        if Columns.make_key(key) in self.recipient_column_headers_as_column_keys:
            if value in [None, ''] or isinstance(value, list):
                if self.duplicate_recipient_column_headers:
                    return None
                else:
                    return Cell.missing_field_error
            try:
                validate_recipient(
                    value,
                    self.template_type,
                    column=key,
                    international_sms=self.international_sms
                )
            except (InvalidEmailError, InvalidPhoneError, InvalidAddressError) as error:
                return str(error)

        if Columns.make_key(key) not in self.placeholders_as_column_keys:
            return

        if value in [None, '']:
            return Cell.missing_field_error


class InvalidEmailError(Exception):

    def __init__(self, message=None):
        super().__init__(message or 'Not a valid email address')


class InvalidPhoneError(InvalidEmailError):
    pass


class InvalidAddressError(InvalidEmailError):
    pass


def normalise_phone_number(number):
    match = parse_number(number, region_code) or parse_number(number)

    if match:
        return phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)

    return False


def is_local_phone_number(number):
    if parse_number(number, region_code) is False:
        return False
    else:
        return True


international_phone_info = namedtuple('PhoneNumber', [
    'international',
    'country_prefix',
    'billable_units',
])


def get_international_phone_info(number):

    number = validate_phone_number(number, international=True)
    prefix = get_international_prefix(number)

    return international_phone_info(
        international=(prefix != country_code),
        country_prefix=prefix,
        billable_units=get_billable_units_for_prefix(prefix)
    )


def get_international_prefix(number):
    number = phonenumbers.parse(number, None)
    return str(number.country_code)


def get_billable_units_for_prefix(prefix):
    return INTERNATIONAL_BILLING_RATES[prefix]['billable_units']


def validate_local_phone_number(number, column=None):
    match = parse_number(number, region_code)
    if match:
        return phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
    else:
        raise InvalidPhoneError('Not a valid local number')


def validate_phone_number(number, column=None, international=False):

    if(";" in number):
        raise InvalidPhoneError('Not a valid number')

    if (not international) or is_local_phone_number(number):
        return validate_local_phone_number(number)

    number = normalise_phone_number(number)

    if number is False:
        raise InvalidPhoneError('Not a valid international number')

    if len(number) < 8:
        raise InvalidPhoneError('Not enough digits')

    if get_international_prefix(number) is None:
        raise InvalidPhoneError('Not a valid country prefix')

    return number


validate_and_format_phone_number = validate_phone_number


def try_validate_and_format_phone_number(number, column=None, international=None, log_msg=None):
    """
    For use in places where you shouldn't error if the phone number is invalid - for example if firetext pass us
    something in
    """
    try:
        return validate_and_format_phone_number(number, column, international)
    except InvalidPhoneError as exc:
        if log_msg:
            current_app.logger.warning('{}: {}'.format(log_msg, exc))
        return number


def validate_email_address(email_address, column=None):  # noqa (C901 too complex)
    # almost exactly the same as by https://github.com/wtforms/wtforms/blob/master/wtforms/validators.py,
    # with minor tweaks for SES compatibility - to avoid complications we are a lot stricter with the local part
    # than neccessary - we don't allow any double quotes or semicolons to prevent SES Technical Failures
    email_address = strip_and_remove_obscure_whitespace(email_address)
    match = re.match(EMAIL_REGEX_PATTERN, email_address)

    # not an email
    if not match:
        raise InvalidEmailError

    if len(email_address) > 320:
        raise InvalidEmailError

    # don't allow consecutive periods in either part
    if '..' in email_address:
        raise InvalidEmailError

    hostname = match.group(1)

    # idna = "Internationalized domain name" - this encode/decode cycle converts unicode into its accurate ascii
    # representation as the web uses. '例え.テスト'.encode('idna') == b'xn--r8jz45g.xn--zckzah'
    try:
        hostname = hostname.encode('idna').decode('ascii')
    except UnicodeError:
        raise InvalidEmailError

    parts = hostname.split('.')

    if len(hostname) > 253 or len(parts) < 2:
        raise InvalidEmailError

    for part in parts:
        if not part or len(part) > 63 or not hostname_part.match(part):
            raise InvalidEmailError

    # if the part after the last . is not a valid TLD then bail out
    if not tld_part.match(parts[-1]):
        raise InvalidEmailError

    return email_address


def format_email_address(email_address):
    return strip_and_remove_obscure_whitespace(email_address.lower())


def validate_and_format_email_address(email_address):
    return format_email_address(validate_email_address(email_address))


def validate_address(address_line, column):
    if Columns.make_key(column) in Columns.from_keys(optional_address_columns).keys():
        return address_line
    if Columns.make_key(column) not in Columns.from_keys(first_column_headings['letter']).keys():
        raise TypeError
    if not address_line or not strip_whitespace(address_line):
        raise InvalidAddressError('Missing')
    return address_line


def validate_recipient(recipient, template_type, column=None, international_sms=False):
    return {
        'email': validate_email_address,
        'sms': partial(validate_phone_number, international=international_sms),
        'letter': validate_address,
    }[template_type](recipient, column)


@lru_cache(maxsize=32, typed=False)
def format_recipient(recipient):
    if not isinstance(recipient, str):
        return ''
    with suppress(InvalidPhoneError):
        return validate_and_format_phone_number(recipient)
    with suppress(InvalidEmailError):
        return validate_and_format_email_address(recipient)
    return recipient


def format_phone_number_human_readable(phone_number):
    match = parse_number(phone_number, region_code) or parse_number(phone_number)

    if match:
        return phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

    return phone_number


def allowed_to_send_to(recipient, safelist):
    return format_recipient(recipient) in [
        format_recipient(recipient) for recipient in safelist
    ]


def insert_or_append_to_dict(dict_, key, value):
    if dict_.get(key):
        if isinstance(dict_[key], list):
            dict_[key].append(value)
        else:
            dict_[key] = [dict_[key], value]
    else:
        dict_.update({key: value})


def parse_number(number, region=None):
    matches = []
    for match in phonenumbers.PhoneNumberMatcher(number, region):
        matches.append(match)

    if len(matches) > 0:
        if region is not None:
            if matches[0].number.country_code == int(country_code):
                return matches[0]
            else:
                return False
        return matches[0]
    else:
        return False
