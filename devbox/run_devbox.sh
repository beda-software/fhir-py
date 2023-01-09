#!/bin/sh
if [ -f ".env" ]; then
    export `cat .env`
fi

if [ -z "${AIDBOX_LICENSE}" ]; then
    echo "AIDBOX_LICENSE is required to run tests"
    exit 1
fi

docker compose -f docker-compose.tests.yaml up --exit-code-from devbox devbox
exit $?
