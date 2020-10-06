"""
Test the docker-compose-updater
"""
import shutil
import os
import subprocess
from unittest import mock
import pytest
import requests
from src.docker_compose_update import Updater
from src.docker_compose_update import Service
from src.docker_compose_update import initialize_logging
from src.docker_compose_update import get_docker_compose_directories


# pylint: disable=missing-function-docstring,no-self-use
class TestDockerComposeUpdate:  # pylint: disable=missing-class-docstring
    @pytest.fixture(scope="function")
    def example_services(self):
        """Create a copy of the example_services"""

        # Delete the folder if it exists
        try:
            shutil.rmtree("./src/test/example_services_test_run")
        except FileNotFoundError:
            pass

        # Copy example_services
        shutil.copytree(
            "./src/test/example_services", "./src/test/example_services_test_run"
        )
        os.remove("./src/test/example_services_test_run/.docker-compose-update-ignore")
        yield
        shutil.rmtree("./src/test/example_services_test_run")

    @pytest.mark.parametrize(
        "path, dryrun, dc_run, dc_content, dockerfile_content, dockerhub_statuscode",
        [
            ("base", True, False, "    image: python:latest\n", None, 200),
            ("base", True, False, "    image: python:latest\n", None, 404),
            ("base", False, True, "    image: python:3.8.2-buster\n", None, 200),
            ("base", False, False, "    image: python:latest\n", None, 404),
            (
                "yaml_error_in_versions",
                False,
                False,
                "    image: python:latest\n",
                None,
                200,
            ),
            ("no_init_version", True, False, "    image: python\n", None, 200),
            (
                "no_init_version",
                False,
                True,
                "    image: python:3.8.2-buster\n",
                None,
                200,
            ),
            ("empty_versions", False, False, "    image: python:latest\n", None, 200),
            ("up_to_date", False, False, "    image: python:3.8.2-buster\n", None, 200),
            (
                "manual_update",
                False,
                True,
                "    image: python:3.7.6-buster\n",
                None,
                200,
            ),
            (
                "manual_update_only",
                False,
                False,
                "    image: python:latest\n",
                None,
                200,
            ),
            (
                "auto_update_only",
                False,
                True,
                "    image: python:3.8.2-buster\n",
                None,
                200,
            ),
            ("key_error", False, False, "    image: python:latest\n", None, 200),
            ("key_error", True, False, "    image: python:latest\n", None, 200),
            ("docker_compose_empty", False, False, None, None, 200),
            (
                "dockerfile_base",
                False,
                True,
                "    build: .\n",
                "FROM python:3.8.2-buster \n",
                200,
            ),
            (
                "dockerfile_base",
                True,
                False,
                "    build: .\n",
                "FROM python:latest\n",
                200,
            ),
            ("dockerfile_empty", True, False, "    build: .\n", None, 200),
        ],
    )
    def test_run(
        self,
        example_services,
        path,
        dryrun,
        dc_run,
        dc_content,
        dockerfile_content,
        dockerhub_statuscode,
    ):  # pylint: disable=unused-argument
        """ Test the run method
        :returns: None

        """
        path = os.path.join("./src/test/example_services_test_run/", path)
        updater = Updater(path, dryrun)
        with mock.patch(
            "src.docker_compose_update.subprocess"
        ) as subprocess_mock, mock.patch(
            "src.docker_compose_update.write_email"
        ), mock.patch(
            "src.docker_compose_update.requests"
        ) as request_mock:
            request_mock.get = mock.Mock(
                side_effect=request_dockerhub(dockerhub_statuscode)
            )

            updater.run()
            assert subprocess_mock.run.called == dc_run
        docker_compose_path = os.path.join(path, "docker-compose.yml")
        with open(docker_compose_path) as docker_compose_file:
            docker_compose = docker_compose_file.readlines()
        if dc_content is not None:
            assert docker_compose[4] == dc_content
        if dockerfile_content is not None:
            dockerfile_path = os.path.join(path, "Dockerfile")
            with open(dockerfile_path) as docker_compose_file:
                dockerfile = docker_compose_file.readlines()
            assert dockerfile[1] == dockerfile_content

    def test_subprocess_error(
        self, example_services
    ):  # pylint: disable=unused-argument
        updater = Updater("./src/test/example_services_test_run/", False)
        with mock.patch(
            "src.docker_compose_update.subprocess.run"
        ) as subprocess_run, mock.patch("src.docker_compose_update.write_email"):
            subprocess_run.side_effect = subprocess.CalledProcessError(2, "testcommand")
            updater.build()
            assert subprocess_run.called
            subprocess_run.reset_mock()
            updater.up()
            assert subprocess_run.called

    def test_read_not_found(self, example_services):  # pylint: disable=unused-argument
        updater = Updater("./src/test/example_services_test_run/", False)
        with mock.patch("src.docker_compose_update.sys.exit") as exit_patch:
            exit_patch.side_effect = SystemExit
            try:
                updater.read()
            except SystemExit:
                pass
            assert exit_patch.called

    def test_write_to_empty_docker_compose(
        self, example_services
    ):  # pylint: disable=unused-argument
        docker_compose_path = (
            "./src/test/example_services_test_run/docker_compose_empty"
        )
        updater = Updater(docker_compose_path, False)
        updater.write_to_docker_compose(None, None)
        with open(
            os.path.join(docker_compose_path, "docker-compose.yml")
        ) as docker_compose_file:
            docker_compose = docker_compose_file.readlines()
        assert docker_compose == []

    def test_write_to_empty_dockerfile(
        self, example_services
    ):  # pylint: disable=unused-argument
        path = "./src/test/example_services_test_run/dockerfile_empty"
        updater = Updater(path, False)
        dockerfile_path = os.path.join(path, "Dockerfile")
        service = Service("", "", "", dockerfile_path)
        updater.write_to_dockerfile(service)
        with open(dockerfile_path, "r") as docker_compose_file:
            dockerfile = docker_compose_file.readlines()
        assert dockerfile == []

    @pytest.mark.parametrize(
        "loglevel_str", ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", ""]
    )
    def test_initialize_logging(self, loglevel_str):
        with mock.patch("src.docker_compose_update.os") as os_mock, mock.patch(
            "src.docker_compose_update.logging"
        ) as logging:
            loglevel = {
                "CRITICAL": logging.CRITICAL,
                "ERROR": logging.ERROR,
                "WARNING": logging.WARNING,
                "INFO": logging.INFO,
                "DEBUG": logging.DEBUG,
                "": logging.INFO,
            }
            if loglevel_str:
                os_mock.environ = {"LOGLEVEL": loglevel_str}
            else:
                os_mock.environ = {}
            initialize_logging()
            logging.getLogger().setLevel.assert_called_with(loglevel[loglevel_str])

    def test_initialize_logging_error(self):
        with mock.patch("src.docker_compose_update.os") as os_mock, mock.patch(
            "src.docker_compose_update.logging", autospec=True
        ) as logging_mock:
            os_mock.environ = {"LOGLEVEL": "DUMMY"}
            try:
                initialize_logging()
                assert False
            except SystemExit:
                pass
            assert not logging_mock.getLogger().setLevel.called
            assert logging_mock.error.called

    def test_get_docker_compose_directories(
        self, example_services
    ):  # pylint: disable=unused-argument
        directories = get_docker_compose_directories(
            "src/test/example_services_test_run"
        )
        directory_list = list(directories)
        for test_directory in [
            "src/test/example_services_test_run/empty_versions",
            "src/test/example_services_test_run/up_to_date",
            "src/test/example_services_test_run/base",
            "src/test/example_services_test_run/manual_update",
            "src/test/example_services_test_run/dockerfile_base",
            "src/test/example_services_test_run/manual_update_only",
            "src/test/example_services_test_run/auto_update_only",
            "src/test/example_services_test_run/key_error",
            "src/test/example_services_test_run/docker_compose_empty",
            "src/test/example_services_test_run/dockerfile_empty",
            "src/test/example_services_test_run/no_init_version",
            "src/test/example_services_test_run/yaml_error_in_versions",
            "src/test/example_services_test_run/docker_compose_versions_in_subdir",
        ]:
            assert test_directory in directory_list
        for test_directory in [
            "src/test/example_services_test_run/empty_dir",
            "src/test/example_services_test_run/docker_compose_versions_in_subdir"
            + "/subdir",
            "src/test/example_services_test_run/ignorefile",
        ]:
            assert test_directory not in directory_list


def request_dockerhub(status_code):
    """
    Returns a function that models a response form requests.get
    """
    # Build request wrapper to return
    def request_wrapper(*args):
        """
        Models a response from requests.get
        The response depends on the request url in args[0]
        """
        response_json = {
            "count": 8,
            "next": "https://bla.example.com",
            "results": [
                {"images": [{"architecture": "amd64"}], "name": "latest"},
                {"images": [{"architecture": "amd64"}], "name": "3"},
                {"images": [{"architecture": "amd64"}], "name": "3.7.6-buster"},
                {"images": [{"architecture": "amd64"}], "name": "3.7-buster"},
                {"images": [{"architecture": "amd64"}], "name": "3.8.2-buster"},
                {"images": [{"architecture": "dummy"}], "name": "3.9.2-buster"},
                {"images": [{"architecture": "amd64"}], "name": "3.8-buster"},
                {"images": [{"architecture": "amd64"}], "name": "3-buster"},
                {"images": [{"architecture": "amd64"}], "name": "buster"},
            ],
        }
        response = requests.Response()
        response.status_code = status_code
        response.json = mock.Mock(return_value=response_json)
        # If this is a request that tries to get the next part from a previouse
        # response return something without a next part
        if args[0] == "https://bla.example.com":
            response_json["next"] = None
            response.json = mock.Mock(return_value=response_json)
        return response

    return request_wrapper
