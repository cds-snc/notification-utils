# Email samples

Renders a set of sample GC Notify emails so you can check how they look in different email clients. Use it to find rendering bugs, and to compare emails before and after changing the email template (`notifications_utils/jinja_templates/email/`) or the Markdown formatters (`notifications_utils/formatters.py`).

## Usage

From the repository root:

```shell
make email-samples
# or, with options:
poetry run python -m scripts.email_samples.generate --help
```

The compatibility check needs Node.js (it runs [doiuse-email](https://github.com/leondreamed/doiuse-email) with `npx`). Pass `--no-lint` to skip it.

Everything is written to `scripts/email_samples/output/` (ignored by git):

| File | What it's for |
| --- | --- |
| `index.html` | A gallery of every sample at desktop and mobile widths. Open it in a browser for a quick look. This is a browser rendering, not an email client rendering. |
| `<sample>.html` | The exact HTML that notification-api sends. Upload it to a screenshot service such as Litmus or Email on Acid / Mailgun Inspect. |
| `<sample>.eml` | A complete email with plain text and HTML parts. Open it in a desktop client (for example Outlook for Windows or Apple Mail) to see how that client renders it. |
| `lint-report.md` | HTML and CSS features the samples use that some clients don't support or only partly support, based on [caniemail.com](https://www.caniemail.com) data. |
| `lint-report.json` | The raw doiuse-email output for each sample. |

## Samples

Samples are defined in [`samples.py`](./samples.py):

- **Content** covers each formatting option: headings, lists (including nested lists), inset text, horizontal rules, links, conditional text, bilingual `[[en]]`/`[[fr]]` blocks, right-to-left text, and long words and links that may overflow on small screens.
- **Branding** mirrors `get_html_email_options` in notification-api: the Government of Canada signature in English or French, a custom logo with or without the signature, a logo on a coloured banner, and no branding. Use `--logo-url` and `--brand-colour` to try a specific service's branding.

Every content sample is rendered with the default branding, and every branding with plain content. This keeps the set small enough to screenshot in many clients.

## Comparing before and after a change

Output is deterministic, so you can diff two runs:

```shell
poetry run python -m scripts.email_samples.generate --output-dir /tmp/before --no-lint
# make your change
poetry run python -m scripts.email_samples.generate --output-dir /tmp/after --no-lint
diff -r /tmp/before /tmp/after
```
