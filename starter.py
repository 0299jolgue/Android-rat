from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import jwt
import os
import time
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET', 'change_me')
JWT_SECRET = os.environ.get('JWT_SECRET', 'change_me')

# Admin credentials (default as requested)
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

# Use threading mode to avoid requiring eventlet/gevent native extensions
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# In-memory device registry: deviceId -> {socket_sid, last_seen, meta}
devices = {}

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapped

# --------------------------------------------------
# Web pages
# --------------------------------------------------
@app.route('/')
@admin_required
def index():
    return render_template('index.html')

@app.route('/devices')
@admin_required
def devices_page():
    return render_template('devices.html')

@app.route('/device/<device_id>')
@admin_required
def device_page(device_id):
    return render_template('device.html', device_id=device_id)

# Login / logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    form = request.form
    username = form.get('username')
    password = form.get('password')
    next_url = request.args.get('next') or url_for('index')
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['admin'] = True
        session['admin_user'] = username
        return redirect(next_url)
    return render_template('login.html', error='Credenciais inválidas')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('admin_user', None)
    return redirect(url_for('login'))

# --------------------------------------------------
# API endpoints
# --------------------------------------------------
@app.route('/api/register', methods=['POST'])
def api_register():
    body = request.get_json() or {}
    device_id = body.get('deviceId')
    name = body.get('name')
    if not device_id:
        return jsonify({'error':'deviceId required'}), 400
    # Create short-lived JWT for device handshake
    token = jwt.encode({'deviceId': device_id, 'iat': int(time.time())}, JWT_SECRET, algorithm='HS256')
    # store meta
    devices[device_id] = {'socket_sid': None, 'last_seen': None, 'meta': {'name': name}}
    return jsonify({'deviceToken': token})

@app.route('/api/devices', methods=['GET'])
@admin_required
def api_list_devices():
    # Return list of known devices with online status
    out = []
    for did, info in devices.items():
        out.append({'deviceId': did, 'online': bool(info['socket_sid']), 'last_seen': info['last_seen'], 'meta': info['meta']})
    return jsonify(out)

@app.route('/api/devices/<device_id>/command', methods=['POST'])
@admin_required
def api_send_command(device_id):
    body = request.get_json() or {}
    allowed = ['PING', 'REQUEST_STATUS', 'UPLOAD_LOGS']
    cmd_type = body.get('type')
    data = body.get('data', {})
    if cmd_type not in allowed:
        return jsonify({'error':'invalid command'}), 400
    info = devices.get(device_id)
    if not info or not info.get('socket_sid'):
        return jsonify({'error':'device offline'}), 404
    socketio.emit('command', {'type': cmd_type, 'data': data}, room=info['socket_sid'])
    return jsonify({'sent': True})

# Health
@app.route('/health')
def health():
    return 'ok'

# --------------------------------------------------
# Socket.IO handlers (devices connect here)
# --------------------------------------------------
@socketio.on('connect')
def on_connect():
    # Expect devices to authenticate via 'auth' event immediately
    emit('connected', {'msg':'connected, send auth token via `auth` event'})

@socketio.on('auth')
def on_auth(data):
    token = data.get('token')
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        device_id = claims.get('deviceId')
        # register socket
        devices.setdefault(device_id, {'socket_sid': None, 'last_seen': None, 'meta': {}})
        devices[device_id]['socket_sid'] = request.sid
        devices[device_id]['last_seen'] = time.time()
        join_room(request.sid)
        emit('auth_ok')
        # notify admins that device is online
        socketio.emit('device_event', {'type':'device_online','deviceId':device_id})
    except Exception as e:
        emit('auth_fail', {'error': str(e)})
        return

@socketio.on('disconnect')
def on_disconnect():
    # find device by sid and clear
    sid = request.sid
    for did, info in list(devices.items()):
        if info.get('socket_sid') == sid:
            devices[did]['socket_sid'] = None
            devices[did]['last_seen'] = time.time()
            socketio.emit('device_event', {'type':'device_offline','deviceId':did})
            break

@socketio.on('response')
def on_response(msg):
    # devices send responses which are broadcast to admin channel
    device_sid = request.sid
    # find device id
    device_id = None
    for did, info in devices.items():
        if info.get('socket_sid') == device_sid:
            device_id = did; break
    socketio.emit('device_event', {'deviceId': device_id, **msg})

# --------------------------------------------------
# Starter entrypoint
# --------------------------------------------------
if __name__ == '__main__':
    # Bind to 0.0.0.0:80 as requested
    port = int(os.environ.get('PORT', 80))
    print(f"Starting Flask SocketIO server on 0.0.0.0:{port} (async_mode=threading)")
    # Try normal run first; if Werkzeug safety check blocks, retry allowing unsafe werkzeug
    try:
        socketio.run(app, host='0.0.0.0', port=port)
    except RuntimeError as e:
        print('Werkzeug safety check blocked run():', e)
        print('Retrying with allow_unsafe_werkzeug=True')
        socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
