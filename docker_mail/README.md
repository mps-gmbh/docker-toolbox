# docker_mail - a small python module to send mails in docker containers

This module provides a single method `write_email(msg_text, msg_subject)`. All
configuration except text and subject are read from env variables. The
following env variables are available:

## Environment Variables

- `MAIL_SMTP_SERVER` Mailserver used to send mails
- `MAIL_FROM` Address the mails are send from
- `MAIL_TO` Address the mails are send to, multiple addresses can be seperated
  by comma

The following variables are optional

- `MAIL_SMTP_SERVER_PORT` Mailserver port, defaults to 465
- `MAIL_SMTP_SSL` Enable SSL for smtp server connection, can be `True` or
  `False` defaults to `True`

If either `MAIL_USER` or `MAIL_PASSWORD` are missing an anonymouse login will
be used

- `MAIL_USER` Smtp user
- `MAIL_PASSWORD` Smtp password
- `LOGLEVEL` Loglevel defaults to `INFO`, can be `CRITICAL`, `ERROR`,
  `WARNING`, `INFO` or `DEBUG`

