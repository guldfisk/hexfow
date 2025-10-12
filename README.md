## Running locally
Build the docker image:
```
docker compose build
```

Install frontend dependencies:
```
docker compose run client npm install
```

Init the database:
```
docker compose run web-server python init_db.py
```

Start the project:
```
docker compose up
```

Confirm it runs at http://localhost:5173/play/?seat=test

## Dev environment
Create and activate python virtual environment (with python 3.11+):
```
python -m venv .venv
source .venv/bin/activate
```

Install dependencies (if you don't have poetry installed globally, you should be
able to get away with installing it locally in the same venv first,
`pip install poetry`):
```
poetry install --with dev
```

Setup pre-commit hooks:
```
pre-commit install
```