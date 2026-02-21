from flask_socketio import SocketIO

# db is defined in models, but often extensions are together.
# However, I already have db in models/__init__.py.
# I will only put socketio here, or other extensions.

socketio = SocketIO(cors_allowed_origins="*")
