import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


db_url = "postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}".format(
    db_user="user",
    db_password="pass",
    db_host=os.environ.get("DB_HOST", "localhost"),
    db_port="5432",
    db_name="hexfow",
)

engine = create_engine(db_url, executemany_mode="values_plus_batch")

session_factory = sessionmaker(bind=engine)
SS = scoped_session(session_factory)
