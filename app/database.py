from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)
