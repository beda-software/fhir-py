#!/bin/bash

export TEST_COMMAND="pipenv run pytest ${@:-tests/} -vv"
docker compose -f docker-compose.tests.yaml up --quiet-pull --exit-code-from app app
