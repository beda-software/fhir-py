#!/bin/bash

docker compose -f docker-compose.tests.yaml up --quiet-pull --exit-code-from app app
