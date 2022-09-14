import sqlalchemy
from sqlalchemy.orm.session import sessionmaker


class DBClient:

    def __init__(self, db_url) -> None:
        self.db_url = db_url
        self.engine = sqlalchemy.create_engine(db_url)
        self.metadata = sqlalchemy.MetaData(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.tables = {}

    def transaction(self):
        return ContextManager(self.session_factory)

    def session(self):
        return self.session_factory()

    def drop_all(self):
        self.metadata.reflect()
        self.session_factory.close_all()
        self.metadata.drop_all()


class ContextManager:

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self.session = None

    def __enter__(self):
        self.session = self.session_factory()
        return self.session

    def __exit__(self, exc_type, exc_value, tb):
        if tb is None:
            self.session.commit()
        else:
            self.session.rollback()
