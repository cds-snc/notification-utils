# Waffles action

This action performs URL checks of self-discovered endpoints within a Flask
application against a provided base URL, i.e. targeting the staging or
production environment.

## Inputs

## `app-libs`

**Required** Project's libs directory location.

**Example**: `/Projects/cds/notification-document-download-api`

## `app-loc`

**Required** Project's directory location.

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

uses: actions/waffles@v1
with:
  app-libs: '/Projects/cds/notification-document-download-api'
  app-loc: '/doc-api-env/Lib/site-packages'
  flask-mod: 'application'
  flask-prop: 'application'
  base-url: 'https://api.document.staging.notification.cdssandbox.xyz'
