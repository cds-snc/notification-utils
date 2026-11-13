import pytest
from bs4 import BeautifulSoup
from notifications_utils.field import Field
from notifications_utils.template import HTMLEmailTemplate, PlainTextEmailTemplate, WithSubjectTemplate, get_html_email_body


@pytest.fixture
def image_values():
    return {
        "chart": {
            "document": {
                "sending_method": "attach",
                "inline_image": {"content_id": "chart-123", "alt_text": 'Usage <chart> & "description"'},
            }
        }
    }


def test_inline_image_is_opt_in(image_values):
    template = {"content": "Your chart:\n\n((chart))", "subject": "Usage"}
    assert 'src="cid:' not in str(HTMLEmailTemplate(template, values=image_values))
    html = BeautifulSoup(str(HTMLEmailTemplate(template, values=image_values, enable_inline_images=True)), "html.parser")
    image = html.find("img", src="cid:chart-123")
    assert image is not None
    assert image["alt"] == 'Usage <chart> & "description"'
    assert html.find("chart") is None


@pytest.mark.parametrize("display_size", [None, "responsive", "original"])
def test_inline_image_display_size(image_values, display_size):
    if display_size is not None:
        image_values["chart"]["document"]["inline_image"]["display_size"] = display_size
    html = BeautifulSoup(str(get_html_email_body("((chart))", image_values, enable_inline_images=True)), "html.parser")
    style = html.find("img")["style"]
    if display_size == "original":
        assert "max-width: none; width: auto;" in style
        assert "max-width: 100%" not in style
    else:
        assert "max-width: 100%;" in style
    assert "height: auto;" in style


def test_invalid_inline_image_display_size(image_values):
    image_values["chart"]["document"]["inline_image"]["display_size"] = 'original"; onerror="alert(1)'
    with pytest.raises(ValueError, match="display size"):
        get_html_email_body("((chart))", image_values, enable_inline_images=True)


@pytest.mark.parametrize("max_width", [1, 580, 1200])
def test_inline_image_max_width(image_values, max_width):
    image_values["chart"]["document"]["inline_image"]["max_width"] = max_width
    html = BeautifulSoup(str(get_html_email_body("((chart))", image_values, enable_inline_images=True)), "html.parser")
    image = html.find("img")
    assert f"max-width: {max_width}px; width: auto;" in image["style"]
    assert "height: auto;" in image["style"]
    assert "width" not in image.attrs
    assert "max-width: 100%" not in image["style"]


@pytest.mark.parametrize("max_width", [0, -1, True, "1200", 1.5, None])
def test_inline_image_rejects_invalid_max_width(image_values, max_width):
    image_values["chart"]["document"]["inline_image"]["max_width"] = max_width
    with pytest.raises(ValueError, match="positive integer"):
        get_html_email_body("((chart))", image_values, enable_inline_images=True)


@pytest.mark.parametrize("display_size", ["original", "responsive"])
def test_inline_image_rejects_combined_sizing(image_values, display_size):
    image_values["chart"]["document"]["inline_image"].update(max_width=1200, display_size=display_size)
    with pytest.raises(ValueError, match="both display_size and max_width"):
        get_html_email_body("((chart))", image_values, enable_inline_images=True)


@pytest.mark.parametrize("renderer", [PlainTextEmailTemplate, WithSubjectTemplate])
def test_non_html_renderers_use_alt_text(image_values, renderer):
    rendered = str(renderer({"content": "((chart))", "subject": "Usage"}, values=image_values))
    assert "Usage" in rendered
    assert "description" in rendered
    assert "inline_image" not in rendered
    assert "chart-123" not in rendered


def test_inline_image_does_not_enable_user_html(image_values):
    html = str(
        get_html_email_body(
            "<script>alert(1)</script>\n\n((chart))\n\n((name))",
            {**image_values, "name": '<img src="https://attacker.invalid" onerror="alert(1)">'},
            enable_inline_images=True,
        )
    )
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.find_all("img")) == 1
    assert soup.find("img")["src"] == "cid:chart-123"
    assert soup.find("script") is None


@pytest.mark.parametrize(
    "content",
    [
        "Text ((chart))",
        "[((chart))](https://example.ca)",
        "[link](((chart)))",
        "((chart??show this))",
        '<a href="((chart))">link</a>',
    ],
)
def test_inline_images_cannot_be_used_in_markup_or_conditionals(content, image_values):
    with pytest.raises(ValueError, match="own line"):
        get_html_email_body(content, image_values, enable_inline_images=True)


@pytest.mark.parametrize("content_id", ['x" onerror="alert(1)', "x\r\nInjected: true", "", "x" * 129])
def test_rejects_invalid_content_ids(content_id, image_values):
    image_values["chart"]["document"]["inline_image"]["content_id"] = content_id
    with pytest.raises(ValueError, match="content ID"):
        get_html_email_body("((chart))", image_values, enable_inline_images=True)


@pytest.mark.parametrize("alt_text", [None, "", "   ", "x" * 1001])
def test_rejects_invalid_alt_text(alt_text, image_values):
    image_values["chart"]["document"]["inline_image"]["alt_text"] = alt_text
    with pytest.raises(ValueError, match="alt text"):
        get_html_email_body("((chart))", image_values, enable_inline_images=True)


def test_content_id_and_alt_text_cannot_inject_attributes(image_values):
    image_values["chart"]["document"]["inline_image"]["alt_text"] = 'a" onerror="alert(1)'
    html = BeautifulSoup(str(get_html_email_body("((chart))", image_values, enable_inline_images=True)), "html.parser")
    assert html.find("img").get("onerror") is None


def test_column_normalisation_and_multiple_images(image_values):
    values = {**image_values, "second_image": image_values["chart"]}
    html = BeautifulSoup(
        str(get_html_email_body("((CHART))\n\n((second image))", values, enable_inline_images=True)), "html.parser"
    )
    assert len(html.find_all("img", src="cid:chart-123")) == 2
    assert "Usage" in str(Field("((chart))", values))
