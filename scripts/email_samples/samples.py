"""
Sample email content and branding combinations used to render GC Notify emails
for visual review in different email clients.

Branding options mirror `get_html_email_options` in notification-api
(app/delivery/send_to_providers.py), so each sample matches what a real
service with that branding type would send.
"""

from dataclasses import dataclass, field
from typing import Any

DEFAULT_LOGO_URL = "https://assets.notification.canada.ca/canada-logo.png"
DEFAULT_BRAND_COLOUR = "#26374a"

PERSONALISATION = {
    "name": "Alex Tremblay",
    "reference": "ABC-123-456",
    "show_optional": "yes",
}


@dataclass(frozen=True)
class Content:
    subject: str
    body: str
    text_direction_rtl: bool = False


@dataclass(frozen=True)
class Branding:
    description: str
    options: dict[str, Any] = field(default_factory=dict)
    uses_logo: bool = False
    uses_colour: bool = False


@dataclass(frozen=True)
class Sample:
    content: str
    branding: str

    @property
    def name(self) -> str:
        return f"{self.content}--{self.branding}"


CONTENTS: dict[str, Content] = {
    "plain": Content(
        subject="Your application ((reference)) was received",
        body=(
            "Hello ((name)),\n\n"
            "We received your application ((reference)). We will contact you within 10 business days.\n\n"
            "If you have questions, visit https://www.canada.ca/en/contact.html\n\n"
            "Thank you,\n"
            "The Example Program team"
        ),
    ),
    "kitchen_sink": Content(
        subject="Every formatting option",
        body=(
            "# Heading level 1\n\n"
            "Hello ((name)), this paragraph has **bold text**, _emphasis_, a "
            "[descriptive link](https://www.canada.ca/en.html) and a bare link: https://www.canada.ca/en/services.html\n\n"
            "## Heading level 2\n\n"
            "A paragraph directly after a level 2 heading.\n"
            "This line follows a single line break.\n\n"
            "* First bullet point\n"
            "* Second bullet point that is long enough to wrap onto a second line on narrow mobile screens\n"
            "* Third bullet point with a [link](https://www.canada.ca/en.html)\n\n"
            "1. First numbered step\n"
            "2. Second numbered step that is long enough to wrap onto a second line on narrow mobile screens\n"
            "3. Third numbered step\n\n"
            "^ This is inset text. It is used to draw attention to important information, "
            "and is long enough to wrap onto several lines.\n\n"
            "---\n\n"
            "Text after a horizontal rule.\n\n"
            "((show_optional??This conditional text appears because show_optional is set.))\n\n"
            "Thank you,\n"
            "The Example Program team"
        ),
    ),
    "lists": Content(
        subject="List layouts",
        body=(
            "## A list straight after a heading\n"
            "* Bullet one\n"
            "* Bullet two\n\n"
            "Nested bullets:\n\n"
            "* Parent bullet\n"
            "    * Child bullet\n"
            "    * Another child bullet that is long enough to wrap onto a second line on narrow mobile screens\n"
            "* Second parent bullet\n\n"
            "Nested numbers:\n\n"
            "1. Parent step\n"
            "    1. Child step\n"
            "    2. Another child step\n"
            "2. Second parent step\n\n"
            "Mixed nesting:\n\n"
            "1. Numbered parent\n"
            "    * Bullet child\n"
            "    * Bullet child\n"
            "2. Numbered parent\n\n"
            "* A list using asterisks\n"
            "- A list using hyphens\n"
            "• A list using bullet characters\n\n"
            "A paragraph after the lists."
        ),
    ),
    "bilingual": Content(
        subject="Your application was received / Votre demande a été reçue",
        body=(
            "[[en]]\n"
            "# Your application was received\n\n"
            "Hello ((name)), we received your application.\n\n"
            "* Reference: ((reference))\n"
            "* Next step: we will contact you\n"
            "[[/en]]\n\n"
            "[[fr]]\n"
            "# Votre demande a été reçue\n\n"
            "Bonjour ((name)), nous avons reçu votre demande.\n\n"
            "* Référence : ((reference))\n"
            "* Prochaine étape : nous communiquerons avec vous\n"
            "[[/fr]]"
        ),
    ),
    "rtl_block": Content(
        subject="Right-to-left block inside a left-to-right email",
        body=(
            "English introduction before the right-to-left block.\n\n"
            "[[rtl]]\n"
            "# مرحبا ((name))\n\n"
            "تم استلام طلبك. سنتصل بك خلال ١٠ أيام عمل.\n\n"
            "* البند الأول\n"
            "* البند الثاني\n\n"
            "^ نص مهم\n"
            "[[/rtl]]\n\n"
            "English text after the right-to-left block."
        ),
    ),
    "rtl_template": Content(
        subject="قالب من اليمين إلى اليسار",
        body=(
            "# مرحبا ((name))\n\n"
            "تم استلام طلبك ((reference)). سنتصل بك خلال ١٠ أيام عمل.\n\n"
            "* البند الأول\n"
            "* البند الثاني\n\n"
            "1. الخطوة الأولى\n"
            "2. الخطوة الثانية\n\n"
            "^ نص مهم\n\n"
            "https://www.canada.ca/en.html"
        ),
        text_direction_rtl=True,
    ),
    "overflow": Content(
        subject="Long words, links and addresses",
        body=(
            "# Overflow and wrapping on small screens\n\n"
            "A long link: https://www.canada.ca/en/employment-social-development/services/my-account/"
            "very/long/path/with/many/segments/index.html?query=parameter&another=value\n\n"
            "A long unbroken token: ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
            "A long email address: firstname.lastname.with.extra.parts@department-of-example-services.gc.ca\n\n"
            "## Une très longue rubrique en français pour tester le retour à la ligne anticonstitutionnellement\n\n"
            "* A bullet with a long link: https://www.canada.ca/fr/emploi-developpement-social/services/mon-dossier.html\n"
        ),
    ),
}

BRANDINGS: dict[str, Branding] = {
    "fip_en": Branding(
        description="Default: Government of Canada signature, English first",
        options={"fip_banner_english": True, "fip_banner_french": False},
    ),
    "fip_fr": Branding(
        description="Default: Government of Canada signature, French first",
        options={"fip_banner_english": False, "fip_banner_french": True},
    ),
    "both_english": Branding(
        description="GC signature (English) plus a custom logo",
        options={"fip_banner_english": True, "fip_banner_french": False, "brand_name": "Example Department"},
        uses_logo=True,
    ),
    "both_french": Branding(
        description="GC signature (French) plus a custom logo",
        options={"fip_banner_english": False, "fip_banner_french": True, "brand_name": "Example Department"},
        uses_logo=True,
    ),
    "custom_logo": Branding(
        description="Custom logo only",
        options={"fip_banner_english": False, "brand_name": "Example Department"},
        uses_logo=True,
    ),
    "custom_logo_with_text": Branding(
        description="Custom logo with brand text and a brand colour accent",
        options={"fip_banner_english": False, "brand_name": "Example Department", "brand_text": "Example Department"},
        uses_logo=True,
        uses_colour=True,
    ),
    "custom_logo_with_background_colour": Branding(
        description="Custom logo and brand text on a coloured banner",
        options={
            "fip_banner_english": False,
            "logo_with_background_colour": True,
            "brand_name": "Example Department",
            "brand_text": "Example Department",
        },
        uses_logo=True,
        uses_colour=True,
    ),
    "no_branding": Branding(
        description="No branding",
        options={"fip_banner_english": False, "fip_banner_french": False},
    ),
}

# Every content sample with the default branding, then every other branding with
# plain content (branding only changes the header and footer). This keeps the set
# small enough to screenshot in many clients without paying for a full matrix.
SAMPLES: list[Sample] = [Sample(content, "fip_en") for content in CONTENTS] + [
    Sample("plain", branding) for branding in BRANDINGS if branding != "fip_en"
]
