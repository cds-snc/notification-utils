# Waffles action

This action performs URL checks of self-discovered endpoints within a Flask
application against a provided base URL, i.e. targeting the staging or
production environment.

## Supporting a new URL within GCNotify

When you want to add a new URL to be supported in GCNotify, this will require
a few code interventions. For example, if you want to publish a new landing page
on the admin component via GCArticles, you'd need to perform these steps to allow
the new URL to get through the firewall rules. We restrict these URLs because
we don't want any URLs to get hit by URL scanning actions on GCNotify, producing
noise in our WAF logs and potentially triggering support alarms.

### Add to AWS WAF rules in Terraform repository

To open new URLs, we need to refine the regular expressions in the Terraform
repository. Listed below are the locations of these, depending on the component
you need to add the new URLs for.

#### notification-admin

1. If the URL to add is for GCArticles, grab the link from the wordpress
platform and the assigned slug for the new article.

2. Add a corresponding  regular expressions at this location to let the
new URL through:

   * [aws/eks/admin_waf_regex_patterns.tf](https://github.com/cds-snc/notification-terraform/blob/main/aws/eks/admin_waf_regex_patterns.tf)

3. Add the new routes into the `GC_ARTICLES_ROUTES` global variable in
this file:

   * [app/articles/routing.py](https://github.com/cds-snc/notification-admin/blob/97bd1e2762c8358af55cccb947496d5bc990a15d/app/articles/routing.py#L5)

#### notification-api

1. Add a corresponding  regular expressions at this location to let the
new URL through:

   * [aws/eks/api_waf_regex_patterns.tf](https://github.com/cds-snc/notification-terraform/blob/main/aws/lambda-api/api_waf_regex_patterns.tf)

#### notification-document-download-api

1. Add a corresponding  regular expressions at this location to let the
new URL through:

   * [aws/eks/waf.tf](https://github.com/cds-snc/notification-terraform/blob/1273707e7c4fe101f8c1a7d31ca3de421662a9e7/aws/eks/waf.tf#L615)

## Inputs

## `app-loc`

**Required** Project's directory location.

**Example**: `/Projects/cds/notification-document-download-api`

## `app-libs`

**Required** Project's libs directory location.

**Example**: `/doc-api-env/Lib/site-packages`

## `flask-mod`

**Required** Flask app module to execute.

**Example**: `application`

## `flask-prop`

**Required** Flask app property in the module.

**Example**: `application`

## `base-url`

**Required** Base URL used to hit the application with discovered Flask endpoints.

**Example**: `https://api.document.staging.notification.cdssandbox.xyz`

## Outputs

None other than the log output and system exit code.

## Example usage

```yaml
uses: actions/waffles@v1
with:
  app-loc: '/doc-api-env/Lib/site-packages'
  app-libs: '/Projects/cds/notification-document-download-api'
  flask-mod: 'application'
  flask-prop: 'application'
  base-url: 'https://api.document.staging.notification.cdssandbox.xyz'
```
