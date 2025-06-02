FROM python:3.11-slim




WORKDIR /code

ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VIRTUALENVS_IN_PROJECT=false
ENV POETRY_NO_INTERACTION=1
RUN pip install poetry==2.0.0

## Copy dependency definitions
COPY poetry.lock /code
COPY pyproject.toml /code

RUN poetry install --with dev

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs

RUN mkdir -p /code
COPY . /code
WORKDIR /code

#RUN pip3 install --upgrade pip
#RUN pip3 install .

#COPY ./appdirs/ /root/.local/share/

#RUN apt-get update && apt-get install --yes --force-yes curl git

#RUN curl -sL https://deb.nodesource.com/setup_14.x -o /tmp/nodesource_setup.sh
#RUN bash /tmp/nodesource_setup.sh
#RUN apt-get update && apt-get install nodejs
#
#RUN apt -y install gnupg2
#RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
#RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" | tee  /etc/apt/sources.list.d/pgdg.list
#RUN apt update
#RUN apt install -y postgresql-client-13

CMD ["bash", "./entrypoint.sh"]


