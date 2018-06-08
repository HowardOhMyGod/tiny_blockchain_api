from flask_server import socketio, app
from flask_socketio import send, emit
import eventlet

eventlet.monkey_patch()

@socketio.on('message')
def handle_message(json):
    print(json)
    emit('server_res', "hello client!")

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)