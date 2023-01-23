all: test lint
test:
	make env-test
	env-test/bin/pytest --cov-report term-missing --cov=src

env-build:
	virtualenv env-build --python=$(which python3)
	env-build/bin/pip install pip-tools
	touch env-build
env-test: test-requirements.txt requirements.txt
	python3 -m venv env-test
	env-test/bin/pip install -r test-requirements.txt  
	env-test/bin/pip install -r requirements.txt
	touch env-test

clean:
	rm -rf env-build/
	rm -rf env-test/

lint: env-test
	make black
	make pylint
	make flake8

flake8: env-test
	env-test/bin/flake8 src
pylint: env-test
	env-test/bin/pylint --fail-under=9 src
black: env-test
	env-test/bin/black --check src
fix-black: env-test
	env-test/bin/black src

requirements: requirements.txt
requirements.txt: env-build requirements.in
	env-build/bin/pip-compile requirements.in

test-requirements: test-requirements.txt
test-requirements.txt: test-requirements.in env-build
	env-build/bin/pip-compile test-requirements.in
