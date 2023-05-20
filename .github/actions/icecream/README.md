# IceCream action

This action performs URL checks of self-discovered endpoints within a Flask
application against a provided base URL, i.e. targeting the staging or
production environment.

## Inputs

## `gh-wiki-repo-url`

**Required** Project's directory location.

**Example**: `/Projects/cds/notification-document-download-api`

## `wiki-page-title`

**Required** Project's libs directory location.

**Example**: `/doc-api-env/Lib/site-packages`

## Outputs

None other than the log output and system exit code.

## Example usage

```yaml
uses: actions/icecream@v1
with:
  gh-wiki-repo-url: ''
  wiki-page-title: 'GCNotify AWS CloudWatch Alarms'
```
