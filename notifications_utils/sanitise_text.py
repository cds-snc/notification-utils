import unicodedata
from typing import Set


class SanitiseText:
    ALLOWED_CHARACTERS: Set = set()

    REPLACEMENT_CHARACTERS = {
        "–": "-",  # EN DASH (U+2013)
        "—": "-",  # EM DASH (U+2014)
        "…": "...",  # HORIZONTAL ELLIPSIS (U+2026)
        "‘": "'",  # LEFT SINGLE QUOTATION MARK (U+2018)
        "’": "'",  # RIGHT SINGLE QUOTATION MARK (U+2019)
        "“": '"',  # LEFT DOUBLE QUOTATION MARK (U+201C)
        "”": '"',  # RIGHT DOUBLE QUOTATION MARK (U+201D)
        "\u200b": "",  # ZERO WIDTH SPACE (U+200B)
        "\u00a0": "",  # NON BREAKING WHITE SPACE (U+200B)
        "\t": " ",  # TAB
    }

    @classmethod
    def encode(cls, content):
        return "".join(cls.encode_char(char) for char in content)

    @classmethod
    def get_non_compatible_characters(cls, content):
        """
        Given an input string, return a set of non compatible characters.

        This follows the same rules as `cls.encode`, but returns just the characters that encode would replace with `?`
        """
        return set(c for c in content if c not in cls.ALLOWED_CHARACTERS and cls.downgrade_character(c) is None)

    @staticmethod
    def get_unicode_char_from_codepoint(codepoint):
        """
        Given a unicode codepoint (eg 002E for '.', 0061 for 'a', etc), return that actual unicode character.

        unicodedata.decomposition returns strings containing codepoints, so we need to eval them ourselves
        """
        # lets just make sure we aren't evaling anything weird
        if not set(codepoint) <= set("0123456789ABCDEF") or not len(codepoint) == 4:
            raise ValueError("{} is not a valid unicode codepoint".format(codepoint))
        return eval('"\\u{}"'.format(codepoint))

    @classmethod
    def downgrade_character(cls, c):
        """
        Attempt to downgrade a non-compatible character to the allowed character set. May downgrade to multiple
        characters, eg `… -> ...`

        Will return None if character is either already valid or has no known downgrade
        """
        decomposed = unicodedata.decomposition(c)
        if decomposed != "" and "<" not in decomposed:
            # decomposition lists the unicode code points a character is made up of, if it's made up of multiple
            # points. For example the á character returns '0061 0301', as in, the character a, followed by a combining
            # acute accent. The decomposition might, however, also contain a decomposition mapping in angle brackets.
            # For a full list of the types, see here: https://www.compart.com/en/unicode/decomposition.
            # If it's got a mapping, we're not sure how best to downgrade it, so just see if it's in the
            # REPLACEMENT_CHARACTERS map. If not, then it's probably a letter with a modifier, eg á
            # ASSUMPTION: The first character of a combined unicode character (eg 'á' == '0061 0301')
            # will be the ascii char
            return cls.get_unicode_char_from_codepoint(decomposed.split()[0])
        else:
            # try and find a mapping (eg en dash -> hyphen ('–': '-')), else return None
            return cls.REPLACEMENT_CHARACTERS.get(c)

    @classmethod
    def encode_char(cls, c):
        """
        Given a single unicode character, return a compatible character from the allowed set.
        """
        # char is a good character already - return that native character.
        if c in cls.ALLOWED_CHARACTERS:
            return c
        else:
            c = cls.downgrade_character(c)
            return c if c is not None else "?"


class SanitiseSMS(SanitiseText):
    """
    Given an input string, makes it GSM and Welsh character compatible. This involves removing all non-gsm characters by
    applying the following rules
    * characters within the GSM character set (https://en.wikipedia.org/wiki/GSM_03.38)
      and extension character set are kept

    * Welsh characters not included in the default GSM character set are kept: Ââ Êê Îî Ôô Ûû Ŵŵ Ŷŷ

    * characters with sensible downgrades are replaced in place
        * characters with diacritics (accents, umlauts, cedillas etc) are replaced with their base character, eg é -> e
        * en dash and em dash (– and —) are replaced with hyphen (-)
        * left/right quotation marks (‘, ’, “, ”) are replaced with ' and "
        * zero width spaces (sometimes used to stop eg "gov.uk" linkifying) are removed
        * tabs are replaced with a single space

    * any remaining unicode characters (eg chinese/cyrillic/glyphs/emoji) are replaced with ?
    """

    # Welsh characters not already included in GSM
    WELSH_NON_GSM_CHARACTERS = set("ÂâÊêÎîÔôÛûŴŵŶŷ")
    FRENCH_NON_GSM_CHARACTERS = set("ÀÂËÎÏÔŒÙÛâçêëîïôœû")
    INUKTITUK_CHARACTERS = set(
        "ᐁᐯᑌᑫᕴᒉᒣᓀᓭᓓᔦᑦᔦᕓᕂᙯᖅᑫᙰᐃᐱᑎᑭᕵᒋᒥᓂᓯ𑪶𑪰ᓕᔨᑦᔨᖨᕕᕆᕿᖅᑭᖏᙱᖠᐄᐲᑏᑮᕶᒌᒦᓃᓰ𑪷𑪱ᓖᔩᑦᔩᖩᕖᕇᖀᖅᑮᖐᙲᖡᐅᐳᑐᑯᕷᒍᒧᓄᓱ𑪸𑪲ᓗᔪᑦᔪᖪᕗᕈᖁᖅᑯᖑᙳᖢᐊᐸᑕᑲᕹᒐᒪᓇᓴ𑪺𑪴ᓚᔭᑦᔭᖬᕙᕋᖃᖅᑲᖓᙵᖤᑉᑦᒃᕻᒡᒻᓐᔅᓪᔾᑦᔾᖮᕝᕐᖅᖅᒃᖕᖖᖦᖯᕼᑊ"  # noqa: E501
    )
    CREE_CHARACTERS = set("ᐊᐁᐃᐅᐸᐯᐱᐳᑕᑌᑎᑐᑲᑫᑭᑯᒐᒉᒋᒍᒪᒣᒥᒧᓇᓀᓂᓄᓴᓭᓯᓱᔭᔦᔨᔪ")
    OJIBWE_CHARACTERS = set(
        "ᐁᐃᐅᐊᐄᐆᐋᐊᐊᐞᐊᐊᐊᐦᐊᐊᐊᐊᐦᐊᐊᐞᐊᐯᐱᐳᐸᐲᐴᐹᐊᑉᐊᣔᑌᑎᑐᑕᑏᑑᑖᐊᑦᐊᣕᑫᑭᑯᑲᑮᑰᑳᐊᒃᐊᣖᒉᒋᒍᒐᒌᒎᒑᐊᒡᐊᣗᒣᒥᒧᒪᒦᒨᒫᐊᒻᐊᣘᐊᒻᐊᐊᣘᐊᓀᓂᓄᓇᓃᓅᓈᐊᓐᐊᣙᐊᓐᐊᐊᣙᐊᓭᓯᓱᓴᓰᓲᓵᐊᔅᐊᣚᐊᔅᐊᐊᣚᐊᔐᔑᔓᔕᔒᔔᔖᐊᔥᐊᣛᐊᔥᐊᐊᣛᐊᔦᔨᔪᔭᔩᔫᔮᐊᔾᐊᐤᐊᐃᐧᐁᐧᐃᐧᐅᐧᐊᐧᐄᐧᐆᐧᐋᐊᐤᐊᐤᐊᣜᐦᐁᐦᐃᐦᐅᐦᐊᐦᐄᐦᐆᐦᐋᐊᐦᐊᐦᐊᐦᐊᐊᐦᐊ"  # noqa: E501
    )

    ALLOWED_CHARACTERS = (
        set(
            "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
            + "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
            + "^{}\\[~]|€"  # character set extension
        )
        | WELSH_NON_GSM_CHARACTERS
        | FRENCH_NON_GSM_CHARACTERS
        | INUKTITUK_CHARACTERS
        | CREE_CHARACTERS
        | OJIBWE_CHARACTERS
    )


class SanitiseASCII(SanitiseText):
    """
    As SMS above, but the allowed characters are printable ascii, from character range 32 to 126 inclusive.
    [chr(x) for x in range(32, 127)]
    """

    ALLOWED_CHARACTERS = set(
        " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    )
