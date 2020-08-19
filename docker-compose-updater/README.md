# docker-compose-update - Keep your docker-compose files and containers up to date

**Warning:** This project is in an early development phase. Although it has a
high test coverage it should be used in production with caution.

`docker-compose-update` is a Docker Container running a python script that
updates the Docker Images referenced in your `docker-compose.yml files. The
idea is that all the images you use are pinned to a specific version and this
version is then updated by `docker-compose-update`. This enables you to always
work with pinned versions which is espetially important in cases of rolebacks
or restoring backups.

## Features

- Update pinned image versions
  - In the `image` section of `docker-compose.yml`
  - In the `FROM` section of Dockerfiles referenctd in the `build` section of
    the `docker-compose.yml`
- Specify new versions to look for by regex
  - For automatic updates
  - For manual updates
- E-Mails about
  - Automatic updates
  - Available manual updates
  - Errors

## Quickstart

To get startet copy the env examplefile:

```
cp env.example .env
```

Configure the variables in den `.env` file and start the container with:

```
docker-compose up
```

The container starts cron and runs the script every minute and updates an
example service.

## Usage

First take a look at the quickstart.

### docker-compose-versions.yml

The script recursiveley searches for `docker-compose.yml` files, if it finds
one it looks for a `docker-compose-versions.yml` file in the same directory.
Such a file can look like this:

```YAML
manual_update:
  dummy: 3\.[0-9]+\.[0-9]+
auto_update:
  dummy: 3\.[0-9]+\.[0-9]+
```

There are two main parts in this file, `manual_update` and `auto_updat`. For
manual updates only a mail notification is send if an update is available, for
auto updates the version is adapted in the corresponding `docker-compose.yml`
or `Dockerfile` and a `docker-compose build` and a `docker-compose up -d` is
triggered. In these sections you have to specify the services that you want to
update. The script will use the image specified in the services or the
corresponding `Dockerfile` and search for tags matching the regular expression
in the `docker-compose-versions.yml`. From the found tags it will use the
newest one and apply it.

#### Examples

Further examples for docker-files can be found in the
[test](src/test/example_services) directory.

#### Regular Expression

The python regex module is used to match regular expressions.

### Mounting the docker-compose files

The script recusiveley searches for `docker-compose-version.yml` files in
`/compose-mount`. Mount your `docker-compose-version.yml` and
`docker-compose.yml` files there or reconfigure the location in the crontab
file or in the entrypoint.

### Configuring cron

Cron can be configured in the crontab file.

### Environment Variables

- `DOCKER_HOST_NAME` Hostname used in the mails to inform you about changes
- `MAIL_SMTP_SERVER` Mailserver used to send mails
- `MAIL_FROM` Address the mails are send from
- `MAIL_TO` Address the mails are send to, multiple addresses can be seperated
  by comma

The following variables are optional

- `ARCHITECTURE` architecture of the docker images to look for, defaults to
  `amd64`
- `MAIL_SMTP_SERVER_PORT` Mailserver port, defaults to 465
- `MAIL_SMTP_SSL` Enable SSL for smtp server connection, can be `True` oder
  `False`

If either `MAIL_USER` or `MAIL_PASSWORD` an anonymouse login will be used

- `MAIL_USER` Smtp user
- `MAIL_PASSWORD` Smtp password

- `LOGLEVEL` Loglevel defaults to `INFO`, can be `CRITICAL`, `ERROR`,
  `WARNING`, `INFO` or `DEBUG`

