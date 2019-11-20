#!/bin/sh

if [ -z "${AIDBOX_LICENSE_KEY_TESTS}" ]; then
    echo "AIDBOX_LICENSE_KEY_TESTS is required to run tests"
    exit 1
fi

if [ -z "${AIDBOX_LICENSE_ID_TESTS}" ]; then
    echo "AIDBOX_LICENSE_ID_TESTS is required to run tests"
    exit 1
fi

docker-compose -f docker-compose.tests.yaml up -d
./wait-for-it.sh localhost:8080
exit $?
