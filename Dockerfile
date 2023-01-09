ARG PYTHON_VERSION
FROM python:$PYTHON_VERSION
RUN pip install pipenv

RUN mkdir /app
WORKDIR /app

COPY Pipfile Pipfile.lock ./
RUN pipenv install --dev

# SQLAlchemy vulnerability - https://pyup.io/v/51668/742
# Remove ignore option once fix is released or upgrade to version 2
# RUN pipenv check -i 51668
COPY . .

EXPOSE 8081
