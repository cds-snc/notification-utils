import datetime
from time import process_time
import os
import pytest

from functools import partial
from unittest import mock
from flask import Markup
from freezegun import freeze_time

from notifications_utils.formatters import unlink_govuk_escaped
from notifications_utils.template import (
    Template,
    HTMLEmailTemplate,
    LetterPreviewTemplate,
    LetterImageTemplate,
    PlainTextEmailTemplate,
    SMSMessageTemplate,
    SMSPreviewTemplate,
    WithSubjectTemplate,
    EmailPreviewTemplate,
    LetterPrintTemplate,
)


def test_pass_through_renderer():
    message = '''
        the
        quick brown
        fox
    '''
    assert str(Template({'content': message})) == message


def test_html_email_inserts_body():
    assert 'the &lt;em&gt;quick&lt;/em&gt; brown fox' in str(HTMLEmailTemplate(
        {'content': 'the <em>quick</em> brown fox', 'subject': ''}
    ))


@pytest.mark.parametrize(
    "content", ('DOCTYPE', 'html', 'body', 'hello world')
)
def test_default_template(content):
    assert content in str(HTMLEmailTemplate({'content': 'hello world', 'subject': ''}))


@pytest.mark.parametrize(
    "show_banner", (True, False)
)
def test_govuk_banner(show_banner):
    email = HTMLEmailTemplate({'content': 'hello world', 'subject': ''})
    email.govuk_banner = show_banner
    if show_banner:
        assert "sig-blk-en.png" in str(email)
    else:
        assert "sig-blk-en.png" not in str(email)


def test_brand_banner_shows():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        brand_banner=True,
        govuk_banner=False
    ))
    assert (
        '<td width="10" height="10" valign="middle"></td>'
    ) not in email
    assert (
        'role="presentation" width="100%" style="border-collapse: collapse;min-width: 100%;width: 100% !important;"'
    ) in email


@pytest.mark.parametrize(
    "brand_logo, brand_text, brand_colour",
    [
        ('http://example.com/image.png', 'Example', 'red'),
        ('http://example.com/image.png', 'Example', '#f00'),
        ('http://example.com/image.png', 'Example', None),
        ('http://example.com/image.png', '', '#f00'),
        (None, 'Example', '#f00')
    ]
)
def test_brand_data_shows(brand_logo, brand_text, brand_colour):
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        brand_banner=True,
        govuk_banner=False,
        brand_logo=brand_logo,
        brand_text=brand_text,
        brand_colour=brand_colour
    ))

    assert 'GOV.UK' not in email
    if brand_logo:
        assert brand_logo in email
    if brand_text:
        assert brand_text in email
    if brand_colour:
        assert 'bgcolor="{}"'.format(brand_colour) in email


def test_alt_text_with_brand_text_and_govuk_banner_shown():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        govuk_banner=True,
        brand_logo='http://example.com/image.png',
        brand_text='Example',
        brand_banner=True,
        brand_name='Notify Logo'
    ))
    assert 'alt=" "' in email
    assert 'alt="Notify Logo"' not in email


def test_alt_text_with_no_brand_text_and_govuk_banner_shown():
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        govuk_banner=True,
        brand_logo='http://example.com/image.png',
        brand_text=None,
        brand_banner=True,
        brand_name='Notify Logo'
    ))
    assert 'alt=" "' in email
    assert 'alt="Notify Logo"' in email


@pytest.mark.parametrize('brand_banner, brand_text, expected_alt_text', [
    (True, None, 'alt="Notify Logo"'),
    (True, 'Example', 'alt=" "'),
    (False, 'Example', 'alt=" "'),
    (False, None, 'alt="Notify Logo"'),
])
def test_alt_text_with_no_govuk_banner(brand_banner, brand_text, expected_alt_text):
    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        govuk_banner=False,
        brand_logo='http://example.com/image.png',
        brand_text=brand_text,
        brand_banner=brand_banner,
        brand_name='Notify Logo'
    ))

    assert expected_alt_text in email


@pytest.mark.parametrize(
    "complete_html", (True, False)
)
@pytest.mark.parametrize(
    "branding_should_be_present, brand_logo, brand_text, brand_colour",
    [
        (True, 'http://example.com/image.png', 'Example', '#f00'),
        (True, 'http://example.com/image.png', 'Example', None),
        (True, 'http://example.com/image.png', '', None),
        (False, None, 'Example', '#f00'),
        (False, 'http://example.com/image.png', None, '#f00')
    ]
)
@pytest.mark.parametrize(
    "content", ('DOCTYPE', 'html', 'body')
)
def test_complete_html(complete_html, branding_should_be_present, brand_logo, brand_text, brand_colour, content):

    email = str(HTMLEmailTemplate(
        {'content': 'hello world', 'subject': ''},
        complete_html=complete_html,
        brand_logo=brand_logo,
        brand_text=brand_text,
        brand_colour=brand_colour,
    ))

    if complete_html:
        assert content in email
    else:
        assert content not in email

    if branding_should_be_present:
        assert brand_logo in email
        assert brand_text in email

        if brand_colour:
            assert brand_colour in email
            assert '##' not in email


def test_preheader_is_at_start_of_html_emails():
    assert (
        '<body style="font-family: Helvetica, Arial, sans-serif;font-size: 16px;margin: 0;color:#0b0c0c;">\n'
        '\n'
        '<span style="display: none;font-size: 1px;color: #fff; max-height: 0;">content…</span>'
    ) in str(
        HTMLEmailTemplate({'content': 'content', 'subject': 'subject'})
    )


@pytest.mark.parametrize('content, values, expected_preheader', [
    (
        (
            'Hello (( name ))\n'
            '\n'
            '# This - is a "heading"\n'
            '\n'
            'My favourite websites\' URLs are:\n'
            '- GOV.UK\n'
            '- https://www.example.com\n'
        ),
        {'name': 'Jo'},
        'Hello Jo This – is a “heading” My favourite websites’ URLs are: • GOV.​UK • https://www.example.com',
    ),
    (
        """
            Lorem Ipsum is simply dummy text of the printing and
            typesetting industry.

            Lorem Ipsum has been the industry’s standard dummy text
            ever since the 1500s, when an unknown printer took a galley
            of type and scrambled it to make a type specimen book.

            Lorem Ipsum is simply dummy text of the printing and
            typesetting industry.

            Lorem Ipsum has been the industry’s standard dummy text
            ever since the 1500s, when an unknown printer took a galley
            of type and scrambled it to make a type specimen book.
        """,
        {},
        (
            'Lorem Ipsum is simply dummy text of the printing and '
            'typesetting industry. Lorem Ipsum has been the industry’s '
            'standard dummy text ever since the 1500s, when an unknown '
            'printer took a galley of type and scrambled it to make a '
            'type specimen book. Lorem Ipsu'
        ),
    ),
    (
        'short email',
        {},
        'short email',
    ),
])
@mock.patch(
    'notifications_utils.template.HTMLEmailTemplate.jinja_template.render',
    return_value='mocked'
)
def test_content_of_preheader_in_html_emails(
    mock_jinja_template,
    content,
    values,
    expected_preheader,
):
    assert str(HTMLEmailTemplate(
        {'content': content, 'subject': 'subject'},
        values
    )) == 'mocked'
    assert mock_jinja_template.call_args[0][0]['preheader'] == expected_preheader


@pytest.mark.parametrize('template_class, extra_args, result, markdown_renderer', [
    [
        HTMLEmailTemplate,
        {},
        (
            'the quick brown fox\n'
            '\n'
            'jumped over the lazy dog\n'
        ),
        'notifications_utils.template.notify_email_markdown',
    ],
    [
        LetterPreviewTemplate,
        {},
        (
            'the quick brown fox\n'
            '\n'
            'jumped over the lazy dog\n'
        ),
        'notifications_utils.template.notify_letter_preview_markdown'
    ],
])
def test_markdown_in_templates(
    template_class,
    extra_args,
    result,
    markdown_renderer,
):
    with mock.patch(markdown_renderer, return_value='') as mock_markdown_renderer:
        str(template_class(
            {
                "content": (
                    'the quick ((colour)) ((animal))\n'
                    '\n'
                    'jumped over the lazy dog'
                ),
                'subject': 'animal story'
            },
            {'animal': 'fox', 'colour': 'brown'},
            **extra_args
        ))
    mock_markdown_renderer.assert_called_once_with(result)


@pytest.mark.parametrize(
    'template_class', [
        HTMLEmailTemplate,
        EmailPreviewTemplate,
        SMSPreviewTemplate,
    ]
)
@pytest.mark.parametrize(
    "url, url_with_entities_replaced", [
        ("http://example.com", "http://example.com"),
        ("http://www.gov.uk/", "http://www.gov.uk/"),
        ("https://www.gov.uk/", "https://www.gov.uk/"),
        ("http://service.gov.uk", "http://service.gov.uk"),
        (
            "http://service.gov.uk/blah.ext?q=a%20b%20c&order=desc#fragment",
            "http://service.gov.uk/blah.ext?q=a%20b%20c&amp;order=desc#fragment",
        ),
        pytest.param("example.com", "example.com", marks=pytest.mark.xfail),
        pytest.param("www.example.com", "www.example.com", marks=pytest.mark.xfail),
        pytest.param(
            "http://service.gov.uk/blah.ext?q=one two three",
            "http://service.gov.uk/blah.ext?q=one two three",
            marks=pytest.mark.xfail,
        ),
        pytest.param("ftp://example.com", "ftp://example.com", marks=pytest.mark.xfail),
        pytest.param("mailto:test@example.com", "mailto:test@example.com", marks=pytest.mark.xfail),
    ]
)
def test_makes_links_out_of_URLs(template_class, url, url_with_entities_replaced):
    assert '<a style="word-wrap: break-word; color: #005ea5;" href="{}">{}</a>'.format(
        url_with_entities_replaced, url_with_entities_replaced
    ) in str(template_class({'content': url, 'subject': ''}))


@pytest.mark.parametrize('content, html_snippet', (
    (
        (
            'You’ve been invited to a service. Click this link:\n'
            'https://service.example.com/accept_invite/a1b2c3d4\n'
            '\n'
            'Thanks\n'
        ),
        (
            '<a style="word-wrap: break-word; color: #005ea5;"'
            ' href="https://service.example.com/accept_invite/a1b2c3d4">'
            'https://service.example.com/accept_invite/a1b2c3d4'
            '</a>'
        ),
    ),
    (
        (
            'https://service.example.com/accept_invite/?a=b&c=d&'
        ),
        (
            '<a style="word-wrap: break-word; color: #005ea5;"'
            ' href="https://service.example.com/accept_invite/?a=b&amp;c=d&amp;">'
            'https://service.example.com/accept_invite/?a=b&amp;c=d&amp;'
            '</a>'
        ),
    ),
))
def test_HTML_template_has_URLs_replaced_with_links(content, html_snippet):
    assert html_snippet in str(HTMLEmailTemplate({'content': content, 'subject': ''}))


@pytest.mark.parametrize(
    "template_content,expected", [
        ("gov.uk", u"gov.\u200Buk"),
        ("GOV.UK", u"GOV.\u200BUK"),
        ("Gov.uk", u"Gov.\u200Buk"),
        ("https://gov.uk", "https://gov.uk"),
        ("https://www.gov.uk", "https://www.gov.uk"),
        ("www.gov.uk", "www.gov.uk"),
        ("gov.uk/register-to-vote", "gov.uk/register-to-vote"),
        ("gov.uk?q=", "gov.uk?q=")
    ]
)
def test_escaping_govuk_in_email_templates(template_content, expected):
    assert unlink_govuk_escaped(template_content) == expected
    assert expected in str(PlainTextEmailTemplate({'content': template_content, 'subject': ''}))
    assert expected in str(HTMLEmailTemplate({'content': template_content, 'subject': ''}))


def test_stripping_of_unsupported_characters_in_email_templates():
    template_content = "line one\u2028line two"
    expected = "line oneline two"
    assert expected in str(PlainTextEmailTemplate({'content': template_content, 'subject': ''}))
    assert expected in str(HTMLEmailTemplate({'content': template_content, 'subject': ''}))


@mock.patch('notifications_utils.template.add_prefix', return_value='')
@pytest.mark.parametrize(
    "template_class, prefix, body, expected_call", [
        (SMSMessageTemplate, "a", "b", (Markup("b"), "a")),
        (SMSPreviewTemplate, "a", "b", (Markup("b"), "a")),
        (SMSMessageTemplate, None, "b", (Markup("b"), None)),
        (SMSPreviewTemplate, None, "b", (Markup("b"), None)),
        (SMSMessageTemplate, '<em>ht&ml</em>', "b", (Markup("b"), '<em>ht&ml</em>')),
        (SMSPreviewTemplate, '<em>ht&ml</em>', "b", (Markup("b"), '&lt;em&gt;ht&amp;ml&lt;/em&gt;')),
    ]
)
def test_sms_message_adds_prefix(add_prefix, template_class, prefix, body, expected_call):
    template = template_class({'content': body})
    template.prefix = prefix
    template.sender = None
    str(template)
    add_prefix.assert_called_once_with(*expected_call)


@mock.patch('notifications_utils.template.add_prefix', return_value='')
@pytest.mark.parametrize(
    'template_class', [SMSMessageTemplate, SMSPreviewTemplate]
)
@pytest.mark.parametrize(
    "show_prefix, prefix, body, sender, expected_call", [
        (False, "a", "b", "c", (Markup("b"), None)),
        (True, "a", "b", None, (Markup("b"), "a")),
        (True, "a", "b", False, (Markup("b"), "a")),
    ]
)
def test_sms_message_adds_prefix_only_if_asked_to(
    add_prefix,
    show_prefix,
    prefix,
    body,
    sender,
    expected_call,
    template_class,
):
    template = template_class(
        {'content': body},
        prefix=prefix,
        show_prefix=show_prefix,
        sender=sender,
    )
    str(template)
    add_prefix.assert_called_once_with(*expected_call)


@pytest.mark.parametrize('content_to_look_for', [
    'GOVUK', 'sms-message-sender'
])
@pytest.mark.parametrize("show_sender", [
    True,
    pytest.param(False, marks=pytest.mark.xfail),
])
def test_sms_message_preview_shows_sender(
    show_sender,
    content_to_look_for,
):
    assert content_to_look_for in str(SMSPreviewTemplate(
        {'content': 'foo'},
        sender='GOVUK',
        show_sender=show_sender,
    ))


def test_sms_message_preview_hides_sender_by_default():
    assert SMSPreviewTemplate({'content': 'foo'}).show_sender is False


@mock.patch('notifications_utils.template.sms_encode', return_value='downgraded')
@pytest.mark.parametrize(
    'template_class', [SMSMessageTemplate, SMSPreviewTemplate]
)
def test_sms_messages_downgrade_non_sms(mock_sms_encode, template_class):
    template = str(template_class({'content': 'Message'}, prefix='Service name'))
    assert 'downgraded' in str(template)
    mock_sms_encode.assert_called_once_with('Service name: Message')


@mock.patch('notifications_utils.template.sms_encode', return_value='downgraded')
def test_sms_messages_dont_downgrade_non_sms_if_setting_is_false(mock_sms_encode):
    template = str(SMSPreviewTemplate(
        {'content': '😎'},
        prefix='👉',
        downgrade_non_sms_characters=False,
    ))
    assert '👉: 😎' in str(template)
    assert mock_sms_encode.called is False


@mock.patch('notifications_utils.template.nl2br')
def test_sms_preview_adds_newlines(nl2br):
    content = "the\nquick\n\nbrown fox"
    str(SMSPreviewTemplate({'content': content}))
    nl2br.assert_called_once_with(content)


@pytest.mark.parametrize('content', [
    (  # Unix-style
        'one newline\n'
        'two newlines\n'
        '\n'
        'end'
    ),
    (  # Windows-style
        'one newline\r\n'
        'two newlines\r\n'
        '\r\n'
        'end'
    ),
    (  # Mac Classic style
        'one newline\r'
        'two newlines\r'
        '\r'
        'end'
    ),
    (  # A mess
        '\t\t\n\r one newline\xa0\n'
        'two newlines\r'
        '\r\n'
        'end\n\n  \r \n \t '
    ),
])
def test_sms_message_normalises_newlines(content):
    assert repr(str(SMSMessageTemplate({'content': content}))) == repr(
        'one newline\n'
        'two newlines\n'
        '\n'
        'end'
    )


@freeze_time("2012-12-12 12:12:12")
@mock.patch('notifications_utils.template.LetterPreviewTemplate.jinja_template.render')
@mock.patch('notifications_utils.template.remove_empty_lines', return_value='123 Street')
@mock.patch('notifications_utils.template.unlink_govuk_escaped')
@mock.patch('notifications_utils.template.notify_letter_preview_markdown', return_value='Bar')
@mock.patch('notifications_utils.template.strip_pipes', side_effect=lambda x: x)
@pytest.mark.parametrize('values, expected_address', [
    ({}, Markup(
        "<span class='placeholder-no-brackets'>address line 1</span>\n"
        "<span class='placeholder-no-brackets'>address line 2</span>\n"
        "<span class='placeholder-no-brackets'>address line 3</span>\n"
        "<span class='placeholder-no-brackets'>address line 4</span>\n"
        "<span class='placeholder-no-brackets'>address line 5</span>\n"
        "<span class='placeholder-no-brackets'>address line 6</span>\n"
        "<span class='placeholder-no-brackets'>postcode</span>"
    )),
    ({
        'address line 1': '123 Fake Street',
        'address line 6': 'United Kingdom',
    }, Markup(
        "123 Fake Street\n"
        "<span class='placeholder-no-brackets'>address line 2</span>\n"
        "<span class='placeholder-no-brackets'>address line 3</span>\n"
        "<span class='placeholder-no-brackets'>address line 4</span>\n"
        "<span class='placeholder-no-brackets'>address line 5</span>\n"
        "United Kingdom\n"
        "<span class='placeholder-no-brackets'>postcode</span>"
    )),
    ({
        'address line 1': '123 Fake Street',
        'address line 2': 'City of Town',
        'postcode': 'SW1A 1AA',
    }, Markup(
        "123 Fake Street\n"
        "City of Town\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "SW1A 1AA"
    ))
])
@pytest.mark.parametrize('contact_block, expected_rendered_contact_block', [
    (
        None,
        ''
    ),
    (
        '',
        ''
    ),
    (
        """
            The Pension Service
            Mail Handling Site A
            Wolverhampton  WV9 1LU

            Telephone: 0845 300 0168
            Email: fpc.customercare@dwp.gsi.gov.uk
            Monday - Friday  8am - 6pm
            www.gov.uk
        """,
        (
            'The Pension Service<br>'
            'Mail Handling Site A<br>'
            'Wolverhampton  WV9 1LU<br>'
            '<br>'
            'Telephone: 0845 300 0168<br>'
            'Email: fpc.customercare@dwp.gsi.gov.uk<br>'
            'Monday - Friday  8am - 6pm<br>'
            'www.gov.uk'
        )
    )
])
@pytest.mark.parametrize('extra_args, expected_logo_file_name, expected_logo_class', [
    ({}, None, None),
    ({'logo_file_name': 'example.foo'}, 'example.foo', 'foo'),
])
@pytest.mark.parametrize('additional_extra_args, expected_date', [
    ({}, '12 December 2012'),
    ({'date': None}, '12 December 2012'),
    ({'date': datetime.date.fromtimestamp(0)}, '1 January 1970'),
])
def test_letter_preview_renderer(
    strip_pipes,
    letter_markdown,
    unlink_govuk,
    remove_empty_lines,
    jinja_template,
    values,
    expected_address,
    contact_block,
    expected_rendered_contact_block,
    extra_args,
    expected_logo_file_name,
    expected_logo_class,
    additional_extra_args,
    expected_date,
):
    extra_args.update(additional_extra_args)
    str(LetterPreviewTemplate(
        {'content': 'Foo', 'subject': 'Subject'},
        values,
        contact_block=contact_block,
        **extra_args
    ))
    remove_empty_lines.assert_called_once_with(expected_address)
    jinja_template.assert_called_once_with({
        'address': '<ul><li>123 Street</li></ul>',
        'subject': 'Subject',
        'message': 'Bar',
        'date': expected_date,
        'contact_block': expected_rendered_contact_block,
        'admin_base_url': 'http://localhost:6012',
        'logo_file_name': expected_logo_file_name,
        'logo_class': expected_logo_class,
    })
    letter_markdown.assert_called_once_with(Markup('Foo\n'))
    unlink_govuk.assert_not_called()
    assert strip_pipes.call_args_list == [
        mock.call('Subject'),
        mock.call('Foo'),
        mock.call(expected_address),
        mock.call(expected_rendered_contact_block),
    ]


@freeze_time("2001-01-01 12:00:00.000000")
@mock.patch('notifications_utils.template.LetterPreviewTemplate.jinja_template.render')
def test_letter_preview_renderer_without_mocks(jinja_template):

    str(LetterPreviewTemplate(
        {'content': 'Foo', 'subject': 'Subject'},
        {'addressline1': 'name', 'addressline2': 'street', 'postcode': 'SW1 1AA'},
        contact_block='',
    ))

    jinja_template_locals = jinja_template.call_args_list[0][0][0]

    assert jinja_template_locals['address'] == (
        '<ul>'
        '<li>name</li>'
        '<li>street</li>'
        '<li>SW1 1AA</li>'
        '</ul>'
    )
    assert jinja_template_locals['subject'] == 'Subject'
    assert jinja_template_locals['message'] == "<p>Foo</p>"
    assert jinja_template_locals['date'] == '1 January 2001'
    assert jinja_template_locals['contact_block'] == ''
    assert jinja_template_locals['admin_base_url'] == 'http://localhost:6012'
    assert jinja_template_locals['logo_file_name'] is None


@freeze_time("2012-12-12 12:12:12")
@mock.patch('notifications_utils.template.LetterImageTemplate.jinja_template.render')
@pytest.mark.parametrize('page_count, expected_oversized, expected_page_numbers', [
    (
        1, False,
        [1],
    ),
    (
        5, False,
        [1, 2, 3, 4, 5],
    ),
    (
        10, False,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    ),
    (
        11, True,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    ),
    (
        99, True,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    ),
])
@pytest.mark.parametrize('postage_args, expected_postage', (
    pytest.param({}, 'second'),
    pytest.param({'postage': 'first'}, 'first'),
    pytest.param({'postage': 'second'}, 'second'),
    pytest.param({'postage': 'third'}, 'third', marks=pytest.mark.xfail(raises=TypeError)),
))
def test_letter_image_renderer(
    jinja_template,
    page_count,
    expected_page_numbers,
    expected_oversized,
    postage_args,
    expected_postage,
):
    str(LetterImageTemplate(
        {'content': 'Content', 'subject': 'Subject'},
        image_url='http://example.com/endpoint.png',
        page_count=page_count,
        contact_block='10 Downing Street',
        **postage_args
    ))
    jinja_template.assert_called_once_with({
        'image_url': 'http://example.com/endpoint.png',
        'page_numbers': expected_page_numbers,
        'too_many_pages': expected_oversized,
        'address': (
            "<ul>"
            "<li><span class='placeholder-no-brackets'>address line 1</span></li>"
            "<li><span class='placeholder-no-brackets'>address line 2</span></li>"
            "<li><span class='placeholder-no-brackets'>address line 3</span></li>"
            "<li><span class='placeholder-no-brackets'>address line 4</span></li>"
            "<li><span class='placeholder-no-brackets'>address line 5</span></li>"
            "<li><span class='placeholder-no-brackets'>address line 6</span></li>"
            "<li><span class='placeholder-no-brackets'>postcode</span></li>"
            "</ul>"
        ),
        'contact_block': '10 Downing Street',
        'date': '12 December 2012',
        'subject': 'Subject',
        'message': '<p>Content</p>',
        'postage': expected_postage,
    })


@pytest.mark.parametrize('page_image_url', [
    pytest.param('http://example.com/endpoint.png?page=0', marks=pytest.mark.xfail),
    'http://example.com/endpoint.png?page=1',
    'http://example.com/endpoint.png?page=2',
    'http://example.com/endpoint.png?page=3',
    pytest.param('http://example.com/endpoint.png?page=4', marks=pytest.mark.xfail),
])
def test_letter_image_renderer_pagination(page_image_url):
    assert page_image_url in str(LetterImageTemplate(
        {'content': '', 'subject': ''},
        image_url='http://example.com/endpoint.png',
        page_count=3,
    ))


@pytest.mark.parametrize('partial_call, expected_exception', [
    (
        partial(LetterImageTemplate),
        TypeError
    ),
    (
        partial(LetterImageTemplate, page_count=1),
        TypeError
    ),
    (
        partial(LetterImageTemplate, image_url='foo'),
        TypeError
    ),
    (
        partial(LetterImageTemplate, image_url='foo', page_count='foo'),
        ValueError
    ),
])
def test_letter_image_renderer_requires_arguments(partial_call, expected_exception):
    with pytest.raises(expected_exception):
        partial_call({'content': '', 'subject': ''})


def test_sets_subject():
    assert WithSubjectTemplate({"content": '', 'subject': 'Your tax is due'}).subject == 'Your tax is due'


def test_subject_line_gets_applied_to_correct_template_types():
    for cls in [
        EmailPreviewTemplate,
        HTMLEmailTemplate,
        PlainTextEmailTemplate,
        LetterPreviewTemplate,
        LetterImageTemplate,
    ]:
        assert issubclass(cls, WithSubjectTemplate)
    for cls in [
        SMSMessageTemplate,
        SMSPreviewTemplate,
    ]:
        assert not issubclass(cls, WithSubjectTemplate)


def test_subject_line_gets_replaced():
    template = WithSubjectTemplate({"content": '', 'subject': '((name))'})
    assert template.subject == Markup("<span class='placeholder'>((name))</span>")
    template.values = {'name': 'Jo'}
    assert template.subject == 'Jo'


@pytest.mark.parametrize('template_class, extra_args, expected_field_calls', [
    (Template, {}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=False),
    ]),
    (WithSubjectTemplate, {}, [
        mock.call('content', {}, html='passthrough', redact_missing_personalisation=False, markdown_lists=True),
    ]),
    (PlainTextEmailTemplate, {}, [
        mock.call('content', {}, html='passthrough', markdown_lists=True)
    ]),
    (HTMLEmailTemplate, {}, [
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=False),
        mock.call('content', {}, html='escape', markdown_lists=True),
    ]),
    (EmailPreviewTemplate, {}, [
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=False),
        mock.call('subject', {}, html='escape', redact_missing_personalisation=False),
        mock.call('((email address))', {}, with_brackets=False),
    ]),
    (SMSMessageTemplate, {}, [
        mock.call('content', {}, html='passthrough'),
    ]),
    (SMSPreviewTemplate, {}, [
        mock.call('((phone number))', {}, with_brackets=False, html='escape'),
        mock.call('content', {}, html='escape', redact_missing_personalisation=False),
    ]),
    (LetterPreviewTemplate, {'contact_block': 'www.gov.uk'}, [
        mock.call('subject', {}, html='escape', redact_missing_personalisation=False),
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=False),
        mock.call((
            '((address line 1))\n'
            '((address line 2))\n'
            '((address line 3))\n'
            '((address line 4))\n'
            '((address line 5))\n'
            '((address line 6))\n'
            '((postcode))'
        ), {}, with_brackets=False, html='escape'),
        mock.call('www.gov.uk', {}, html='escape', redact_missing_personalisation=False),
    ]),
    (LetterImageTemplate, {
        'image_url': 'http://example.com', 'page_count': 1, 'contact_block': 'www.gov.uk'
    }, [
        mock.call((
            '((address line 1))\n'
            '((address line 2))\n'
            '((address line 3))\n'
            '((address line 4))\n'
            '((address line 5))\n'
            '((address line 6))\n'
            '((postcode))'
        ), {}, with_brackets=False, html='escape'),
        mock.call('www.gov.uk', {}, html='escape', redact_missing_personalisation=False),
        mock.call('subject', {}, html='escape', redact_missing_personalisation=False),
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=False),
    ]),
    (Template, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='escape', redact_missing_personalisation=True),
    ]),
    (WithSubjectTemplate, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='passthrough', redact_missing_personalisation=True, markdown_lists=True),
    ]),
    (EmailPreviewTemplate, {'redact_missing_personalisation': True}, [
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=True),
        mock.call('subject', {}, html='escape', redact_missing_personalisation=True),
        mock.call('((email address))', {}, with_brackets=False),
    ]),
    (SMSPreviewTemplate, {'redact_missing_personalisation': True}, [
        mock.call('((phone number))', {}, with_brackets=False, html='escape'),
        mock.call('content', {}, html='escape', redact_missing_personalisation=True),
    ]),
    (LetterPreviewTemplate, {'contact_block': 'www.gov.uk', 'redact_missing_personalisation': True}, [
        mock.call('subject', {}, html='escape', redact_missing_personalisation=True),
        mock.call('content', {}, html='escape', markdown_lists=True, redact_missing_personalisation=True),
        mock.call((
            '((address line 1))\n'
            '((address line 2))\n'
            '((address line 3))\n'
            '((address line 4))\n'
            '((address line 5))\n'
            '((address line 6))\n'
            '((postcode))'
        ), {}, with_brackets=False, html='escape'),
        mock.call('www.gov.uk', {}, html='escape', redact_missing_personalisation=True),
    ]),
])
@mock.patch('notifications_utils.template.Field.__init__', return_value=None)
@mock.patch('notifications_utils.template.Field.__str__', return_value='1\n2\n3\n4\n5\n6\n7\n8')
def test_templates_handle_html_and_redacting(
    mock_field_str,
    mock_field_init,
    template_class,
    extra_args,
    expected_field_calls,
):
    assert str(template_class({'content': 'content', 'subject': 'subject'}, **extra_args))
    assert mock_field_init.call_args_list == expected_field_calls


@pytest.mark.parametrize('template_class, extra_args, expected_remove_whitespace_calls', [
    (PlainTextEmailTemplate, {}, [
        mock.call('\n\ncontent'),
        mock.call(Markup('subject')),
        mock.call(Markup('subject')),
    ]),
    (HTMLEmailTemplate, {}, [
        mock.call(
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
            'content'
            '</p>'
        ),
        mock.call('\n\ncontent'),
        mock.call(Markup('subject')),
        mock.call(Markup('subject')),
    ]),
    (EmailPreviewTemplate, {}, [
        mock.call(
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
            'content'
            '</p>'
        ),
        mock.call(Markup('subject')),
        mock.call(Markup('subject')),
        mock.call(Markup('subject')),
    ]),
    (SMSMessageTemplate, {}, [
        mock.call('content'),
    ]),
    (SMSPreviewTemplate, {}, [
        mock.call('content'),
    ]),
    (LetterPreviewTemplate, {'contact_block': 'www.gov.uk'}, [
        mock.call(Markup('subject')),
        mock.call(Markup('<p>content</p>')),
        mock.call((
            "<span class='placeholder-no-brackets'>address line 1</span>\n"
            "<span class='placeholder-no-brackets'>address line 2</span>\n"
            "<span class='placeholder-no-brackets'>address line 3</span>\n"
            "<span class='placeholder-no-brackets'>address line 4</span>\n"
            "<span class='placeholder-no-brackets'>address line 5</span>\n"
            "<span class='placeholder-no-brackets'>address line 6</span>\n"
            "<span class='placeholder-no-brackets'>postcode</span>"
        )),
        mock.call(Markup('www.gov.uk')),
        mock.call(Markup('subject')),
        mock.call(Markup('subject')),
    ]),
])
@mock.patch('notifications_utils.template.remove_whitespace_before_punctuation', side_effect=lambda x: x)
def test_templates_remove_whitespace_before_punctuation(
    mock_remove_whitespace,
    template_class,
    extra_args,
    expected_remove_whitespace_calls,
):
    template = template_class({'content': 'content', 'subject': 'subject'}, **extra_args)

    assert str(template)

    if hasattr(template, 'subject'):
        assert template.subject

    assert mock_remove_whitespace.call_args_list == expected_remove_whitespace_calls


@pytest.mark.parametrize('template_class, extra_args, expected_calls', [
    (PlainTextEmailTemplate, {}, [
        mock.call('\n\ncontent'),
        mock.call(Markup('subject')),
    ]),
    (HTMLEmailTemplate, {}, [
        mock.call(
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
            'content'
            '</p>'
        ),
        mock.call('\n\ncontent'),
        mock.call(Markup('subject')),
    ]),
    (EmailPreviewTemplate, {}, [
        mock.call(
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">'
            'content'
            '</p>'
        ),
        mock.call(Markup('subject')),
    ]),
    (SMSMessageTemplate, {}, [
    ]),
    (SMSPreviewTemplate, {}, [
    ]),
    (LetterPreviewTemplate, {'contact_block': 'www.gov.uk'}, [
        mock.call(Markup('subject')),
        mock.call(Markup('<p>content</p>')),
    ]),
])
@mock.patch('notifications_utils.template.make_quotes_smart', side_effect=lambda x: x)
@mock.patch('notifications_utils.template.replace_hyphens_with_en_dashes', side_effect=lambda x: x)
def test_templates_make_quotes_smart_and_dashes_en(
    mock_en_dash_replacement,
    mock_smart_quotes,
    template_class,
    extra_args,
    expected_calls,
):
    template = template_class({'content': 'content', 'subject': 'subject'}, **extra_args)

    assert str(template)

    if hasattr(template, 'subject'):
        assert template.subject

    mock_smart_quotes.assert_has_calls(expected_calls)
    mock_en_dash_replacement.assert_has_calls(expected_calls)


@pytest.mark.parametrize('content', (
    "first.o'last@example.com",
    "first.o’last@example.com",
))
@pytest.mark.parametrize('template_class', (
    HTMLEmailTemplate,
    PlainTextEmailTemplate,
    EmailPreviewTemplate,
))
def test_no_smart_quotes_in_email_addresses(template_class, content):
    template = template_class({
        'content': content,
        'subject': content,
    })
    assert "first.o'last@example.com" in str(template)
    assert template.subject == "first.o'last@example.com"


def test_smart_quotes_removed_from_long_template_in_under_a_second():
    long_string = 'a' * 100000
    template = PlainTextEmailTemplate({'content': long_string, 'subject': ''})

    start_time = process_time()

    str(template)

    assert process_time() - start_time < 1


def test_basic_templates_return_markup():

    template_dict = {'content': 'content', 'subject': 'subject'}

    for output in [
        str(Template(template_dict)),
        str(WithSubjectTemplate(template_dict)),
        WithSubjectTemplate(template_dict).subject,
    ]:
        assert isinstance(output, Markup)


@pytest.mark.parametrize('template_instance, expected_placeholders', [
    (
        SMSMessageTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content'],
    ),
    (
        SMSPreviewTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content'],
    ),
    (
        PlainTextEmailTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
    (
        HTMLEmailTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
    (
        EmailPreviewTemplate(
            {"content": "((content))", "subject": "((subject))"},
        ),
        ['content', 'subject'],
    ),
    (
        LetterPreviewTemplate(
            {"content": "((content))", "subject": "((subject))"},
            contact_block='((contact_block))',
        ),
        ['content', 'subject', 'contact_block'],
    ),
    (
        LetterImageTemplate(
            {"content": "((content))", "subject": "((subject))"},
            contact_block='((contact_block))',
            image_url='http://example.com',
            page_count=99,
        ),
        ['content', 'subject', 'contact_block'],
    ),
])
def test_templates_extract_placeholders(
    template_instance,
    expected_placeholders,
):
    assert template_instance.placeholders == set(expected_placeholders)


@pytest.mark.parametrize('extra_args', [
    {
        'from_name': 'Example service'
    },
    {
        'from_name': 'Example service',
        'from_address': 'test@example.com',
    },
    pytest.param({}, marks=pytest.mark.xfail),
])
def test_email_preview_shows_from_name(extra_args):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        **extra_args
    )
    assert '<th>From</th>' in str(template)
    assert 'Example service' in str(template)
    assert 'test@example.com' not in str(template)


def test_email_preview_escapes_html_in_from_name():
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        from_name='<script>alert("")</script>',
        from_address='test@example.com',
    )
    assert '<script>' not in str(template)
    assert '&lt;script&gt;alert("")&lt;/script&gt;' in str(template)


@pytest.mark.parametrize('extra_args', [
    {
        'reply_to': 'test@example.com'
    },
    pytest.param({}, marks=pytest.mark.xfail),
])
def test_email_preview_shows_reply_to_address(extra_args):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        **extra_args
    )
    assert '<th>Reply&nbsp;to</th>' in str(template)
    assert 'test@example.com' in str(template)


@pytest.mark.parametrize('template_values, expected_content', [
    (
        {},
        '<span class=\'placeholder-no-brackets\'>email address</span>'
    ),
    (
        {'email address': 'test@example.com'},
        'test@example.com'
    ),
])
def test_email_preview_shows_recipient_address(
    template_values,
    expected_content,
):
    template = EmailPreviewTemplate(
        {'content': 'content', 'subject': 'subject'},
        template_values,
    )
    assert expected_content in str(template)


@mock.patch('notifications_utils.template.strip_dvla_markup', return_value='FOOBARBAZ')
def test_letter_preview_strips_dvla_markup(mock_strip_dvla_markup):
    assert 'FOOBARBAZ' in str(LetterPreviewTemplate(
        {
            "content": 'content',
            'subject': 'subject',
        },
    ))
    assert mock_strip_dvla_markup.call_args_list == [
        mock.call(Markup('subject')),
        mock.call('content'),
    ]


dvla_file_spec = [
    {
        'Field number': '1',
        'Field name': 'OTT',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': """
            Current assumption is a single OTT for Notify = 140
            141 has also been reserved for future use
        """,
        'Example': '140',
    },
    {
        'Field number': '2',
        'Field name': 'ORG-ID',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': 'Unique identifier for the sending organisation',
        'Example': '500',
    },
    {
        'Field number': '3',
        'Field name': 'ORG-NOTIFICATION-TYPE',
        'Mandatory': 'Y',
        'Data type': 'N3',
        'Comment': """
            Identifies the specific letter type for this organisation
        """,
        'Example': '001',
    },
    {
        'Field number': '4',
        'Field name': 'ORG-NAME',
        'Mandatory': 'Y',
        'Data type': 'A90',
        'Comment': """
            Free text organisation name which appears under the
            crest in large font

            Not used by Notify
        """,
        'Example': '',
    },
    {
        'Field number': '5',
        'Field name': 'NOTIFICATION-ID',
        'Mandatory': 'Y',
        'Data type': 'A15',
        'Comment': """
            Unique identifier for each notification consisting of
            the current date and a numeric counter that resets each
            day.  Supports a maximum of 10 million notification
            events per day. Format:
                CCYYMMDDNNNNNNN
            Where:
                CCYY = Current year
                MMDD = Current month and year (zero padded)
                NNNNNNN = Daily counter (zero padded to 7 digits)
        """,
        'Example': 'reference',
    },
    {
        'Field number': '6',
        'Field name': 'NOTIFICATION-DATE',
        'Mandatory': 'Y',
        'Data type': 'A8',
        'Comment': """
            The date that will be shown on the notification Provided
            in format': 'DDMMYYYY This will be formatted to a long
            date format by the composition process

            Not used by Notify

            Given example was: 29042016
        """,
        'Example': '',
    },
    {
        'Field number': '7',
        'Field name': 'CUSTOMER-REFERENCE',
        'Mandatory': '',
        'Data type': 'A30',
        'Comment': """
            Full text of customer\'s reference

            Not implemented by Notify yet.

            Given example was:
                Our ref: 1234-5678
        """,
        'Example': '',
    },
    {
        'Field number': '8',
        'Field name': 'ADDITIONAL-LINE-1',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': """
            In the example templates this information appears in the
            footer in a small font.   These lines are free text,
            they may contain an address, e.g. of originating
            department, E9 but this will not be validated or used as
            a return address.
        """,
        'Example': 'The Pension Service',
    },
    {
        'Field number': '9',
        'Field name': 'ADDITIONAL-LINE-2',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Mail Handling Site A',
    },
    {
        'Field number': '10',
        'Field name': 'ADDITIONAL-LINE-3',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Wolverhampton  WV9 1LU',
    },
    {
        'Field number': '11',
        'Field name': 'ADDITIONAL-LINE-4',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': 'Deliberate blank line',
        'Example': '',
    },
    {
        'Field number': '12',
        'Field name': 'ADDITIONAL-LINE-5',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Telephone: 0845 300 0168',
    },
    {
        'Field number': '13',
        'Field name': 'ADDITIONAL-LINE-6',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Email: fpc.customercare@dwp.gsi.gov.uk',
    },
    {
        'Field number': '14',
        'Field name': 'ADDITIONAL-LINE-7',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'Monday - Friday  8am - 6pm',
    },
    {
        'Field number': '15',
        'Field name': 'ADDITIONAL-LINE-8',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': 'www.gov.uk',
    },
    {
        'Field number': '16',
        'Field name': 'ADDITIONAL-LINE-9',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '17',
        'Field name': 'ADDITIONAL-LINE-10',
        'Mandatory': '',
        'Data type': 'A50',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '18',
        'Field name': 'TO-NAME-1',
        'Mandatory': 'Y',
        'Data type': 'A60',
        'Comment': """
            Recipient full name includes title Must be present -
            validated by Notify
        """,
        'Example': 'Mr Henry Hadlow',
    },
    {
        'Field number': '19',
        'Field name': 'TO-NAME-2',
        'Mandatory': '',
        'Data type': 'A40',
        'Comment': """
            Additional name or title line

            Not able to pass this through at the moment

            Given example was: Managing Director
        """,
        'Example': '',
    },
    {
        'Field number': '20',
        'Field name': 'TO-ADDRESS-LINE-1',
        'Mandatory': 'Y',
        'Data type': 'A35',
        'Comment': """
            Must be present - PAF validation by Notify Must match
            PAF (in combination with TO-POST-CODE) to maximise
            postage discount
        """,
        'Example': '123 Electric Avenue',
    },
    {
        'Field number': '21',
        'Field name': 'TO-ADDRESS-LINE-2',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Address lines 2 through 5 are optional Composition
            process will remove blank address lines
        """,
        'Example': 'Great Yarmouth',
    },
    {
        'Field number': '22',
        'Field name': 'TO-ADDRESS-LINE-3',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': 'Norfolk',
    },
    {
        'Field number': '23',
        'Field name': 'TO-ADDRESS-LINE-4',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '24',
        'Field name': 'TO-ADDRESS-LINE-5',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '25',
        'Field name': 'TO-POST-CODE',
        'Mandatory': 'Y',
        'Data type': 'A8',
        'Comment': """,
            Unformatted (ie. SA6 7JL not SA067JL) Must be present -
            PAF validation by Notify Must match PAF (in combination
            with TO-ADDRESS-LINE-1) to maximise postage discount
        """,
        'Example': 'NR1 5PQ',
    },
    {
        'Field number': '26',
        'Field name': 'RETURN-NAME',
        'Mandatory': '',
        'Data type': 'A40',
        'Comment': """
            This section added to handle return of undelivered mail
            to a specific organisational address may be required in
            a later release of the service.

            Not used by Notify at the moment.

            Given example:
                DWP Pension Service
        """,
        'Example': '',
    },
    {
        'Field number': '27',
        'Field name': 'RETURN-ADDRESS-LINE-1',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                Mail Handling Site A
        """,
        'Example': '',
    },
    {
        'Field number': '28',
        'Field name': 'RETURN-ADDRESS-LINE-2',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                Wolverhampton
        """,
        'Example': '',
    },
    {
        'Field number': '29',
        'Field name': 'RETURN-ADDRESS-LINE-3',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '30',
        'Field name': 'RETURN-ADDRESS-LINE-4',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '31',
        'Field name': 'RETURN-ADDRESS-LINE-5',
        'Mandatory': '',
        'Data type': 'A35',
        'Comment': '',
        'Example': '',
    },
    {
        'Field number': '32',
        'Field name': 'RETURN-POST-CODE',
        'Mandatory': '',
        'Data type': 'A8',
        'Comment': """
            Not used by Notify at the moment.

            Given example:
                WV9 1LU
        """,
        'Example': '',
    },
    {
        'Field number': '33',
        'Field name': 'SUBJECT-LINE',
        'Mandatory': '',
        'Data type': 'A120',
        'Comment': """
            Not used by Notify any more, passed in the body

            Your application is due soon
        """,
        'Example': '',
    },
    {
        'Field number': '34',
        'Field name': 'NOTIFICATION-BODY',
        'Mandatory': '',
        'Data type': 'A',
        'Comment': """
            Difficult to define a maximum length as dependent on
            other formatting factors absolute maximum for OSG is 6
            pages but ideally no more than 4 pages total. OSG to
            confirm approach to mark up and line breaks...
        """,
        'Example': (
            '29 April 2016<cr><cr>'
            '<h1>Your application is something & something<normal><cr><cr>'
            'Dear Henry Hadlow,<cr><cr>'
            'Thank you for applying to register a lasting power of '
            'attorney (LPA) for property and financial affairs. We '
            'have checked your application and...<cr><cr>'
        ),
    }
]


@pytest.mark.parametrize("address, expected", [
    (
        {
            "address line 1": "line 1",
            "address line 2": "line 2",
            "address line 3": "line 3",
            "address line 4": "line 4",
            "address line 5": "line 5",
            "address line 6": "line 6",
            "postcode": "N1 4W2",
        },
        {
            "addressline1": "line 1",
            "addressline2": "line 2",
            "addressline3": "line 3",
            "addressline4": "line 4",
            "addressline5": "line 5",
            "addressline6": "line 6",
            "postcode": "N1 4W2",
        },
    ), (
        {
            "addressline1": "line 1",
            "addressline2": "line 2",
            "addressline3": "line 3",
            "addressline4": "line 4",
            "addressline5": "line 5",
            "addressLine6": "line 6",
            "postcode": "N1 4W2",
        },
        {
            "addressline1": "line 1",
            "addressline2": "line 2",
            "addressline3": "line 3",
            "addressline4": "line 4",
            "addressline5": "line 5",
            "addressline6": "line 6",
            "postcode": "N1 4W2",
        },
    ),
    (
        {
            "addressline1": "line 1",
            "addressline3": "line 3",
            "addressline5": "line 5",
            "addressline6": "line 6",
            "postcode": "N1 4W2",
        },
        {
            "addressline1": "line 1",
            # addressline2 is required, but not given
            "addressline3": "line 3",
            "addressline4": "",
            "addressline5": "line 5",
            "addressline6": "line 6",
            "postcode": "N1 4W2",
        },
    ),
    (
        {
            "addressline1": "line 1",
            "addressline2": "line 2",
            "addressline3": None,
            "addressline6": None,
            "postcode": "N1 4W2",
        },
        {
            "addressline1": "line 1",
            "addressline2": "line 2",
            "addressline3": "",
            "addressline4": "",
            "addressline5": "",
            "addressline6": "",
            "postcode": "N1 4W2",
        },
    ),
    (
        {
            "addressline1": "line 1",
            "addressline2": "\t     ,",
            "postcode": "N1 4W2",
        },
        {
            "addressline1": "line 1",
            "addressline2": "\t     ,",
            "addressline3": "",
            "addressline4": "",
            "addressline5": "",
            "addressline6": "",
            "postcode": "N1 4W2",
        },
    ),
])
def test_letter_address_format(address, expected):
    template = LetterPreviewTemplate(
        {'content': '', 'subject': ''},
        address,
    )
    assert template.values_with_default_optional_address_lines == expected
    # check that we can actually build a valid letter from this data
    assert str(template)


@freeze_time("2001-01-01 12:00:00.000000")
@pytest.mark.parametrize('markdown, expected', [
    (
        (
            'Here is a list of bullets:\n'
            '\n'
            '* one\n'
            '* two\n'
            '* three\n'
            '\n'
            'New paragraph'
        ),
        (
            '<ul>\n'
            '<li>one</li>\n'
            '<li>two</li>\n'
            '<li>three</li>\n'
            '</ul>\n'
            '<p>New paragraph</p>\n'
        )
    ),
    (
        (
            '# List title:\n'
            '\n'
            '* one\n'
            '* two\n'
            '* three\n'
        ),
        (
            '<h2>List title:</h2>\n'
            '<ul>\n'
            '<li>one</li>\n'
            '<li>two</li>\n'
            '<li>three</li>\n'
            '</ul>\n'
        )
    ),
    (
        (
            'Here’s an ordered list:\n'
            '\n'
            '1. one\n'
            '2. two\n'
            '3. three\n'
        ),
        (
            '<p>Here’s an ordered list:</p><ol>\n'
            '<li>one</li>\n'
            '<li>two</li>\n'
            '<li>three</li>\n'
            '</ol>'
        )
    ),
])
def test_lists_in_combination_with_other_elements_in_letters(markdown, expected):
    assert expected in str(LetterPreviewTemplate(
        {'content': markdown, 'subject': 'Hello'},
        {},
    ))


@pytest.mark.parametrize('template_class', [
    SMSMessageTemplate,
    SMSPreviewTemplate,
])
def test_message_too_long(template_class):
    body = ('b' * 400) + '((foo))'
    template = template_class({'content': body}, prefix='a' * 100, values={'foo': 'c' * 200})
    assert template.is_message_too_long() is True


@pytest.mark.parametrize('template_class, kwargs', [
    (EmailPreviewTemplate, {}),
    (HTMLEmailTemplate, {}),
    (PlainTextEmailTemplate, {}),
    (LetterPreviewTemplate, {}),
    (LetterImageTemplate, {'image_url': 'foo', 'page_count': 1}),
])
def test_non_sms_ignores_message_too_long(template_class, kwargs):
    body = 'a' * 1000
    template = template_class({'content': body, 'subject': 'foo'}, **kwargs)
    assert template.is_message_too_long() is False


@pytest.mark.parametrize(
    (
        'content,'
        'expected_preview_markup,'
    ), [
        (
            'a\n\n\nb',
            (
                '<p>a</p>'
                '<p>b</p>'
            ),
        ),
        (
            (
                'a\n'
                '\n'
                '* one\n'
                '* two\n'
                '* three\n'
                'and a half\n'
                '\n'
                '\n'
                '\n'
                '\n'
                'foo'
            ),
            (
                '<p>a</p><ul>\n'
                '<li>one</li>\n'
                '<li>two</li>\n'
                '<li>three<br>and a half</li>\n'
                '</ul>\n'
                '<p>foo</p>'
            ),
        ),
    ]
)
def test_multiple_newlines_in_letters(
    content,
    expected_preview_markup,
):
    assert expected_preview_markup in str(LetterPreviewTemplate(
        {'content': content, 'subject': 'foo'}
    ))


@pytest.mark.parametrize('subject', [
    ' no break ',
    ' no\tbreak ',
    '\tno break\t',
    'no \r\nbreak',
    'no \nbreak',
    'no \rbreak',
    '\rno break\n',
])
@pytest.mark.parametrize('template_class, extra_args', [
    (PlainTextEmailTemplate, {}),
    (HTMLEmailTemplate, {}),
    (EmailPreviewTemplate, {}),
    (LetterPreviewTemplate, {}),
])
def test_whitespace_in_subjects(template_class, subject, extra_args):

    template_instance = template_class(
        {'content': 'foo', 'subject': subject},
        **extra_args
    )
    assert template_instance.subject == 'no break'


@pytest.mark.parametrize('template_class, expected_output', [
    (
        PlainTextEmailTemplate,
        'paragraph one\n\n\xa0\n\nparagraph two',
    ),
    (
        HTMLEmailTemplate,
        (
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">paragraph one</p>'
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">&nbsp;</p>'
            '<p style="Margin: 0 0 20px 0; font-size: 19px; line-height: 25px; color: #0B0C0C;">paragraph two</p>'
        ),
    ),
])
def test_govuk_email_whitespace_hack(template_class, expected_output):

    template_instance = template_class({
        'content': 'paragraph one\n\n&nbsp;\n\nparagraph two',
        'subject': 'foo'
    })
    assert expected_output in str(template_instance)


def test_letter_preview_uses_non_breaking_hyphens():
    assert 'non\u2011breaking' in str(LetterPreviewTemplate(
        {'content': 'non-breaking', 'subject': 'foo'}
    ))
    assert '–' in str(LetterPreviewTemplate(
        {'content': 'en dash - not hyphen - when set with spaces', 'subject': 'foo'}
    ))


@freeze_time("2001-01-01 12:00:00.000000")
def test_nested_lists_in_lettr_markup():

    template_content = str(LetterPreviewTemplate({
        'content': (
            'nested list:\n'
            '\n'
            '1. one\n'
            '2. two\n'
            '3. three\n'
            '  - three one\n'
            '  - three two\n'
            '  - three three\n'
        ),
        'subject': 'foo',
    }))

    assert (
        '      <p>\n'
        '        1 January 2001\n'
        '      </p>\n'
        '      <h1>\n'
        '        foo\n'
        '      </h1>\n'
        '      <p>nested list:</p><ol>\n'
        '<li>one</li>\n'
        '<li>two</li>\n'
        '<li>three<ul>\n'
        '<li>three one</li>\n'
        '<li>three two</li>\n'
        '<li>three three</li>\n'
        '</ul></li>\n'
        '</ol>\n'
        '\n'
        '    </div>\n'
        '  </body>\n'
        '</html>'
    ) in template_content


def test_that_print_template_is_the_same_as_preview():
    assert dir(LetterPreviewTemplate) == dir(LetterPrintTemplate)
    assert os.path.basename(LetterPreviewTemplate.jinja_template.filename) == 'preview.jinja2'
    assert os.path.basename(LetterPrintTemplate.jinja_template.filename) == 'print.jinja2'


def test_plain_text_email_whitespace():
    email = PlainTextEmailTemplate({'subject': 'foo', 'content': (
        '# Heading\n'
        '\n'
        '1. one\n'
        '2. two\n'
        '3. three\n'
        '\n'
        '***\n'
        '\n'
        '# Heading\n'
        '\n'
        'Paragraph\n'
        '\n'
        'Paragraph\n'
        '\n'
        '^ callout\n'
        '\n'
        '1. one not four\n'
        '1. two not five'
    )})
    assert str(email) == (
        'Heading\n'
        '-----------------------------------------------------------------\n'
        '\n'
        '1. one\n'
        '2. two\n'
        '3. three\n'
        '\n'
        '=================================================================\n'
        '\n'
        '\n'
        'Heading\n'
        '-----------------------------------------------------------------\n'
        '\n'
        'Paragraph\n'
        '\n'
        'Paragraph\n'
        '\n'
        'callout\n'
        '\n'
        '1. one not four\n'
        '2. two not five\n'
    )


@pytest.mark.parametrize('renderer, expected_content', (
    (PlainTextEmailTemplate, (
        'Heading link: https://example.com\n'
        '-----------------------------------------------------------------\n'
    )),
    (HTMLEmailTemplate, (
        '<h2 style="Margin: 0 0 20px 0; padding: 0; font-size: 27px; '
        'line-height: 35px; font-weight: bold; color: #0B0C0C;">'
        'Heading <a style="word-wrap: break-word; color: #005ea5;" href="https://example.com">link</a>'
        '</h2>'
    )),
    (LetterPreviewTemplate, (
        '<h2>Heading link: <strong>example.com</strong></h2>'
    )),
    (LetterPrintTemplate, (
        '<h2>Heading link: <strong>example.com</strong></h2>'
    )),
))
def test_heading_only_template_renders(renderer, expected_content):
    assert expected_content in str(renderer({'subject': 'foo', 'content': (
        '# Heading [link](https://example.com)'
    )}))


@pytest.mark.parametrize("template_class", [
    LetterPreviewTemplate,
    LetterPrintTemplate,
])
@pytest.mark.parametrize("filename, expected_html_class", [
    ('example.png', 'class="png"'),
    ('example.svg', 'class="svg"'),
])
def test_image_class_applied_to_logo(template_class, filename, expected_html_class):
    assert expected_html_class in str(template_class(
        {'content': 'Foo', 'subject': 'Subject'},
        logo_file_name=filename,
    ))


@pytest.mark.parametrize("template_class", [
    LetterPreviewTemplate,
    LetterPrintTemplate,
])
def test_image_not_present_if_no_logo(template_class):
    # can't test that the html doesn't move in utils - tested in template preview instead
    assert '<img' not in str(template_class({'content': 'Foo', 'subject': 'Subject'}, logo_file_name=None))
