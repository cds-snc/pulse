import flask
import pytest
from flask_pymongo import PyMongo
from pulse import models


@pytest.fixture(autouse=True)
def app_setup(app) -> None:
    with app.app_context():
        yield


def test_default_db_name() -> None:
    assert models.db.db.name.startswith('pulse')



