#!/usr/bin/env python3
"""RUN – VR Horror multiplayer server.

Zero dependencies (Python 3.9+). One process does two jobs:
  * serves the game files from ./public over HTTP
  * relays player positions between players in the same room over WebSocket at /ws
Run:  python server.py        (PORT env var sets the port, default 8080)
"""
import asyncio, base64, hashlib, json, math, mimetypes, os, re, struct, time, uuid
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "public")
PORT = int(os.environ.get("PORT", "8080"))
MAX_PER_ROOM = int(os.environ.get("MAX_PER_ROOM", "12"))
MAX_FRAME = 8192
GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,47}$")
LOOK_RE = re.compile(r"^[a-z]{1,12}\|[a-z]{1,12}\|[a-z]{1,12}$")
mimetypes.add_type("application/manifest+json", ".webmanifest")
rooms = {}  # room name -> {client id: Client}


def frame(payload: bytes, op: int = 1) -> bytes:
    n = len(payload)
    head = bytes([0x80 | op])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack(">H", n)
    else:
        head += bytes([127]) + struct.pack(">Q", n)
    return head + payload


async def read_frame(reader):
    b = await reader.readexactly(2)
    fin, op, masked, n = b[0] & 0x80, b[0] & 0x0F, b[1] & 0x80, b[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", await reader.readexactly(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", await reader.readexactly(8))[0]
    if n > MAX_FRAME or not masked:
        raise ValueError("bad frame")
    mask = await reader.readexactly(4)
    data = bytearray(await reader.readexactly(n))
    for i in range(n):
        data[i] ^= mask[i % 4]
    return fin, op, bytes(data)


class Client:
    def __init__(self, writer):
        self.writer = writer
        self.id = uuid.uuid4().hex[:8]
        self.room = None
        self.pres = {}
        self.last = 0.0
        self.tokens = 40.0
        self.tt = time.monotonic()
        self.seen = time.monotonic()

    async def send(self, obj):
        try:
            self.writer.write(frame(json.dumps(obj, separators=(",", ":")).encode()))
            await self.writer.drain()
        except Exception:
            pass


def vec(v):
    if isinstance(v, list) and len(v) == 3:
        try:
            out = [float(x) for x in v]
        except (TypeError, ValueError):
            return None
        if all(math.isfinite(x) for x in out):
            return [round(max(-2000.0, min(2000.0, x)), 2) for x in out]
    return None


def clean_pres(raw):
    out = {}
    if not isinstance(raw, dict):
        return out
    for k in ("p", "l", "r"):
        v = vec(raw.get(k))
        if v:
            out[k] = v
    try:
        q = float(raw.get("q", 0))
        if math.isfinite(q):
            out["q"] = round(q, 2)
    except (TypeError, ValueError):
        pass
    k = raw.get("k")
    if isinstance(k, str) and LOOK_RE.match(k):
        out["k"] = k
    for f in ("it", "zn"):
        if raw.get(f) in (0, 1):
            out[f] = int(raw[f])
    return out


async def broadcast(room, msg, skip=None):
    members = list(rooms.get(room, {}).values())
    await asyncio.gather(*(o.send(msg) for o in members if o is not skip))


async def leave(c):
    r, c.room = c.room, None
    if r is None:
        return
    m = rooms.get(r)
    if m is None:
        return
    m.pop(c.id, None)
    if not m:
        rooms.pop(r, None)
    else:
        await broadcast(r, {"t": "left", "id": c.id, "r": r})


async def join(c, name):
    if not NAME_RE.match(name):
        await c.send({"t": "error", "m": "bad room name"})
        return
    if c.room != name:
        if len(rooms.get(name, {})) >= MAX_PER_ROOM:
            await c.send({"t": "error", "m": "room full"})
            return
        await leave(c)
        rooms.setdefault(name, {})[c.id] = c
        c.room, c.pres = name, {}
    peers = [{"id": o.id, "p": o.pres} for o in rooms[name].values() if o is not c]
    await c.send({"t": "welcome", "id": c.id, "room": name, "peers": peers})


async def on_message(c, raw):
    now = time.monotonic()
    c.tokens = min(40.0, c.tokens + (now - c.tt) * 30)
    c.tt = now
    if c.tokens < 1:
        return
    c.tokens -= 1
    try:
        o = json.loads(raw)
    except ValueError:
        return
    if not isinstance(o, dict):
        return
    t = o.get("t")
    if t == "join":
        await join(c, str(o.get("room", "lobby")).lower())
    elif t == "p" and c.room:
        if now - c.last < 0.03:
            return
        c.last = now
        c.pres = clean_pres(o.get("p"))
        await broadcast(c.room, {"t": "p", "id": c.id, "r": c.room, "p": c.pres}, skip=c)


async def ws_session(reader, writer, hdr):
    key = hdr.get("sec-websocket-key")
    if not key:
        writer.close()
        return
    accept = base64.b64encode(hashlib.sha1(key.encode() + GUID).digest()).decode()
    writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                  "Connection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
    await writer.drain()
    c = Client(writer)

    async def pinger():
        while True:
            await asyncio.sleep(20)
            if time.monotonic() - c.seen > 55:
                writer.close()
                return
            try:
                writer.write(frame(b"", 9))
            except Exception:
                return

    ping = asyncio.create_task(pinger())
    buf = bytearray()
    try:
        while True:
            fin, op, data = await read_frame(reader)
            c.seen = time.monotonic()
            if op == 8:
                break
            if op == 9:
                writer.write(frame(data, 10))
            elif op in (0, 1):
                buf += data
                if len(buf) > MAX_FRAME:
                    break
                if fin:
                    msg = bytes(buf)
                    buf.clear()
                    await on_message(c, msg)
    except (asyncio.IncompleteReadError, ConnectionError, ValueError, OSError):
        pass
    finally:
        ping.cancel()
        await leave(c)
        try:
            writer.close()
        except Exception:
            pass


async def serve_static(writer, method, path):
    def respond(code, reason, body=b"", ctype="text/plain; charset=utf-8", extra=""):
        head = (f"HTTP/1.1 {code} {reason}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n"
                f"Connection: close\r\n{extra}\r\n").encode()
        writer.write(head + (b"" if method == "HEAD" else body))

    if method not in ("GET", "HEAD"):
        return respond(405, "Method Not Allowed")
    if path == "/healthz":
        return respond(200, "OK", b"ok")
    rel = "index.html" if path in ("", "/") else path.lstrip("/")
    full = os.path.normpath(os.path.join(PUBLIC, rel))
    if not full.startswith(PUBLIC + os.sep) or not os.path.isfile(full):
        return respond(404, "Not Found", b"not found")
    with open(full, "rb") as f:
        body = f.read()
    ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/manifest+json"):
        ctype += "; charset=utf-8"
    respond(200, "OK", body, ctype, "Cache-Control: no-cache\r\n")


async def handle(reader, writer):
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
        lines = head.decode("latin1").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        hdr = {}
        for ln in lines[1:]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                hdr[k.strip().lower()] = v.strip()
        path = unquote(path.split("?", 1)[0])
        if path == "/ws" and "websocket" in hdr.get("upgrade", "").lower():
            await ws_session(reader, writer, hdr)
            return
        await serve_static(writer, method, path)
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", PORT)
    print(f"RUN server listening on :{PORT}  (game at /, websocket at /ws)", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
