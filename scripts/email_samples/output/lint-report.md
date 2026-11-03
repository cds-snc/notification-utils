# Email client compatibility report

Static analysis by [doiuse-email](https://github.com/leondreamed/doiuse-email) 0.4.1, using its bundled [caniemail.com](https://www.caniemail.com) data (which may lag the live site).
Clients checked: `outlook.*, gmail.*, apple-mail.*, yahoo.*, samsung-email.*, thunderbird.*`.

This only lists features that a client is *known* not to support. It can't tell whether the email still looks acceptable, and it misses features caniemail has no data for. Confirm findings in real clients.

## Not supported

| Feature | Clients | Samples |
| --- | --- | --- |
| `<body> element` | outlook.android, outlook.ios, yahoo.android, yahoo.ios | all |
| `@media` | gmail.mobile-webmail, outlook.windows, outlook.windows-mail, thunderbird.macos | all |
| `word-break` | outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all except bilingual--fip_en, lists--fip_en, rtl_block--fip_en |
| `Attribute selector` | gmail.mobile-webmail, outlook.windows, outlook.windows-mail | all |
| `background-image` | outlook.windows, outlook.windows-mail | all |
| `border-radius` | outlook.windows, outlook.windows-mail | all except plain--no_branding |
| `Class selector` | gmail.mobile-webmail | all |
| `Descendant combinator` | gmail.mobile-webmail | all |
| `display:none` | gmail.mobile-webmail | all |
| `role attribute` | outlook.windows-mail | all |
| `Type selector` | gmail.mobile-webmail | all |

## Partially supported

| Feature | Clients | Samples |
| --- | --- | --- |
| `!important keyword` | gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail, outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `@media` | gmail.android, gmail.desktop-webmail, gmail.ios, outlook.android, outlook.ios, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `Attribute selector` | gmail.android, gmail.desktop-webmail, gmail.ios, outlook.android, outlook.ios, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `margin` | gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail, outlook.android, outlook.ios, outlook.windows, outlook.windows-mail | all |
| `word-break` | apple-mail.ios, apple-mail.macos, gmail.android, gmail.ios, gmail.mobile-webmail, outlook.android, outlook.ios, samsung-email.android | all except bilingual--fip_en, lists--fip_en, rtl_block--fip_en |
| `display` | gmail.android, gmail.ios, outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `text-align` | gmail.android, gmail.ios, outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all except plain--custom_logo, plain--custom_logo_with_background_colour, plain--custom_logo_with_text, plain--no_branding |
| `<body> element` | gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail, yahoo.desktop-webmail | all |
| `background` | outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `font-weight` | outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios | bilingual--fip_en, kitchen_sink--fip_en, lists--fip_en, overflow--fip_en, plain--custom_logo_with_background_colour, rtl_block--fip_en, rtl_template--fip_en |
| `max-width` | apple-mail.ios, outlook.windows, outlook.windows-mail, yahoo.ios | all |
| `background-image` | yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `border-radius` | yahoo.android, yahoo.desktop-webmail, yahoo.ios | all except plain--no_branding |
| `Class selector` | gmail.android, gmail.ios, yahoo.android | all |
| `Descendant combinator` | gmail.android, gmail.ios, yahoo.android | all |
| `dir attribute` | gmail.mobile-webmail, outlook.windows, outlook.windows-mail | all |
| `lang attribute` | yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `role attribute` | yahoo.android, yahoo.desktop-webmail, yahoo.ios | all |
| `Type selector` | gmail.android, gmail.ios, yahoo.android | all |
| `border` | outlook.windows, outlook.windows-mail | all except plain--no_branding |
| `display:none` | outlook.windows, outlook.windows-mail | all |
| `line-height` | outlook.windows, outlook.windows-mail | all |
| `padding` | outlook.windows, outlook.windows-mail | all |
| `height attribute` | outlook.windows | all except plain--no_branding |
| `width attribute` | outlook.windows | all except plain--no_branding |

## Notes from caniemail

### `!important keyword`

- outlook.windows: Partial. Not supported inline. (See [email-bugs#31](https://github.com/hteumeuleu/email-bugs/issues/31))
- gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail: Partial. Only supported in lowercase. (See [email-bugs#13](https://github.com/hteumeuleu/email-bugs/issues/13))
- gmail.android, gmail.ios, gmail.mobile-webmail: Partial. Only supported inline when using a Non Gmail Account due to the lack of `<style>` support.
- outlook.windows, outlook.windows-mail: Partial. Only supported with a space before.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Removed if there is no space before when used with a `background-image` property. (See [email-bugs#16](https://github.com/hteumeuleu/email-bugs/issues/16))

### `<body> element`

- gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail, yahoo.desktop-webmail: Partial. Replaced by a `<div>` with supported attributes.

### `@media`

- yahoo.android: Buggy. Requires a double `<head>` hack to work.
- gmail.android, gmail.desktop-webmail, gmail.ios: Partial. Does not support height based media queries.
- outlook.android, outlook.ios: Partial. Does not support nested media queries.
- gmail.android, gmail.ios: Partial. Not supported with non Gmail accounts.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Only supports `screen`, `min-width`, `max-width`, `min-height` and `max-height` based media queries.

### `Attribute selector`

- outlook.android, outlook.ios: Partial. Can not be used with a class selector (`.test[class]`). Must be used solo (`[class]`) or with an element selector (`td[class]`).
- gmail.android, gmail.ios: Partial. Doesn't work with Non Gmail Accounts.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Only supports `[attr=value]` syntax.
- outlook.android, outlook.ios: Partial. Only supports `[attr]`, `[attr=value]`, `[attr~=value]`, `[attr|=value]` syntaxes.
- gmail.android, gmail.desktop-webmail, gmail.ios: Partial. Only supports `[attr~=value]` syntax. Only `class` as an attribute name is known to be supported.

### `Class selector`

- yahoo.android: Buggy. The first `<head>` in the HTML is removed, so `<style>` elements need to be in a second `<head>` element.
- gmail.android, gmail.ios: Partial. Not supported with non Gmail accounts.

### `Descendant combinator`

- yahoo.android: Buggy. The first `<head>` in the HTML is removed, so `<style>` elements need to be in a second `<head>` element.
- gmail.android, gmail.ios: Partial. Not supported with non Gmail accounts.

### `Type selector`

- yahoo.android: Buggy. The first `<head>` in the HTML is removed, so `<style>` elements need to be in a second `<head>` element.
- gmail.android, gmail.ios: Partial. Not supported with non Gmail accounts.

### `background`

- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Does not support multiple values. The comma between two values is removed.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Does not support the `/ value` shorthand for `background-size`. But it can be used in the `background-size` property instead.
- outlook.windows, outlook.windows-mail: Partial. Only `background-color` values are supported.

### `background-image`

- outlook.windows: Background images can be used in VML. See [backgrounds.cm](https://backgrounds.cm/) and [VML documentation](https://docs.microsoft.com/en-us/windows/win32/vml/web-workshop---how-to-use-vml-on-web-pages-----fill--element).
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Does not support multiple values. The comma between two values is removed.

### `border`

- outlook.windows, outlook.windows-mail: Buggy. Unreliable if used on a `<p>` or a `<div>`.
- outlook.windows, outlook.windows-mail: Partial. A border can not be bigger than 8px.

### `border-radius`

- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial support. Shorthand for setting elliptical borders with the slash `/` notation is not supported e.g. `border-radius: 27% 73% 70% 30% / 30% 34% 66% 70%;`.
- outlook.windows, outlook.windows-mail: Round corners can be used in VML with the `RoundRect` element. See [buttons.cm](https://buttons.cm/) and [VML documentation](https://docs.microsoft.com/en-us/windows/win32/vml/msdn-online-vml-roundrect-element).

### `dir attribute`

- outlook.windows, outlook.windows-mail: Buggy on anchor `<a>` tags.
- gmail.mobile-webmail: Buggy. The client applies an `rtl` direction to the entire email if it contains text in a `rtl` language.

### `display`

- outlook.windows, outlook.windows-mail: Buggy. `display:none` does not inherit to inner tables.
- outlook.windows, outlook.windows-mail: Partial. Only supports `display:none` (but not on `<img>`).
- gmail.android, gmail.ios: Partial. `flex`, `grid`, `flow-root`, `contents`, `inline flow-root`, `inline flex`, `inline grid`, `initial`, `revert`, `unset` are not supported with Non Gmail Accounts.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. `flow-root`, `inline-flex`, `inline-grid`, `inline flow`, `contents`, `revert` are not supported.

### `display:none`

- outlook.windows, outlook.windows-mail: Partial. Does not inherit onto nested `<table>` elements.
- outlook.windows, outlook.windows-mail: Partial. Does not work when applied directly to an `<img>` element.

### `font-weight`

- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial support. `<number>` values are not supported as per CSS Fonts Level 4 where any `<number>` value between 1 and 1000 (inclusive) is a valid value. Only the following numeric values are supported: 100, 200, 300, 400, 500, 600, 700, 800, and 900.
- outlook.windows, outlook.windows-mail: Partial support. `<number>` values between 0 and 599 are set as normal font weight. `<number>` values between 600 and 1000 are set as bold font weight.

### `height attribute`

- outlook.windows: Buggy. Percentage width on `<img>` elements are based on the physical file's width, not on the parent element's width.
- outlook.windows: Buggy. Sizes set in attributes don't scale in 120 dpi mode.

### `lang attribute`

- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Not supported on `<td>` elements.

### `line-height`

- outlook.windows, outlook.windows-mail: Buggy. `em` and `px` units behave weirdly. Use `mso-line-height-rule:exactly`.

### `margin`

- outlook.windows, outlook.windows-mail: Buggy. `background-color` is included inside the `margin`.
- gmail.android, gmail.desktop-webmail, gmail.ios, gmail.mobile-webmail, outlook.android, outlook.ios, outlook.windows, outlook.windows-mail: Partial. Negative values are not supported.
- outlook.windows, outlook.windows-mail: Partial. Not supported on `<span>` and `<body>` elements.
- outlook.windows: Partial. `auto` value is not supported.

### `max-width`

- apple-mail.ios, yahoo.ios: Partial. Doesn't work on `<table>` elements, as per [CSS 2.1 specification](https://www.w3.org/TR/CSS2/visudet.html#min-max-widths).
- outlook.windows, outlook.windows-mail: Partial. Only works on `<table>` elements.

### `padding`

- outlook.windows, outlook.windows-mail: Buggy. Vertical padding will be the same for all cells of a same row, adopting the biggest value.
- outlook.windows, outlook.windows-mail: Partial. Only supported on table cells.

### `role attribute`

- outlook.windows: Not live tested, only looked at processed code on Litmus.
- yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Only works on the `<table>` tag.

### `text-align`

- gmail.android, gmail.ios: Partial. Flow-relative values `start` and `end` are not supported with non Gmail account.
- outlook.windows, outlook.windows-mail, yahoo.android, yahoo.desktop-webmail, yahoo.ios: Partial. Flow-relative values `start` and `end` are not supported.

### `width attribute`

- outlook.windows: Buggy. Percentage width on `<img>` elements are based on the physical file's width, not on the parent element's width.
- outlook.windows: Buggy. Sizes set in attributes don't scale in 120 dpi mode.
- apple-mail.macos: The `width` attribute is ignored on CID embedded images. See [#171](https://github.com/hteumeuleu/caniemail/issues/171).

### `word-break`

- apple-mail.ios, apple-mail.macos, gmail.android, gmail.ios, gmail.mobile-webmail, outlook.android, outlook.ios, samsung-email.android: Buggy. Supported but a `word-wrap:break-word` is applied, making it look like `break-all`.
- gmail.desktop-webmail: Supported. But Gmail adds `<wbr>` every 30 characters.
