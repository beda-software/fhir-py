#!/bin/bash

export TEST_COMMAND="pipenv run pytest ${@:-tests/}"
docker compose -f docker-compose.tests.yaml up --quiet-pull --exit-code-from app app
