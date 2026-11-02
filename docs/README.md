# Documentation

## Email template

### Email branding

The jinja template can render emails with 1 of 4 different brands. 

![The 4 brands: GOV.UK, GOV.UK and logo, Your logo and Your logo on a
colour](./images/email-branding-types.png)

Email templates for services without an associated logo will use the first brand, GOV.UK, by default.

Each of the other brands require certain attributes for the template to render them successfully.

![](./images/email-template-branding-modes.svg)

Note: the term 'government identity' refers to logos from the [government identity system (PDF, 4.2MB)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/362346/hmg_identity_system_guidelines_2012.pdf).

The dimensions of logos vary. Their height will be either 27px or 54px, depending on what suits the
image. The width will adjust to keep the aspect-ratio.

### Default branding images (FIP signature, wordmark)

The images used by the default branding live in [`notifications_utils/static/email`](../notifications_utils/static/email),
so changes to them show up as image diffs in pull requests.

They are served from each environment's asset domain (`assets.<domain>`) under content-addressed names, for
example `https://assets.notification.canada.ca/email-assets/gc-logo-en-522e149af6.png`. The hash is computed
from the file contents by [`email_assets.py`](../notifications_utils/email_assets.py), so:

* changing an image changes its URL. There is no cache-busting query string to update.
* emails that have already been sent keep pointing at the image they were sent with.
* an environment only starts using a new image once its api/admin run a utils version that references it.

Pass `asset_domain` (the app's `ASSET_DOMAIN` config) to `HTMLEmailTemplate` and `EmailPreviewTemplate` so each
environment uses its own assets. It defaults to `assets.notification.canada.ca`.

notification-terraform uploads the images to every environment's asset bucket, alongside the admin assets
(see [`aws/common/uploadS3Assets.tf`](https://github.com/cds-snc/notification-terraform/blob/main/aws/common/uploadS3Assets.tf)).
It clones this repo's `main` branch and computes the same content-addressed names, so new environments get the
images automatically. Uploads are additive: replaced images are never deleted, so an existing URL always keeps
serving the same image. Only `.gif`, `.jpeg`, `.jpg`, `.png` and `.svg` files are uploaded.

To change an image:

1. Replace the file in `notifications_utils/static/email`, keeping the same filename, and bump the version.
2. Merge, then push the version tag (`scripts/push-tag.sh`).
3. Run the "Merge to main (Staging)" workflow in notification-terraform so the new image is uploaded to staging.
   Nothing references it yet, so emails are unchanged.
4. Bump utils in api and admin and check the emails sent from staging.
5. Make sure the notification-terraform production release (which uploads the image to production) is applied
   before api and admin are released to production.

### Accessibility hacks

The following hacks have been added to make the template work with assistive technologies.

#### Empty alt text replaced with a single space

By convention, an empty value for the alt attribute of images tells user agents the image is
presentational and to be ignored from the normal flow.

This rule is not respected by some clients and some screenreaders are therefore announcing the
images. What's worse is, because of their having no alt text, the images are announced as the URL of
the image.

We found giving these images an alt value of " " makes some screenreaders ignore them and others
announce them as 'graphic'.

More details of this problem can be found in [pull request #542](https://github.com/alphagov/notifications-utils/pull/542).

#### No spacer images

A common hack for HTML emails is to use blank images, set to a dimension to create empty space in
your layout.

Because of the issue with alt text, any spacer images are announced to the user, which is not the
intention. For this reason we should try not to use them.

#### Use line break element for layout space

Another common hack is to use space characters encoded as HTML entities (ie `&nbsp;`), for empty
space in your layout. These are announced to users of screenreaders so should not be used. A
`<br />` tag, which is not part of the content of the document, should be used instead.

### Email hacks

HTML emails will be viewed on a large range of client programs and devices. The engine used to render the email can also change. Outlook, for example, has changed its renderer through the versions (see this [history of outlook email rendering](https://www.howto-outlook.com/faq/wordhtml.htm)).

Because of this, our email template relies on hacks to let it display consistently across clients/devices.

#### Meta tag to turn off format-detection

Adding the following stops phone numbers being turned into links.

##### Example

`<meta content="telephone=no" name="format-detection" />`

#### Duplicate CSS in different parts of the document

Clients will apply CSS depending on how it is defined but this is not consistent so multiple applications are needed.

##### Examples

CSS duplicated between the document head and inline styles.

```
  <style type="text/css">
    body { margin:0 !important; }
```

```
   <body style="margin: 0">
```

Styles duplicated between inline CSS and HTML4-style attributes on the element.

```
  <table
      style="width: 100% !important;"
      width="100%"
  >
```

#### Layout using tables

CSS used for layout is ignored by many clients. The pre-CSS method of using tables instead is currently the best way to build layouts that work across the greatest number of clients/devices. See this article on [why use tables for layout in emails](https://litmus.com/blog/the-tyranny-of-tables-why-web-and-email-design-are-so-different).

We give all our tables `role="presentation"` to ensure assistive technologies ignore them. We also zero their `border`, `cell-padding` and `cell-spacing` to ensure clients don't apply their own version of these values.

#### Conditional comments for Outlook

Microsoft-specific conditional comments can be used to deliver blocks of HTML only to certain versions of Outlook.

See this article on [using outlook conditional comments](https://templates.mailchimp.com/development/css/outlook-conditional-css/) for more detail.

```
   <!--[if (gte mso 9)|(IE)]>
   ...
   <![endif]-->
```

#### Use of !important in CSS

Clients can add their own CSS to emails. Using !important means the preceeding styles have a better chance of overwriting any CSS specific to that client.

#### Use of inline CSS

Some clients strip CSS out from the head of the email. Using inline CSS ensures elements will still be styled if this happens.

#### Email preheaders

The first line in the `<body>` of the template is used by clients to show a preview of the email (see [the commit that adds the preheader](https://github.com/alphagov/notifications-utils/commit/368b55eb509035e116291ac6346f658bc4b089fc) for details.)

We use CSS to hide it from the email when viewed in full.

#### Uppercase margin CSS

outlook.com strips margins out from CSS but capitalising them means it ignores them. This form is still recognised as valid CSS by all other clients. See this article on [margins in outlook.com](https://www.emailonacid.com/blog/article/email-development/outlook-com-does-support-margins/) for details.

#### Use of bgcolor instead of background-color in CSS

Support for the CSS property `background-color` across clients is buggy so we use the HTML4-style
`bgcolor` attribute instead. See this guide on [support for
background-color](https://www.campaignmonitor.com/css/color-background/background-color/).
