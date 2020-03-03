import shutil
import pytest
import os
import requests
import subprocess
import argparse
from unittest import mock
from src.docker_compose_update import Updater
from src.docker_compose_update import Service
from src.docker_compose_update import get_commandline_arguments


class TestDockerComposeUpdate:
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
        yield
        shutil.rmtree("./src/test/example_services_test_run")

    @pytest.mark.parametrize(
        "path, dryrun, dc_run, dc_content, dockerfile_content, dockerhub_statuscode",
        [
            ("base", True, False, "    image: python:latest\n", None, 200),
            ("base", True, False, "    image: python:latest\n", None, 404),
            ("base", False, True, "    image: python:3.8.2-buster\n", None, 200),
            ("base", False, False, "    image: python:latest\n", None, 404),
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
                "FROM python:3.8.2-buster \n",
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
    ):
        """ Test the run method
        :returns: None

        """
        path = os.path.join("./src/test/example_services_test_run/", path)
        updater = Updater(path, dryrun)
        with mock.patch(
            "src.docker_compose_update.subprocess"
        ) as subprocess, mock.patch(
            "src.docker_compose_update.write_email"
        ), mock.patch(
            "src.docker_compose_update.requests"
        ) as request_mock:
            response = requests.Response()
            response.status_code = dockerhub_statuscode
            response.json = mock.Mock(
                return_value=(
                    [
                        {"layer": "", "name": "latest"},
                        {"layer": "", "name": "3"},
                        {"layer": "", "name": "3.7.6-buster"},
                        {"layer": "", "name": "3.7-buster"},
                        {"layer": "", "name": "3.8.2-buster"},
                        {"layer": "", "name": "3.8-buster"},
                        {"layer": "", "name": "3-buster"},
                        {"layer": "", "name": "buster"},
                    ]
                )
            )
            request_mock.get = mock.Mock(return_value=response)

            updater.run()
            assert subprocess.run.called == dc_run
        docker_compose_path = os.path.join(path, "docker-compose.yml")
        with open(docker_compose_path) as f:
            docker_compose = f.readlines()
        if dc_content is not None:
            assert docker_compose[4] == dc_content
        if dockerfile_content is not None:
            dockerfile_path = os.path.join(path, "Dockerfile")
            with open(dockerfile_path) as f:
                dockerfile = f.readlines()
            assert dockerfile[1] == dockerfile_content

    def test_subprocess_error(self, example_services):
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

    def test_read_not_found(self, example_services):
        updater = Updater("./src/test/example_services_test_run/", False)
        with mock.patch("src.docker_compose_update.exit") as exit_patch:
            exit_patch.side_effect = SystemExit
            try:
                updater.read()
            except SystemExit:
                pass
            assert exit_patch.called

    def test_write_to_empty_docker_compose(self, example_services):
        docker_compose_path = (
            "./src/test/example_services_test_run/docker_compose_empty"
        )
        updater = Updater(docker_compose_path, False)
        updater.write_to_docker_compose(None, None)
        with open(os.path.join(docker_compose_path, "docker-compose.yml")) as f:
            docker_compose = f.readlines()
        assert docker_compose == []

    def test_write_to_empty_dockerfile(self, example_services):
        path = "./src/test/example_services_test_run/dockerfile_empty"
        updater = Updater(path, False)
        dockerfile_path = os.path.join(path, "Dockerfile")
        service = Service("", "", "", dockerfile_path)
        updater.write_to_dockerfile(service)
        with open(dockerfile_path, "r") as f:
            dockerfile = f.readlines()
        assert dockerfile == []
