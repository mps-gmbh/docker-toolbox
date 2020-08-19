#!/usr/bin/python3
"""
This module updates the docker images of the docker-compose on the given path
"""
from email.mime.text import MIMEText
import smtplib
import logging
import os
import sys


def write_email(msg_text, msg_subject):
    """ Writes an e-mail with the given text and subject

    :msg_text:(str) Message text
    :msg_subject:(str) Message subject
    :returns: None
    """
    try:
        smtp_server_domain = os.environ["MAIL_SMTP_SERVER"]
        mail_from = os.environ["MAIL_FROM"]
        mail_to = os.environ["MAIL_TO"]
    except KeyError as exception:
        logging.error(
            "Environment variable %s not specified, cannot send mails", exception
        )
        sys.exit(1)
    smtp_server_port = os.environ.get("MAIL_SMTP_SERVER_PORT", 465)
    username = os.environ.get("MAIL_USER", None)
    password = os.environ.get("MAIL_PASSWORD", None)
    smtp_ssl = os.environ.get("MAIL_SMTP_SSL", "True")

    msg = MIMEText(msg_text)
    msg["Subject"] = msg_subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    logging.debug(
        "Sending message with following settings:\n"
        + "Server: "
        + smtp_server_domain
        + "\n"
        + "From: "
        + mail_from
        + "\n"
        + "To: "
        + mail_to
        + "\n"
        + "Subject: "
        + msg_subject
        + "\n"
        + "Content: "
        + msg_text
    )

    try:
        # Send the message via our own SMTP server.
        if smtp_ssl != "False":
            smtpserver = smtplib.SMTP_SSL(smtp_server_domain, smtp_server_port)
        else:
            smtpserver = smtplib.SMTP(smtp_server_domain, smtp_server_port)
        if username and password:
            smtpserver.login(username, password)

        smtpserver.send_message(msg)
        smtpserver.quit()
    except ConnectionRefusedError as error:
        logging.error(
            "Connection refused by smtp server, please make shure \
            your smtp server on %s is configured correctly. The error is: %s",
            smtp_server_domain,
            str(error),
        )
    except smtplib.SMTPServerDisconnected as error:
        logging.error("Connection to smtpserver failed with with error: %s", str(error))
    except smtplib.SMTPRecipientsRefused as exception:
        logging.error(
            """Error from smtp server, you are not allowed to
            send a message to this user: %s""",
            str(exception),
        )
