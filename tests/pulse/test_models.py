import os
import socket
import typing
import flask
import pytest
from flask_pymongo import PyMongo
from pulse import create_app
from pulse import models


def local_mongo_is_running() -> bool:
    if 'CIRCLECI' in os.environ:
        return True

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 27017))
    except socket.error:
        return True
    else:
        sock.close()
        return False


@pytest.fixture()
def database_uri() -> typing.Iterator[str]:
    if not local_mongo_is_running():
        pytest.skip('Local MongoDB instance is not running.')
    return 'mongodb://localhost:27017'


@pytest.fixture()
def app(database_uri: str, monkeypatch) -> flask.Flask:
    app = create_app()
    app.config['TESTING'] = True

    app.config['MONGO_TEST_URI'] = database_uri
    mongo = PyMongo(app, config_prefix='MONGO_TEST')
    monkeypatch.setattr(models, 'db', mongo)
    return app

class TestDatabase():

    @pytest.fixture(autouse=True)
    def app_setup(self, app) -> None:
        with app.app_context():
            yield

    def test_default_db_name(self) -> None:
        assert models.db.db.name == 'pulse'
