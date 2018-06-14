from flask import Flask
from flask_compress import Compress

def create_app(environment='development'):
    app = Flask(__name__, instance_relative_config=True)

    # Gzip compress most things
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml',
        'text/csv', 'application/json', 'application/javascript'
    ]
    if environment == 'development':
        app.config.from_object('track.config.DevelopmentConfig')
    elif environment == 'testing':
        app.config.from_object('track.config.TestingConfig')
    else:
        app.config.from_object('track.config.ProductionConfig')
        import logging.handlers
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        handler.setLevel(app.config.get('LOGLEVEL'))
        app.logger.addHanlder(handler)

    app.config.from_pyfile('application.cfg', silent=True)
    app.logger.info(app.config.get("INSTANCE_TEST_VARIABLE"))
    Compress(app)

    from track.cache import cache
    cache.init_app(app)

    from track import views
    views.register(app)

    from track import helpers
    helpers.register(app)

    from track.models import db
    db.init_app(app)

    return app
