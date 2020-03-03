#!/usr/bin/python3
"""
This module updates the docker images of the docker-compose on the given path

Author: Janosch Deurer
Mail: deurer@mps-med.de

"""
from contextlib import contextmanager
from email.mime.text import MIMEText
from collections import defaultdict
import smtplib
import logging
import argparse
import re
import os
import subprocess
import socket
import yaml
import requests
import packaging.version


class Updater(object):

    """Update a single docker-compose.yml. """

    def __init__(self, path, dryrun):
        self.path = path
        self.dryrun = dryrun
        # Read docker-compose.yml as list
        self.docker_compose_path = os.path.join(path, "docker-compose.yml")
        self.docker_compose_versions_path = os.path.join(
            path, "docker-compose-versions.yml"
        )
        self.docker_compose = ""
        self.docker_compose_versions = None
        self.services = {"auto_update": dict(), "manual_update": dict()}
        self.updated_services = defaultdict(dict)

    def run(self):
        """ Run this class
        :returns: None

        """
        self.read()
        if self.docker_compose_versions is None or self.docker_compose is None:
            return
        for service_type in self.services:
            for service_name, service in self.services[service_type].items():
                # For manual updates check if auto_update already found a new
                # version
                if (
                    service_type == "manual_update"
                    and service_name in self.services["auto_update"]
                ):
                    service.current_version = self.services["auto_update"][
                        service_name
                    ].next_version

                service.find_next_version()
                if service.current_version == service.next_version:
                    logging.debug(
                        "No new version was found for service %s in %s",
                        service_name,
                        self.path,
                    )
                    continue
                else:
                    logging.debug(
                        "A new version was found for service %s in %s",
                        service_name,
                        self.path,
                    )
                self.updated_services[service_type][service_name] = service

        if not self.updated_services:
            logging.info("No changes for services in %s where found.", self.path)
            return

        mail_text = (
            "Updates in directory " + self.path + " on " + socket.gethostname() + "\n"
        )
        for service_type in self.updated_services:
            if service_type == "auto_update":
                mail_text = mail_text + (
                    "\nThe following Updates where found and automatically applied:\n\n"
                )
            else:
                mail_text = (
                    mail_text
                    + "\nThe following Updates where found but where not applied as "
                    + "they are configured for manual updates only:\n\n"
                )

            for service_name, service in self.services[service_type].items():
                mail_text = (
                    mail_text
                    + service_name
                    + ":\n  Old: "
                    + service.current_version
                    + "\n  New: "
                    + service.next_version
                    + "\n"
                )
                if service_type == "auto_update":
                    if service.dockerfile_path:
                        self.write_to_dockerfile(service)
                        self.build()
                    else:
                        self.write_to_docker_compose(service_name, service)
            if service_type == "auto_update":
                self.up()
        if self.dryrun:
            logging.info("Dryrun, not sending email")
            return
        write_email(
            mail_text,
            "[Dockerupdate]["
            + socket.gethostname()
            + "] Service Update for "
            + self.path,
        )

    def build(self):
        """ Build the new Docker image
        :returns: None

        """
        if self.dryrun:
            logging.info("Dryrun, skipping docker-compose build")
            return

        with working_directory(self.path):
            logging.info("Running docker-compose build")
            try:
                subprocess.run(["/usr/local/bin/docker-compose", "build"], check=True)
            except subprocess.CalledProcessError as error:
                logging.error("Could not run docker-compose build: %s", error)
                error_mail(error)

    def up(self):
        """Start the new Docker containers
        :returns: None

        """
        if self.dryrun:
            logging.info("Dryrun, skipping docker-compose up")
            return

        with working_directory(self.path):
            logging.info("Running docker-compose up -d")
            try:
                subprocess.run(
                    ["/usr/local/bin/docker-compose", "up", "-d"], check=True
                )
            except subprocess.CalledProcessError as error:
                logging.error("Could not run docker-compose up: %s", error)
                error_mail(error)

    def read(self):
        """ Initialize the class by reading information from the
        docker-compose.yml and docker-compose-versions.yml

        :returns: None

        """
        try:
            with open(self.docker_compose_path, "r") as stream:
                self.docker_compose = yaml.safe_load(stream)
            with open(self.docker_compose_versions_path, "r") as stream:
                self.docker_compose_versions = yaml.safe_load(stream)
        except FileNotFoundError as error:
            self.error_mail(error)
            exit(1)
        if self.docker_compose is None:
            text = "Empty docker-compose.yml at " + self.path
            self.error_mail(text)
            return
        if self.docker_compose_versions is None:
            logging.warning("Empty docker-compose-version.yml at %s", self.path)
            return

        for service_type in self.services:
            # continue if service type was not defined in the file
            if service_type not in self.docker_compose_versions:
                continue
            for service_name, search_regex in self.docker_compose_versions[
                service_type
            ].items():
                try:
                    docker_compose_service = self.docker_compose["services"][
                        service_name
                    ]
                except KeyError:
                    text = (
                        "The service "
                        + service_name
                        + " given in "
                        + self.docker_compose_versions_path
                        + " could not be found in "
                        + self.docker_compose_path
                    )
                    self.error_mail(text)
                    continue

                dockerfile_path = ""
                try:
                    image, current_version = docker_compose_service["image"].split(":")
                except KeyError:
                    # If image does not exist, there must be a build section
                    logging.debug(
                        "No image section was found, looking for build section"
                    )
                    try:
                        dockerfile_path = docker_compose_service["build"]["context"]
                    except (KeyError, TypeError):
                        dockerfile_path = docker_compose_service["build"]
                    logging.debug(
                        "Found build section with Dockerfile path %s", dockerfile_path
                    )
                    dockerfile_path = os.path.join(
                        self.path, dockerfile_path, "Dockerfile"
                    )

                    version = self.get_version_from_dockerfile(dockerfile_path)
                    # If no version was found skip this service
                    if version is None:
                        return
                    print(version)
                    image, current_version = version

                new_service = Service(
                    image, search_regex, current_version, dockerfile_path
                )
                self.services[service_type][service_name] = new_service

    def write_to_docker_compose(self, service_name, service):
        """Write changes to docker-compose

        :service: Service that changed
        :returns: None

        """
        if self.dryrun:
            logging.info("Dryrun, skipping to write the file")
            return
        # Writeout the changes. This is done manually, as using the yaml
        # package would lead to all comments in the docker-compose.yml beeing
        # removed.
        logging.info(
            "Writing new version for service %s to docker-compose.yml", service_name
        )
        with open(self.docker_compose_path, "r") as stream:
            docker_compose_text = stream.readlines()
        inside_service_section = False
        for i, _ in enumerate(docker_compose_text):
            line = docker_compose_text[i]
            if re.search("^ *" + service_name + ": *$", line):
                inside_service_section = True
            if inside_service_section and re.search("^ *image:", line):
                docker_compose_text[i] = line.replace(
                    service.current_version, service.next_version
                )
                # As the same image can also be used for other services we
                # have to stop here
                break
        with open(self.docker_compose_path, "w") as stream:
            stream.writelines(docker_compose_text)

    def write_to_dockerfile(self, service):
        """Write the given version to the FROM statement in the Dockerfile at the
        given path

        :path: Path of the Dockerfile
        :version: version to write
        :returns: None

        """
        logging.info(
            "Writing new version to Dockerfile at %s.", service.dockerfile_path
        )
        # Read Dockerfile as list
        with open(service.dockerfile_path, "r") as stream:
            dockerfile = stream.readlines()
        for i, _ in enumerate(dockerfile):
            line = dockerfile[i]
            if line.startswith("FROM"):
                dockerfile[i] = " ".join(
                    [line.split()[0], service.image + ":" + service.next_version, "\n"]
                )
                break
        print(service.dockerfile_path)
        with open(service.dockerfile_path, "w") as stream:
            stream.writelines(dockerfile)

    def get_version_from_dockerfile(self, path):
        """Get docker image version from the Dockerfile at the given path
        :path: Path of the Dockerfile
        :returns: image version

        """
        # Read Dockerfile as list
        with open(path, "r") as stream:
            dockerfile = stream.readlines()
        img_version = ""
        for i, _ in enumerate(dockerfile):
            line = dockerfile[i]
            if line.startswith("FROM"):
                img_version = line.split()[1].split(":")
                break
        else:
            text = "Dockerfile at " + path + " seems to be missing a FROM statement"
            self.error_mail(text)
            return
        return img_version

    def error_mail(self, error):
        logging.error(error)
        if self.dryrun:
            logging.info("Dryrun, skipping sending mail")
            return
        error_mail(error)


class Service(object):

    """Docstring for Service. """

    def __init__(self, image, search_regex, current_version, dockerfile_path):
        """TODO: to be defined1. """
        self.image = image
        self.search_regex = search_regex
        self.current_version = current_version
        self.next_version = current_version
        self.dockerfile_path = dockerfile_path

    def find_next_version(self):
        """ Search on dockerhub for the newest versions of the dockerimage
        :category: YAML block where the search regex is defined.

        :returns: Dict of dockerhub versions for each service specified in
        docker-compose-versions.yml

        """
        logging.debug(
            "Searching for regex %s in %s tags", self.search_regex, self.image
        )
        # Get all tags from dockerhub
        dockerhub_versions = requests.get(
            "https://registry.hub.docker.com/v1/repositories/" + self.image + "/tags"
        )
        if dockerhub_versions.status_code == 404:
            text = "The dockerimage " + self.image + " could not be found on dockerhub."
            logging.error(text)
            error_mail(text)
            return

        for tag in dockerhub_versions.json():
            found_tag = re.search(self.search_regex, tag["name"])
            if found_tag is not None:
                logging.debug("Found tag %s", found_tag.string)
                if packaging.version.parse(found_tag.string) > packaging.version.parse(
                    self.next_version
                ):
                    self.next_version = found_tag.string
        logging.debug("Current version: %s", self.current_version)
        logging.debug("Newest version: %s", self.next_version)


@contextmanager
def working_directory(directory):
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(owd)


def get_commandline_arguments():
    """ Commandline argument parser for this module
    :returns: namespace with parsed arguments

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path of the docker-compose.yml")
    parser.add_argument(
        "-r",
        "--recursive",
        help="find all docker-compose-versions.yml in "
        + "subdirectories and run the update there",
        action="store_true",
    )
    parser.add_argument("--logfile", help="path to a file the output is passed to")
    parser.add_argument(
        "-d", "--dryrun", help="only show what would happen", action="store_true"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbosity", help="increase output verbosity", action="store_true"
    )
    group.add_argument(
        "-q", "--quiet", help="no output except errors", action="store_true"
    )
    args = parser.parse_args()
    return args


def initialize_logging(commandline_args):
    """Initialize logging as given in the commandline arguments

    :commandline_args: namespace with commandline arguments including verbosity
    and logfile if given
    :returns: None

    """
    loglevel = "INFO"
    if commandline_args.verbosity:
        loglevel = "DEBUG"
    if commandline_args.quiet:
        loglevel = "ERROR"

    logfile = commandline_args.logfile

    # If logfile is given, generate a new logger with file handling
    if logfile:
        filehandler = logging.FileHandler(logfile, "a")
        formatter = logging.Formatter()
        filehandler.setFormatter(formatter)
        logger = logging.getLogger()
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(filehandler)

    loglevel = getattr(logging, loglevel.upper())
    logging.getLogger().setLevel(loglevel)


def error_mail(error):
    subject = (
        "[Dockerupdate][" + socket.gethostname() + "] Error in docker-compose-update"
    )
    text = "The following error uccured:\n" + str(error)
    write_email(text, subject)


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
            "Environment variable %s not " + "specified, cannot send mails", exception
        )
        exit(1)
    smtp_server_port = os.environ.get("MAIL_SMTP_SERVER_PORT", 465)
    username = os.environ.get("MAIL_USER", None)
    password = os.environ.get("MAIL_PASSWORD", None)

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
        smtpserver = smtplib.SMTP_SSL(smtp_server_domain, smtp_server_port)
        if username is not None and password is not None:
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
            "Error from smtp server, you are not allowed "
            + "to send a message to this user: %s",
            str(exception),
        )


def main():
    """Entrypoint when used as an executable
    :returns: None

    """

    try:
        # Initialize Logging
        logging.basicConfig(level=logging.DEBUG)
        args = get_commandline_arguments()
        initialize_logging(args)

        # If recursive option is not given just run the updater for the given path
        if not args.recursive:
            updater = Updater(os.path.abspath(args.path), args.dryrun)
            updater.run()
            exit(0)
        # If the recursive option is given, recursiveley search for
        # docker-compose-versions.yml and run the updater for each found path
        pathlist = []
        for root, _, files in os.walk(args.path):
            for file in files:
                if file == "docker-compose-versions.yml":
                    pathlist.append(root)
        for path in pathlist:
            abspath = os.path.abspath(path)
            logging.info(
                "Found docker-compose-versions.yml in %s. Starting updater.", abspath
            )
            updater = Updater(abspath, args.dryrun)
            updater.run()
    except Exception:
        # If something goes wrong try sending an E-Mail
        if not args.dryrun:
            logging.critical(
                "An unhandled error occured, sending a mail about the error"
            )
            error_mail("Unhandled error")
        raise


if __name__ == "__main__":
    main()
