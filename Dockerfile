FROM python:3.11-slim

RUN apt update && apt install nodejs npm -y

COPY client/package.json /code/client/package.json
COPY client/package-lock.json /code/client/package-lock.json
WORKDIR code/client
RUN npm install

WORKDIR /code

ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VIRTUALENVS_IN_PROJECT=false
ENV POETRY_NO_INTERACTION=1
RUN pip install poetry==2.0.0

COPY poetry.lock /code
COPY pyproject.toml /code

RUN poetry install --with dev

RUN mkdir -p /code
COPY . /code

ENV PYTHONPATH=.
