"""
Test the docker-compose-updater
"""

from unittest import mock
import smtplib
import pytest
from docker_mail.docker_mail import write_email


# pylint: disable=missing-function-docstring,no-self-use
class TestDockerComposeUpdate:  # pylint: disable=missing-class-docstring
    @pytest.mark.parametrize("os_mock_value", [("mock_string"), ("False"), (None)])
    def test_write_email(self, os_mock_value):
        with mock.patch("docker_mail.docker_mail.os") as os_mock, mock.patch(
            "docker_mail.docker_mail.smtplib"
        ) as smtplib_mock:
            os_mock.environ.get.return_value = os_mock_value
            write_email("test text", "test subject")
            if os_mock_value == "False":
                assert smtplib_mock.SMTP.called
            else:
                assert smtplib_mock.SMTP_SSL.called

    def test_write_email_key_error(self):
        """
        Check system exit if env variables are not given
        """
        with mock.patch("docker_mail.docker_mail.os") as os_mock:
            os_mock.environ.__getitem__.side_effect = KeyError
            try:
                write_email("test text", "test subject")
            except SystemExit:
                return
        assert False

    def test_write_email_server_errors(self):
        with mock.patch("docker_mail.docker_mail.os"), mock.patch(
            "docker_mail.docker_mail.smtplib"
        ) as smtplib_mock:
            smtplib_mock.SMTPServerDisconnected = smtplib.SMTPServerDisconnected
            smtplib_mock.SMTPRecipientsRefused = smtplib.SMTPRecipientsRefused

            for error in [
                ConnectionRefusedError,
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPRecipientsRefused("test recipient"),
            ]:
                smtplib_mock.SMTP_SSL.side_effect = error
                write_email("test text", "test subject")
