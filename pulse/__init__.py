from flask import Flask
from flask_compress import Compress

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Gzip compress most things
    app.config['COMPRESS_MIMETYPES'] = [
      'text/html', 'text/css', 'text/xml',
      'text/csv', 'application/json', 'application/javascript'
    ]
    app.config.from_object('pulse.config')
    app.config.from_pyfile('application.cfg', silent=True)
    Compress(app)

    from pulse import views
    views.register(app)

    from pulse import helpers
    helpers.register(app)

    from pulse.models import db
    db.init_app(app)

    return app
