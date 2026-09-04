const express = require('express');
const http = require('http');
const jwt = require('jsonwebtoken');
const { Server } = require('socket.io');

const app = express();
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*' } });

const JWT_SECRET = process.env.JWT_SECRET || 'change_me';
const PORT = process.env.PORT || 3000;

// In-memory mapping deviceId -> socket
const deviceSockets = new Map();

function findSocketForDevice(deviceId) {
  return deviceSockets.get(deviceId) || null;
}

function joinDeviceRoom(socket, deviceId) {
  deviceSockets.set(deviceId, socket);
  socket.join(`device:${deviceId}`);
}

function leaveDeviceRoom(socket) {
  const deviceId = socket.data.deviceId;
  if (deviceId) deviceSockets.delete(deviceId);
}

// --------------------------------------------------
// Simple auth middleware for admin routes (JWT)
// --------------------------------------------------
function requireAuth(req, res, next) {
  const auth = req.headers.authorization?.split(' ')[1];
  if (!auth) return res.status(401).send('unauthorized');
  try {
    req.claims = jwt.verify(auth, JWT_SECRET);
    next();
  } catch (e) { return res.status(401).send('unauthorized'); }
}

// --------------------------------------------------
// REST endpoints
// Note: Integrate with DB in place of in-memory stubs
// --------------------------------------------------

// Registro inicial do device (cliente fornece deviceId e meta)
app.post('/api/register', (req, res) => {
  const { deviceId, name } = req.body || {};
  if (!deviceId) return res.status(400).json({ error: 'deviceId required' });
  // Persistir device em DB aqui (ex: devices table)
  // Gerar um token curto para handshake do device
  const deviceToken = jwt.sign({ deviceId }, JWT_SECRET, { expiresIn: '24h' });
  return res.json({ deviceToken });
});

// Lista devices (exemplo protegido)
app.get('/api/devices', requireAuth, (req, res) => {
  // Substituir com fetch do DB
  // Para demo, retornamos sockets conectados
  const list = Array.from(deviceSockets.keys()).map(id => ({ deviceId: id, online: true }));
  return res.json(list);
});

// Envia comando predefinido para device (via socket)
app.post('/api/devices/:id/command', requireAuth, (req, res) => {
  const payload = { type: req.body.type, data: req.body.data || {} };
  const allowed = ['PING', 'REQUEST_STATUS', 'UPLOAD_LOGS'];
  if (!allowed.includes(payload.type)) return res.status(400).send('invalid command');
  const socket = findSocketForDevice(req.params.id);
  if (!socket) return res.status(404).send('device offline');
  socket.emit('command', payload);
  // TODO: logar ação em DB: admin, device, tipo, timestamp
  return res.json({ sent: true });
});

// Health
app.get('/health', (req, res) => res.send('ok'));

// --------------------------------------------------
// Socket.IO handling
// --------------------------------------------------
io.on('connection', (socket) => {
  console.log('ws: connection', socket.id);

  socket.on('auth', (token) => {
    try {
      const claims = jwt.verify(token, JWT_SECRET);
      socket.data.deviceId = claims.deviceId;
      joinDeviceRoom(socket, claims.deviceId);
      console.log('device auth ok', claims.deviceId);
      socket.emit('auth_ok');
    } catch (e) {
      socket.emit('auth_fail');
      socket.disconnect(true);
    }
  });

  socket.on('response', (msg) => {
    // msg expected: { type, data, timestamp }
    console.log('response from', socket.data.deviceId, msg.type);
    // Persist into DB or forward to admin WS channel
    // Example: emit to any admin room listening for device events
    io.to(`admins`).emit('device_event', { deviceId: socket.data.deviceId, ...msg });
  });

  socket.on('disconnect', (reason) => {
    console.log('ws: disconnect', socket.id, reason);
    leaveDeviceRoom(socket);
  });
});

server.listen(PORT, () => console.log(`server up on ${PORT}`));
