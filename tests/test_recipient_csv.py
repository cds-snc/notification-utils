import pytest
import itertools
import unicodedata
from functools import partial
from orderedset import OrderedSet

from notifications_utils import SMS_CHAR_COUNT_LIMIT
from notifications_utils.recipients import Cell, RecipientCSV, Row
from notifications_utils.template import SMSMessageTemplate


def _index_rows(rows):
    return set(row.index for row in rows)


@pytest.mark.parametrize(
    "file_contents,template_type,expected",
    [
        (
            "",
            "sms",
            [],
        ),
        (
            "phone number",
            "sms",
            [],
        ),
        (
            """
                phone number,name
                +1 123, test1
                +1 456,test2
            """,
            "sms",
            [
                [('phone number', '+1 123'), ('name', 'test1')],
                [('phone number', '+1 456'), ('name', 'test2')]
            ]
        ),
        (
            """
                phone number,name
                +1 123,
                +1 456
            """,
            "sms",
            [
                [('phone number', '+1 123'), ('name', None)],
                [('phone number', '+1 456'), ('name', None)]
            ]
        ),
        (
            """
                email address,name
                test@example.com,test1
                test2@example.com, test2
            """,
            "email",
            [
                [('email address', 'test@example.com'), ('name', 'test1')],
                [('email address', 'test2@example.com'), ('name', 'test2')]
            ]
        ),
        (
            """
                email address
                test@example.com,test1,red
                test2@example.com, test2,blue
            """,
            "email",
            [
                [('email address', 'test@example.com'), (None, ['test1', 'red'])],
                [('email address', 'test2@example.com'), (None, ['test2', 'blue'])]
            ]
        ),
        (
            """
                email address,name
                test@example.com,"test1"
                test2@example.com,"   test2    "
                test3@example.com," test3"
            """,
            "email",
            [
                [('email address', 'test@example.com'), ('name', 'test1')],
                [('email address', 'test2@example.com'), ('name', 'test2')],
                [('email address', 'test3@example.com'), ('name', 'test3')]
            ]
        ),
        (
            """
                email address,date,name
                test@example.com,"Nov 28, 2016",test1
                test2@example.com,"Nov 29, 2016",test2
            """,
            "email",
            [
                [('email address', 'test@example.com'), ('date', 'Nov 28, 2016'), ('name', 'test1')],
                [('email address', 'test2@example.com'), ('date', 'Nov 29, 2016'), ('name', 'test2')]
            ]
        ),
        (
            """
                address_line_1
                Alice
                Bob
            """,
            "letter",
            [
                [('address_line_1', 'Alice')],
                [('address_line_1', 'Bob')]
            ]
        ),
        (
            """
                address line 1,address line 2,address line 5,address line 6,postcode,name,thing
                A. Name,,,,XM4 5HQ,example,example
            """,
            "letter",
            [[
                ('addressline1', 'A. Name'),
                ('addressline2', None),
                # optional address rows 3 and 4 not in file
                ('addressline5', None),
                ('addressline5', None),
                ('postcode', 'XM4 5HQ'),
                ('name', 'example'),
                ('thing', 'example'),
            ]]
        ),
        (
            """
                phone number, list, list, list
                07900900001, cat, rat, gnat
                07900900002, dog, hog, frog
                07900900003, elephant
            """,
            "sms",
            [
                [
                    ('phone number', '07900900001'),
                    ('list', ['cat', 'rat', 'gnat'])
                ],
                [
                    ('phone number', '07900900002'),
                    ('list', ['dog', 'hog', 'frog'])
                ],
                [
                    ('phone number', '07900900003'),
                    ('list', ['elephant', None, None])
                ],
            ]
        )
    ]
)
def test_get_rows(file_contents, template_type, expected):
    rows = list(RecipientCSV(file_contents, template_type=template_type).rows)
    if not expected:
        assert rows == expected
    for index, row in enumerate(expected):
        assert len(rows[index].items()) == len(row)
        for key, value in row:
            assert rows[index].get(key).data == value


def test_get_rows_does_no_error_checking_of_rows_or_cells(mocker):
    has_error_mock = mocker.patch.object(Row, 'has_error')
    has_bad_recipient_mock = mocker.patch.object(Row, 'has_bad_recipient')
    has_missing_data_mock = mocker.patch.object(Row, 'has_missing_data')
    cell_recipient_error_mock = mocker.patch.object(Cell, 'recipient_error')

    recipients = RecipientCSV(
        """
            email address, name
            a@b.com,
            a@b.com, My Name
            a@b.com,


        """,
        template_type='email',
        placeholders=['name'],
        max_errors_shown=3
    )

    rows = recipients.get_rows()
    for i in range(3):
        assert next(rows).recipient == 'a@b.com'

    assert has_error_mock.called is False
    assert has_bad_recipient_mock.called is False
    assert has_missing_data_mock.called is False
    assert cell_recipient_error_mock.called is False


def test_get_rows_only_iterates_over_file_once(mocker):
    row_mock = mocker.patch('notifications_utils.recipients.Row')

    recipients = RecipientCSV(
        """
            email address, name
            a@b.com,
            a@b.com, My Name
            a@b.com,


        """,
        template_type='email',
        placeholders=['name'],
    )

    rows = recipients.get_rows()
    for i in range(3):
        next(rows)

    assert row_mock.call_count == 3
    assert recipients.rows_as_list is None


@pytest.mark.parametrize(
    "file_contents,template_type,expected",
    [
        (
            """
                phone number,name
                6502532222, test1
                +1 650 253 2222,test2
                ,
            """,
            'sms',
            [
                {
                    'index': 0,
                    'message_too_long': False
                },
                {
                    'index': 1,
                    'message_too_long': False
                },
            ]
        ),
        (
            """
                email address,name,colour
                test@example.com,test1,blue
                test2@example.com, test2,red
            """,
            'email',
            [
                {
                    'index': 0,
                    'message_too_long': False
                },
                {
                    'index': 1,
                    'message_too_long': False
                },
            ]
        )
    ]
)
def test_get_annotated_rows(file_contents, template_type, expected):
    recipients = RecipientCSV(
        file_contents,
        template_type=template_type,
        placeholders=['name'],
        max_initial_rows_shown=1
    )
    for index, expected_row in enumerate(expected):
        annotated_row = list(recipients.rows)[index]
        assert annotated_row.index == expected_row['index']
        assert annotated_row.message_too_long == expected_row['message_too_long']
    assert len(list(recipients.rows)) == 2
    assert len(list(recipients.initial_rows)) == 1
    assert not recipients.has_errors


def test_get_rows_with_errors():
    recipients = RecipientCSV(
        """
            email address, name
            a@b.com,
            a@b.com,
            a@b.com,
            a@b.com,
            a@b.com,
            a@b.com,


        """,
        template_type='email',
        placeholders=['name'],
        max_errors_shown=3
    )
    assert len(list(recipients.rows_with_errors)) == 6
    assert len(list(recipients.initial_rows_with_errors)) == 3
    assert recipients.has_errors


@pytest.mark.parametrize('template_type, row_count, header, filler, row_with_error', [
    ('email', 500, "email address\n", "test@example.com\n", "test at example dot com"),
    ('sms', 500, "phone number\n", "6502532222\n", "12345"),
])
def test_big_list_validates_right_through(template_type, row_count, header, filler, row_with_error):
    big_csv = RecipientCSV(
        header + (filler * (row_count - 1) + row_with_error),
        template_type=template_type,
        max_errors_shown=100,
        max_initial_rows_shown=3
    )
    assert len(list(big_csv.rows)) == row_count
    assert _index_rows(big_csv.rows_with_bad_recipients) == {row_count - 1}  # 0 indexed
    assert _index_rows(big_csv.rows_with_errors) == {row_count - 1}
    assert len(list(big_csv.initial_rows_with_errors)) == 1
    assert big_csv.has_errors


def test_big_list():
    big_csv = RecipientCSV(
        "email address,name\n" + ("a@b.com\n" * 50000),
        template_type='email',
        placeholders=['name'],
        max_errors_shown=100,
        max_initial_rows_shown=3,
        safelist=["a@b.com"]
    )
    assert len(list(big_csv.initial_rows)) == 3
    assert len(list(big_csv.initial_rows_with_errors)) == 100
    assert len(list(big_csv.rows)) == big_csv.max_rows
    assert big_csv.has_errors


def test_overly_big_list():
    big_csv = RecipientCSV(
        "phonenumber,name\n" + ("6502532222,example\n" * 50001),
        template_type='sms',
        placeholders=['name'],
    )
    assert len(big_csv) == 50001
    assert big_csv.too_many_rows is True
    assert big_csv.has_errors is True
    assert list(big_csv.rows_with_missing_data) == []
    assert list(big_csv.rows_with_bad_recipients) == []
    assert list(big_csv.rows_with_message_too_long) == []


@pytest.mark.parametrize(
    "file_contents,template_type,placeholders,expected_recipients,expected_personalisation",
    [
        (
            """
                phone number,name, date
                +1 123,test1,today
                +1456,    ,tomorrow
                ,,
                , ,
            """,
            'sms',
            ['name'],
            ['+1 123', '+1456'],
            [{'name': 'test1'}, {'name': None}]
        ),
        (
            """
                email address,name,colour
                test@example.com,test1,red
                testatexampledotcom,test2,blue
            """,
            'email',
            ['colour'],
            ['test@example.com', 'testatexampledotcom'],
            [
                {'colour': 'red'},
                {'colour': 'blue'}
            ]
        ),
        (
            """
                email address
                test@example.com,test1,red
                testatexampledotcom,test2,blue
            """,
            'email',
            [],
            ['test@example.com', 'testatexampledotcom'],
            []
        )
    ]
)
def test_get_recipient(file_contents, template_type, placeholders, expected_recipients, expected_personalisation):

    recipients = RecipientCSV(file_contents, template_type=template_type, placeholders=placeholders)

    for index, row in enumerate(expected_personalisation):
        for key, value in row.items():
            assert recipients[index].recipient == expected_recipients[index]
            assert recipients[index].personalisation.get(key) == value


@pytest.mark.parametrize(
    "file_contents,template_type,placeholders,expected_recipients,expected_personalisation",
    [
        (
            """
                email address,test
                test@example.com,test1,red
                testatexampledotcom,test2,blue
            """,
            'email',
            ['test'],
            [
                (0, 'test@example.com'),
                (1, 'testatexampledotcom')
            ],
            [
                {'emailaddress': 'test@example.com', 'test': 'test1'},
                {'emailaddress': 'testatexampledotcom', 'test': 'test2'},
            ],
        )
    ]
)
def test_get_recipient_respects_order(file_contents,
                                      template_type,
                                      placeholders,
                                      expected_recipients,
                                      expected_personalisation):
    recipients = RecipientCSV(file_contents, template_type=template_type, placeholders=placeholders)

    for row, email in expected_recipients:
        assert (
            recipients[row].index,
            recipients[row].recipient,
            recipients[row].personalisation,
        ) == (
            row,
            email,
            expected_personalisation[row],
        )


@pytest.mark.parametrize(
    "file_contents,template_type,expected,expected_missing",
    [
        (
            "", 'sms', [], set(['phone number', 'name'])
        ),
        (
            """
                phone number,name
                6502532222,test1
                6502532222,test1
                6502532222,test1
            """,
            'sms',
            ['phone number', 'name'],
            set()
        ),
        (
            """
                email address,name,colour
            """,
            'email',
            ['email address', 'name', 'colour'],
            set()
        ),
        (
            """
                address_line_1, address_line_2, postcode, name
            """,
            'letter',
            ['address_line_1', 'address_line_2', 'postcode', 'name'],
            set()
        ),
        (
            """
                email address,colour
            """,
            'email',
            ['email address', 'colour'],
            set(['name'])
        ),
        (
            """
                address_line_1, address_line_2, name
            """,
            'letter',
            ['address_line_1', 'address_line_2', 'name'],
            set(['postcode'])
        ),
        (
            """
                phone number,list,list,name,list
            """,
            'sms',
            ['phone number', 'list', 'name'],
            set()
        ),
    ]
)
def test_column_headers(file_contents, template_type, expected, expected_missing):
    recipients = RecipientCSV(file_contents, template_type=template_type, placeholders=['name'])
    assert recipients.column_headers == expected
    assert recipients.missing_column_headers == expected_missing
    assert recipients.has_errors == bool(expected_missing)


@pytest.mark.parametrize(
    'placeholders',
    [
        None,
        ['name']
    ]
)
@pytest.mark.parametrize(
    'file_contents,template_type',
    [
        pytest.param('', 'sms', marks=pytest.mark.xfail),
        pytest.param('name', 'sms', marks=pytest.mark.xfail),
        pytest.param('email address', 'sms', marks=pytest.mark.xfail),
        pytest.param(
            # missing postcode
            'address_line_1, address_line_2, address_line_3, address_line_4, address_line_5',
            'letter',
            marks=pytest.mark.xfail,
        ),
        ('phone number', 'sms'),
        ('phone number,name', 'sms'),
        ('email address', 'email'),
        ('email address,name', 'email'),
        ('PHONENUMBER', 'sms'),
        ('email_address', 'email'),
        (
            'address_line_1, address_line_2, postcode',
            'letter'
        ),
        (
            'address_line_1, address_line_2, address_line_3, address_line_4, address_line_5, address_line_6, postcode',
            'letter'
        ),
    ]
)
def test_recipient_column(placeholders, file_contents, template_type):
    assert RecipientCSV(file_contents, template_type=template_type, placeholders=placeholders).has_recipient_columns


@pytest.mark.parametrize(
    "file_contents,template_type,rows_with_bad_recipients,rows_with_missing_data",
    [
        (
            """
                phone number,name,date
                6502532222,test1,test1
                6502532222,test1
                +1 123,test1,test1
                6502532222,test1,test1
                6502532222,test1
                +1644000000,test1,test1
                ,test1,test1
            """,
            'sms',
            {2, 5}, {1, 4, 6}
        ),
        (
            """
                phone number,name
                6502532222,test1,test2
            """,
            'sms',
            set(), set()
        ),
        (
            """
            """,
            'sms',
            set(), set()
        ),
        (
            # missing postcode
            """
                address_line_1,address_line_2,address_line_3,address_line_4,address_line_5,postcode,date
                name,          building,      street,        town,          county,        postcode,today
                name,          building,      street,        town,          county,        ,        today
            """,
            'letter',
            set(), {1}
        ),
        (
            # only required address fields
            """
                address_line_1, postcode, date
                name,           postcode, today
            """,
            'letter',
            set(), set()
        ),
        (
            # optional address fields not filled in
            """
                address_line_1,address_line_2,address_line_3,address_line_4,address_line_5,postcode,date
                name          ,123 fake st.  ,              ,              ,              ,postcode,today
            """,
            'letter',
            set(), set()
        ),
    ]
)
@pytest.mark.parametrize('partial_instance', [
    partial(RecipientCSV),
    partial(RecipientCSV, international_sms=False),
])
def test_bad_or_missing_data(
    file_contents, template_type, rows_with_bad_recipients, rows_with_missing_data, partial_instance
):
    recipients = partial_instance(file_contents, template_type=template_type, placeholders=['date'])
    assert _index_rows(recipients.rows_with_bad_recipients) == rows_with_bad_recipients
    assert _index_rows(recipients.rows_with_missing_data) == rows_with_missing_data
    if rows_with_bad_recipients or rows_with_missing_data:
        assert recipients.has_errors is True


@pytest.mark.parametrize("file_contents,rows_with_bad_recipients", [
    (
        """
            phone number
            800000000000
            1234
            +17900123
        """,
        {0, 1, 2},
    ),
    (
        """
            phone number, country
            +2302086859, Mauritius
        """,
        set(),
    ),
])
def test_international_recipients(file_contents, rows_with_bad_recipients):
    recipients = RecipientCSV(file_contents, template_type='sms', international_sms=True)
    assert _index_rows(recipients.rows_with_bad_recipients) == rows_with_bad_recipients


def test_errors_when_too_many_rows():
    recipients = RecipientCSV(
        "email address\n" + ("a@b.com\n" * (50001)),
        template_type='email'
    )
    assert recipients.max_rows == 50000
    assert recipients.too_many_rows is True
    assert recipients.has_errors is True
    assert recipients.rows[49000]['email_address'].data == 'a@b.com'
    # We stop processing subsequent rows
    assert recipients.rows[50000] is None


@pytest.mark.parametrize(
    "file_contents,template_type,safelist,count_of_rows_with_errors",
    [
        (
            """
                phone number
                6502532222
                07700900461
                07700900462
                07700900463
            """,
            'sms',
            ['6502532222'],  # Same as first phone number but in different format
            3
        ),
        (
            """
                phone number
                6502532222
                +16502532222
                07700900462
            """,
            'sms',
            ['6502532222', '07700900461', '07700900462', '07700900463', 'test@example.com'],
            0
        ),
        (
            """
                email address
                IN_SAFELIST@EXAMPLE.COM
                not_in_safelist@example.com
            """,
            'email',
            ['in_safelist@example.com', '6502532222'],  # Email case differs to the one in the CSV
            1
        )
    ]
)
def test_recipient_safelist(file_contents, template_type, safelist, count_of_rows_with_errors):

    recipients = RecipientCSV(
        file_contents,
        template_type=template_type,
        safelist=safelist
    )

    if count_of_rows_with_errors:
        assert not recipients.allowed_to_send_to
    else:
        assert recipients.allowed_to_send_to

    # Make sure the safelist isn’t emptied by reading it. If it’s an iterator then
    # there’s a risk that it gets emptied after being read once
    recipients.safelist = (str(fake_number) for fake_number in range(7700900888, 7700900898))
    list(recipients.safelist)
    assert not recipients.allowed_to_send_to
    assert recipients.has_errors

    # An empty safelist is treated as no safelist at all
    recipients.safelist = []
    assert recipients.allowed_to_send_to
    recipients.safelist = itertools.chain()
    assert recipients.allowed_to_send_to


def test_detects_rows_which_result_in_overly_long_messages():
    template = SMSMessageTemplate(
        {'content': '((placeholder))', 'template_type': 'sms'},
        sender=None,
        prefix=None,
    )
    recipients = RecipientCSV(
        """
            phone number,placeholder
            6502532222,1
            6502532222,{one_under}
            6502532223,{exactly}
            6502532224,{one_over}
        """.format(
            one_under='a' * (SMS_CHAR_COUNT_LIMIT - 1),
            exactly='a' * SMS_CHAR_COUNT_LIMIT,
            one_over='a' * (SMS_CHAR_COUNT_LIMIT + 1),
        ),
        template_type=template.template_type,
        template=template
    )
    assert _index_rows(recipients.rows_with_errors) == {3}
    assert _index_rows(recipients.rows_with_message_too_long) == {3}
    assert recipients.has_errors


@pytest.mark.parametrize(
    "key, expected",
    sum([
        [(key, expected) for key in group] for expected, group in [
            ('6502532222', (
                'phone number',
                '   PHONENUMBER',
                'phone_number',
                'phone-number',
                'phoneNumber'
            )),
            ('Jo', (
                'FIRSTNAME',
                'first name',
                'first_name ',
                'first-name',
                'firstName'
            )),
            ('Bloggs', (
                'Last    Name',
                'LASTNAME',
                '    last_name',
                'last-name',
                'lastName   '
            ))
        ]
    ], [])
)
def test_ignores_spaces_and_case_in_placeholders(key, expected):
    recipients = RecipientCSV(
        """
            phone number,FIRSTNAME, Last Name
            6502532222, Jo, Bloggs
        """,
        placeholders=['phone_number', 'First Name', 'lastname'],
        template_type='sms'
    )
    first_row = recipients[0]
    assert first_row.get(key).data == expected
    assert first_row[key].data == expected
    assert first_row.recipient == '6502532222'
    assert len(first_row.items()) == 3
    assert not recipients.has_errors

    assert recipients.missing_column_headers == set()
    recipients.placeholders = {'one', 'TWO', 'Thirty_Three'}
    assert recipients.missing_column_headers == {'one', 'TWO', 'Thirty_Three'}
    assert recipients.has_errors


@pytest.mark.parametrize('character, name', (

    (' ', 'SPACE'),

    # these ones don’t have unicode names
    ('\n', None),  # newline
    ('\r', None),  # carriage return
    ('\t', None),  # tab

    ('\u180E', 'MONGOLIAN VOWEL SEPARATOR'),
    ('\u200B', 'ZERO WIDTH SPACE'),
    ('\u200C', 'ZERO WIDTH NON-JOINER'),
    ('\u200D', 'ZERO WIDTH JOINER'),
    ('\u2060', 'WORD JOINER'),
    ('\uFEFF', 'ZERO WIDTH NO-BREAK SPACE'),

    # all the things
    (' \n\r\t\u000A\u000D\u180E\u200B\u200C\u200D\u2060\uFEFF', None)

))
def test_ignores_leading_whitespace_in_file(character, name):

    if name is not None:
        assert unicodedata.name(character) == name

    recipients = RecipientCSV(
        '{}emailaddress\ntest@example.com'.format(character),
        template_type='email'
    )
    first_row = recipients[0]

    assert recipients.column_headers == ['emailaddress']
    assert recipients.recipient_column_headers == ['email address']
    assert recipients.missing_column_headers == set()
    assert recipients.placeholders == ['email address']

    assert first_row.get('email address').data == 'test@example.com'
    assert first_row['email address'].data == 'test@example.com'
    assert first_row.recipient == 'test@example.com'

    assert not recipients.has_errors


def test_error_if_too_many_recipients():
    recipients = RecipientCSV(
        'phone number,\n6502532222,\n6502532222,\n6502532222,',
        placeholders=['phone_number'],
        template_type='sms',
        remaining_messages=2
    )
    assert recipients.has_errors
    assert recipients.more_rows_than_can_send


def test_dont_error_if_too_many_recipients_not_specified():
    recipients = RecipientCSV(
        'phone number,\n6502532222,\n6502532222,\n6502532222,',
        placeholders=['phone_number'],
        template_type='sms'
    )
    assert not recipients.has_errors
    assert not recipients.more_rows_than_can_send


@pytest.mark.parametrize('index, expected_row', [
    (
        0,
        {
            'phone number': '07700 90000 1',
            'colour': 'red',
        },
    ),
    (
        1,
        {
            'phone_number': '07700 90000 2',
            'COLOUR': 'green',
        },
    ),
    (
        2,
        {
            'p h o n e  n u m b e r': '07700 90000 3',
            '   colour   ': 'blue'
        },
    ),
    pytest.param(
        3,
        {
            'phone number': 'foo'
        },
        marks=pytest.mark.xfail(raises=IndexError),
    ),
    (
        -1,
        {
            'p h o n e  n u m b e r': '07700 90000 3',
            '   colour   ': 'blue'
        },
    ),
])
def test_recipients_can_be_accessed_by_index(index, expected_row):
    recipients = RecipientCSV(
        """
            phone number, colour
            07700 90000 1, red
            07700 90000 2, green
            07700 90000 3, blue
        """,
        placeholders=['phone_number'],
        template_type='sms'
    )
    for key, value in expected_row.items():
        assert recipients[index][key].data == value


@pytest.mark.parametrize('international_sms', (True, False))
def test_multiple_sms_recipient_columns(international_sms):
    recipients = RecipientCSV(
        """
            phone number, phone number, phone_number, foo
            6502532222, 6502532223, 6502532224, bar
        """,
        template_type='sms',
        international_sms=international_sms,
    )
    assert recipients.column_headers == ['phone number', 'phone_number', 'foo']
    assert recipients.column_headers_as_column_keys == dict(phonenumber='', foo='').keys()
    assert recipients.rows[0].get('phone number').data == (
        '6502532224'
    )
    assert recipients.rows[0].get('phone number').error is None
    assert recipients.duplicate_recipient_column_headers == OrderedSet([
        'phone number', 'phone_number'
    ])
    assert recipients.has_errors


@pytest.mark.parametrize('column_name', (
    "phone_number", "phonenumber", "phone number", "phone-number", 'p h o n e  n u m b e r'
))
def test_multiple_sms_recipient_columns_with_missing_data(column_name):
    recipients = RecipientCSV(
        """
            names, phone number, {}
            "Joanna and Steve", 07900 900111
        """.format(column_name),
        template_type='sms',
        international_sms=True,
    )
    expected_column_headers = ['names', 'phone number']
    if column_name != "phone number":
        expected_column_headers.append(column_name)
    assert recipients.column_headers == expected_column_headers
    assert recipients.column_headers_as_column_keys == dict(phonenumber='', names='').keys()
    # A piece of weirdness uncovered: since rows are created before spaces in column names are normalised, when
    # there are duplicate recipient columns and there is data for only one of the columns, if the columns have the same
    # spacing, phone number data will be a list of this one phone number and None, while if the spacing style differs
    # between two duplicate column names, the phone number data will be None. If there are no duplicate columns
    # then our code finds the phone number well regardless of the spacing, so this should not affect our users.
    phone_number_data = None
    if column_name == "phone number":
        phone_number_data = ['07900 900111', None]
    assert recipients.rows[0]['phonenumber'].data == phone_number_data
    assert recipients.rows[0].get('phone number').error is None
    expected_duplicated_columns = ['phone number']
    if column_name != "phone number":
        expected_duplicated_columns.append(column_name)
    assert recipients.duplicate_recipient_column_headers == OrderedSet(expected_duplicated_columns)
    assert recipients.has_errors


def test_multiple_email_recipient_columns():
    recipients = RecipientCSV(
        """
            EMAILADDRESS, email_address, foo
            one@two.com,  two@three.com, bar
        """,
        template_type='email',
    )
    assert recipients.rows[0].get('email address').data == (
        'two@three.com'
    )
    assert recipients.rows[0].get('email address').error is None
    assert recipients.has_errors
    assert recipients.duplicate_recipient_column_headers == OrderedSet([
        'EMAILADDRESS', 'email_address'
    ])
    assert recipients.has_errors


def test_multiple_letter_recipient_columns():
    recipients = RecipientCSV(
        """
            address line 1, Address Line 2, address line 1, address_line_2
            1,2,3,4
        """,
        template_type='letter',
    )
    assert recipients.rows[0].get('addressline1').data == (
        '3'
    )
    assert recipients.rows[0].get('addressline1').error is None
    assert recipients.has_errors
    assert recipients.duplicate_recipient_column_headers == OrderedSet([
        'address line 1', 'Address Line 2', 'address line 1', 'address_line_2'
    ])
    assert recipients.has_errors


def test_displayed_rows_when_some_rows_have_errors():
    recipients = RecipientCSV(
        """
            email address, name
            a@b.com,
            a@b.com,
            a@b.com, My Name
            a@b.com,
            a@b.com,
        """,
        template_type='email',
        placeholders=['name'],
        max_errors_shown=3
    )

    assert len(list(recipients.displayed_rows)) == 3


def test_displayed_rows_when_there_are_no_rows_with_errors():
    recipients = RecipientCSV(
        """
            email address, name
            a@b.com, My Name
            a@b.com, My Name
            a@b.com, My Name
            a@b.com, My Name
        """,
        template_type='email',
        placeholders=['name'],
        max_errors_shown=3
    )

    assert len(list(recipients.displayed_rows)) == 4


def test_multi_line_placeholders_work():
    recipients = RecipientCSV(
        """
            email address, data
            a@b.com, "a\nb\n\nc"
        """,
        template_type='email',
        placeholders=['data']
    )

    assert recipients.rows[0].personalisation['data'] == 'a\nb\n\nc'
