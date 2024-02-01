import pytest

from notifications_utils.sanitise_text import SanitiseText, SanitiseSMS, SanitiseASCII


@pytest.mark.parametrize("chars, cls", [("ÀÂËÎÏÔŒÙÛâçêëîïôœû", SanitiseSMS)])
def test_encode_chars_sms_fr_not_downgraded(chars, cls):
    for char in chars:
        assert cls.encode_char(char) == char


params, ids = zip(
    (("a", "a"), "ascii char (a)"),
    # ascii control char (not in GSM)
    (("\t", " "), "ascii control char not in gsm (tab)"),
    # these unicode chars should change to something completely different for compatibility
    (("–", "-"), "compatibility transform unicode char (EN DASH (U+2013)"),
    (("—", "-"), "compatibility transform unicode char (EM DASH (U+2014)"),
    (("…", "..."), "compatibility transform unicode char (HORIZONTAL ELLIPSIS (U+2026)"),
    (("\u200B", ""), "compatibility transform unicode char (ZERO WIDTH SPACE (U+200B)"),
    (("‘", "'"), "compatibility transform unicode char (LEFT SINGLE QUOTATION MARK (U+2018)"),
    (("’", "'"), "compatibility transform unicode char (RIGHT SINGLE QUOTATION MARK (U+2019)"),
    (("“", '"'), "compatibility transform unicode char (LEFT DOUBLE QUOTATION MARK (U+201C)	"),
    (("”", '"'), "compatibility transform unicode char (RIGHT DOUBLE QUOTATION MARK (U+201D)"),
    (("\xa0", ""), "nobreak transform unicode char (NO-BREAK SPACE (U+00A0))"),
    # this unicode char is not decomposable
    (("😬", "?"), "undecomposable unicode char (grimace emoji)"),
    (("↉", "?"), "vulgar fraction (↉) that we do not try decomposing"),
)


@pytest.mark.parametrize("char, expected", params, ids=ids)
@pytest.mark.parametrize("cls", [SanitiseSMS, SanitiseASCII])
def test_encode_chars_the_same_for_ascii_and_sms(char, expected, cls):
    assert cls.encode_char(char) == expected


params, ids = zip(
    # ascii control chars are allowed in GSM but not in ASCII
    (("\n", "\n", "?"), "ascii control char in gsm (newline)"),
    (("\r", "\r", "?"), "ascii control char in gsm (return)"),
    # These characters are present in GSM but not in ascii
    (("à", "à", "a"), "non-ascii gsm char (a with accent)"),
    (("€", "€", "?"), "non-ascii gsm char (euro)"),
    # These characters are Welsh characters that are not present in GSM
    (("â", "â", "a"), "non-gsm Welsh char (a with hat)"),
    (("Ŷ", "Ŷ", "Y"), "non-gsm Welsh char (capital y with hat)"),
)

params_inuktitut = (
    ("ᐁ", "ᐁ"),
    ("ᐯ", "ᐯ"),
    ("ᑌ", "ᑌ"),
    ("ᑫ", "ᑫ"),
    ("ᕴ", "ᕴ"),
    ("ᒉ", "ᒉ"),
    ("ᒣ", "ᒣ"),
    ("ᓀ", "ᓀ"),
    ("ᓭ", "ᓭ"),
    ("ᓓ", "ᓓ"),
    ("ᔦ", "ᔦ"),
    ("ᑦ", "ᑦ"),
    ("ᔦ", "ᔦ"),
    ("ᕓ", "ᕓ"),
    ("ᕂ", "ᕂ"),
    ("ᙯ", "ᙯ"),
    ("ᖅ", "ᖅ"),
    ("ᑫ", "ᑫ"),
    ("ᙰ", "ᙰ"),
    ("ᐃ", "ᐃ"),
    ("ᐱ", "ᐱ"),
    ("ᑎ", "ᑎ"),
    ("ᑭ", "ᑭ"),
    ("ᕵ", "ᕵ"),
    ("ᒋ", "ᒋ"),
    ("ᒥ", "ᒥ"),
    ("ᓂ", "ᓂ"),
    ("ᓯ", "ᓯ"),
    ("\U00011ab6", "\U00011ab6"),
    ("\U00011ab0", "\U00011ab0"),
    ("ᓕ", "ᓕ"),
    ("ᔨ", "ᔨ"),
    ("ᑦ", "ᑦ"),
    ("ᔨ", "ᔨ"),
    ("ᖨ", "ᖨ"),
    ("ᕕ", "ᕕ"),
    ("ᕆ", "ᕆ"),
    ("ᕿ", "ᕿ"),
    ("ᖅ", "ᖅ"),
    ("ᑭ", "ᑭ"),
    ("ᖏ", "ᖏ"),
    ("ᙱ", "ᙱ"),
    ("ᖠ", "ᖠ"),
    ("ᐄ", "ᐄ"),
    ("ᐲ", "ᐲ"),
    ("ᑏ", "ᑏ"),
    ("ᑮ", "ᑮ"),
    ("ᕶ", "ᕶ"),
    ("ᒌ", "ᒌ"),
    ("ᒦ", "ᒦ"),
    ("ᓃ", "ᓃ"),
    ("ᓰ", "ᓰ"),
    ("\U00011ab7", "\U00011ab7"),
    ("\U00011ab1", "\U00011ab1"),
    ("ᓖ", "ᓖ"),
    ("ᔩ", "ᔩ"),
    ("ᑦ", "ᑦ"),
    ("ᔩ", "ᔩ"),
    ("ᖩ", "ᖩ"),
    ("ᕖ", "ᕖ"),
    ("ᕇ", "ᕇ"),
    ("ᖀ", "ᖀ"),
    ("ᖅ", "ᖅ"),
    ("ᑮ", "ᑮ"),
    ("ᖐ", "ᖐ"),
    ("ᙲ", "ᙲ"),
    ("ᖡ", "ᖡ"),
    ("ᐅ", "ᐅ"),
    ("ᐳ", "ᐳ"),
    ("ᑐ", "ᑐ"),
    ("ᑯ", "ᑯ"),
    ("ᕷ", "ᕷ"),
    ("ᒍ", "ᒍ"),
    ("ᒧ", "ᒧ"),
    ("ᓄ", "ᓄ"),
    ("ᓱ", "ᓱ"),
    ("\U00011ab8", "\U00011ab8"),
    ("\U00011ab2", "\U00011ab2"),
    ("ᓗ", "ᓗ"),
    ("ᔪ", "ᔪ"),
    ("ᑦ", "ᑦ"),
    ("ᔪ", "ᔪ"),
    ("ᖪ", "ᖪ"),
    ("ᕗ", "ᕗ"),
    ("ᕈ", "ᕈ"),
    ("ᖁ", "ᖁ"),
    ("ᖅ", "ᖅ"),
    ("ᑯ", "ᑯ"),
    ("ᖑ", "ᖑ"),
    ("ᙳ", "ᙳ"),
    ("ᖢ", "ᖢ"),
    ("ᐊ", "ᐊ"),
    ("ᐸ", "ᐸ"),
    ("ᑕ", "ᑕ"),
    ("ᑲ", "ᑲ"),
    ("ᕹ", "ᕹ"),
    ("ᒐ", "ᒐ"),
    ("ᒪ", "ᒪ"),
    ("ᓇ", "ᓇ"),
    ("ᓴ", "ᓴ"),
    ("\U00011aba", "\U00011aba"),
    ("\U00011ab4", "\U00011ab4"),
    ("ᓚ", "ᓚ"),
    ("ᔭ", "ᔭ"),
    ("ᑦ", "ᑦ"),
    ("ᔭ", "ᔭ"),
    ("ᖬ", "ᖬ"),
    ("ᕙ", "ᕙ"),
    ("ᕋ", "ᕋ"),
    ("ᖃ", "ᖃ"),
    ("ᖅ", "ᖅ"),
    ("ᑲ", "ᑲ"),
    ("ᖓ", "ᖓ"),
    ("ᙵ", "ᙵ"),
    ("ᖤ", "ᖤ"),
    ("ᑉ", "ᑉ"),
    ("ᑦ", "ᑦ"),
    ("ᒃ", "ᒃ"),
    ("ᕻ", "ᕻ"),
    ("ᒡ", "ᒡ"),
    ("ᒻ", "ᒻ"),
    ("ᓐ", "ᓐ"),
    ("ᔅ", "ᔅ"),
    ("ᓪ", "ᓪ"),
    ("ᔾ", "ᔾ"),
    ("ᑦ", "ᑦ"),
    ("ᔾ", "ᔾ"),
    ("ᖮ", "ᖮ"),
    ("ᕝ", "ᕝ"),
    ("ᕐ", "ᕐ"),
    ("ᖅ", "ᖅ"),
    ("ᖅ", "ᖅ"),
    ("ᒃ", "ᒃ"),
    ("ᖕ", "ᖕ"),
    ("ᖖ", "ᖖ"),
    ("ᖦ", "ᖦ"),
    ("ᖯ", "ᖯ"),
    ("ᕼ", "ᕼ"),
    ("ᑊ", "ᑊ"),
)


@pytest.mark.parametrize("char, expected_sms, expected_ascii", params, ids=ids)
def test_encode_chars_different_between_ascii_and_sms(char, expected_sms, expected_ascii):
    assert SanitiseSMS.encode_char(char) == expected_sms
    assert SanitiseASCII.encode_char(char) == expected_ascii


@pytest.mark.parametrize("char, expected", params_inuktitut)
def test_encode_chars_inuktitut_sms(char, expected):
    assert SanitiseSMS.encode_char(char) == expected


@pytest.mark.parametrize(
    "codepoint, char",
    [
        ("0041", "A"),
        ("0061", "a"),
    ],
)
def test_get_unicode_char_from_codepoint(codepoint, char):
    assert SanitiseText.get_unicode_char_from_codepoint(codepoint) == char


@pytest.mark.parametrize("bad_input", ["", "GJ", "00001", '0001";import sys;sys.exit(0)"'])
def test_get_unicode_char_from_codepoint_rejects_bad_input(bad_input):
    with pytest.raises(ValueError):
        SanitiseText.get_unicode_char_from_codepoint(bad_input)


@pytest.mark.parametrize(
    "content, expected",
    [
        ("Łódź", "?odz"),
        ("The quick brown fox jumps over the lazy dog", "The quick brown fox jumps over the lazy dog"),
    ],
)
def test_encode_string(content, expected):
    assert SanitiseSMS.encode(content) == expected
    assert SanitiseASCII.encode(content) == expected


@pytest.mark.parametrize(
    "content, cls, expected",
    [
        ("The quick brown fox jumps over the lazy dog", SanitiseSMS, set()),
        ("The “quick” brown fox has some downgradable characters\xa0", SanitiseSMS, set()),
        ("Need more 🐮🔔", SanitiseSMS, {"🐮", "🔔"}),
        ("Ŵêlsh chârâctêrs ârê cômpâtîblê wîth SanitiseSMS", SanitiseSMS, set()),
        ("Lots of GSM chars that arent ascii compatible:\n\r€", SanitiseSMS, set()),
        ("Lots of GSM chars that arent ascii compatible:\n\r€", SanitiseASCII, {"\n", "\r", "€"}),
    ],
)
def test_sms_encoding_get_non_compatible_characters(content, cls, expected):
    assert cls.get_non_compatible_characters(content) == expected
