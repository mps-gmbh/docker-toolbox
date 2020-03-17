all: test lint
test:
	make env-test
	env-test/bin/pytest --cov-report term-missing --cov=src

env-build:
	virtualenv env-build --python=$(which python3)
	env-build/bin/pip install pip-tools
	touch env-build
env-test: test-requirements.txt requirements.txt
	virtualenv env-test --python=$(which python3)
	env-test/bin/pip install -r test-requirements.txt  
	env-test/bin/pip install -r requirements.txt
	touch env-test

clean:
	rm -rf env-build/
	rm -rf env-test/

lint: env-test
	env-test/bin/black --check ./src/docker_compose_update.py
fix-lint: env-test
	env-test/bin/black ./src/docker_compose_update.py

requirements: requirements.txt
requirements.txt: env-build requirements.in
	env-build/bin/pip-compile requirements.in

test-requirements: test-requirements.txt
test-requirements.txt: test-requirements.in env-build
	env-build/bin/pip-compile test-requirements.in