#!/usr/bin/env python3
"""
小K家庭电话
局域网内：直接用局域网IP
外网：绑定后通过信令服务器中转（需要公网访问，可配合frp/花生壳）

依赖：pip install websockets
"""
import asyncio, json, os, sys, threading, webbrowser
import tkinter as tk
from tkinter import scrolledtext
import websockets

HOST = "0.0.0.0"
WS_PORT = 8765
HTTP_PORT = 8080

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 在线用户：{name: websocket}
_clients: dict = {}
# 通话中：{caller: callee}
_calls: dict = {}

BG="#1e1e2e"; BG2="#2a2a3e"; ACCENT="#7c9ef8"; ACCENT2="#a6e3a1"
DANGER="#f38ba8"; TEXT="#cdd6f4"; TEXT_DIM="#6c7086"

# ══════════════════════════════════════════════════════
# WebSocket 信令服务器
# ══════════════════════════════════════════════════════
async def _handle(ws):
    name = None
    try:
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "register":
                name = msg["name"]
                _clients[name] = ws
                await _broadcast({"type":"online","users": list(_clients.keys())})
                _log(f"📱 {name} 上线")

            elif t == "call":
                target = msg["to"]
                if target in _clients:
                    await _clients[target].send(json.dumps(
                        {"type":"incoming","from": name}))
                else:
                    await ws.send(json.dumps({"type":"error","msg":"对方不在线"}))

            elif t == "answer":
                caller = msg["to"]
                if caller in _clients:
                    await _clients[caller].send(json.dumps(
                        {"type":"answered","from": name}))
                    _calls[caller] = name
                    _calls[name] = caller

            elif t == "reject":
                caller = msg["to"]
                if caller in _clients:
                    await _clients[caller].send(json.dumps(
                        {"type":"rejected","from": name}))

            elif t == "hangup":
                peer = _calls.pop(name, None)
                if peer:
                    _calls.pop(peer, None)
                    if peer in _clients:
                        await _clients[peer].send(json.dumps(
                            {"type":"hangup","from": name}))

            # WebRTC 信令转发
            elif t in ("offer","answer_sdp","ice"):
                target = msg.get("to")
                if target and target in _clients:
                    msg["from"] = name
                    await _clients[target].send(json.dumps(msg))

    except Exception:
        pass
    finally:
        if name and name in _clients:
            del _clients[name]
            _calls.pop(name, None)
            await _broadcast({"type":"online","users": list(_clients.keys())})
            _log(f"📴 {name} 下线")

async def _broadcast(msg):
    if _clients:
        data = json.dumps(msg, ensure_ascii=False)
        await asyncio.gather(*[c.send(data) for c in _clients.values()],
                             return_exceptions=True)

_log_fn = print
def _log(msg):
    _log_fn(msg)

# ══════════════════════════════════════════════════════
# HTTP 服务器（提供网页客户端）
# ══════════════════════════════════════════════════════
_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小K家庭电话</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#1e1e2e;color:#cdd6f4;font-family:'微软雅黑',sans-serif;
     display:flex;flex-direction:column;align-items:center;min-height:100vh;padding:20px}
h1{color:#7c9ef8;margin:20px 0 10px;font-size:1.4em}
#login,#main{width:100%;max-width:400px}
input{width:100%;padding:12px;background:#2a2a3e;border:1px solid #45475a;
      border-radius:8px;color:#cdd6f4;font-size:1em;margin:8px 0}
button{width:100%;padding:12px;border:none;border-radius:8px;font-size:1em;
       cursor:pointer;margin:6px 0;font-family:'微软雅黑',sans-serif}
.btn-primary{background:#7c9ef8;color:#1e1e2e}
.btn-success{background:#a6e3a1;color:#1e1e2e}
.btn-danger{background:#f38ba8;color:#1e1e2e}
.btn-gray{background:#45475a;color:#cdd6f4}
#status{color:#a6e3a1;margin:8px 0;font-size:.9em}
#users{margin:16px 0}
.user-item{display:flex;justify-content:space-between;align-items:center;
           padding:10px 14px;background:#2a2a3e;border-radius:8px;margin:6px 0}
.user-name{font-size:1em}
.call-btn{padding:8px 18px;background:#7c9ef8;color:#1e1e2e;border:none;
          border-radius:6px;cursor:pointer;font-size:.9em}
#calling-panel{display:none;text-align:center;padding:20px;
               background:#2a2a3e;border-radius:12px;margin:16px 0}
#calling-panel h2{margin-bottom:16px;color:#7c9ef8}
audio{display:none}
</style>
</head>
<body>
<h1>📞 小K家庭电话</h1>

<div id="login">
  <input id="nameInput" placeholder="输入你的名字（如：爸爸、妈妈）" />
  <button class="btn-primary" onclick="doLogin()">进入</button>
</div>

<div id="main" style="display:none">
  <div id="status">● 连接中...</div>
  <div id="users"></div>
  <div id="calling-panel">
    <h2 id="calling-title">呼叫中...</h2>
    <button class="btn-danger" id="hangup-btn" onclick="hangup()">挂断</button>
    <button class="btn-success" id="answer-btn" style="display:none" onclick="answer()">接听</button>
  </div>
</div>

<audio id="remoteAudio" autoplay></audio>
<audio id="ringtone" loop>
  <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAA..." type="audio/wav">
</audio>

<script>
let ws, pc, localStream, myName, peerName;
const WS_PORT = """ + str(WS_PORT) + """;

function doLogin() {
  myName = document.getElementById('nameInput').value.trim();
  if (!myName) return alert('请输入名字');
  document.getElementById('login').style.display = 'none';
  document.getElementById('main').style.display = 'block';
  connect();
}

function connect() {
  const host = location.hostname;
  ws = new WebSocket(`ws://${host}:${WS_PORT}`);
  ws.onopen = () => {
    ws.send(JSON.stringify({type:'register', name:myName}));
    document.getElementById('status').textContent = '● 在线：' + myName;
  };
  ws.onmessage = async e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'online') renderUsers(msg.users);
    else if (msg.type === 'incoming') await onIncoming(msg.from);
    else if (msg.type === 'answered') await onAnswered(msg.from);
    else if (msg.type === 'rejected') onRejected(msg.from);
    else if (msg.type === 'hangup') onHangup();
    else if (msg.type === 'offer') await onOffer(msg);
    else if (msg.type === 'answer_sdp') await onAnswerSdp(msg);
    else if (msg.type === 'ice') await onIce(msg);
    else if (msg.type === 'error') alert(msg.msg);
  };
  ws.onclose = () => {
    document.getElementById('status').textContent = '● 已断开，3秒后重连...';
    setTimeout(connect, 3000);
  };
}

function renderUsers(users) {
  const div = document.getElementById('users');
  div.innerHTML = '<div style="color:#6c7086;font-size:.85em;margin-bottom:8px">在线成员</div>';
  users.filter(u => u !== myName).forEach(u => {
    div.innerHTML += `<div class="user-item">
      <span class="user-name">👤 ${u}</span>
      <button class="call-btn" onclick="callUser('${u}')">📞 拨打</button>
    </div>`;
  });
  if (users.filter(u=>u!==myName).length === 0)
    div.innerHTML += '<div style="color:#6c7086;text-align:center;padding:20px">暂无其他在线成员</div>';
}

async function callUser(target) {
  peerName = target;
  ws.send(JSON.stringify({type:'call', to:target}));
  showCalling(`正在呼叫 ${target}...`, false);
  await startPeerConnection(true);
}

async function onIncoming(from) {
  peerName = from;
  showCalling(`📞 ${from} 来电`, true);
}

async function onAnswered(from) {
  // 对方接听，发送offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  ws.send(JSON.stringify({type:'offer', to:peerName, sdp:offer.sdp}));
}

async function onOffer(msg) {
  if (!pc) await startPeerConnection(false);
  await pc.setRemoteDescription({type:'offer', sdp:msg.sdp});
  const ans = await pc.createAnswer();
  await pc.setLocalDescription(ans);
  ws.send(JSON.stringify({type:'answer_sdp', to:msg.from, sdp:ans.sdp}));
}

async function onAnswerSdp(msg) {
  await pc.setRemoteDescription({type:'answer', sdp:msg.sdp});
}

async function onIce(msg) {
  if (pc && msg.candidate)
    await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
}

function onRejected(from) {
  alert(`${from} 拒绝了通话`);
  hideCalling();
}

function onHangup() {
  alert('对方已挂断');
  cleanup();
}

async function startPeerConnection(isCaller) {
  localStream = await navigator.mediaDevices.getUserMedia({audio:true});
  pc = new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});
  localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  pc.ontrack = e => { document.getElementById('remoteAudio').srcObject = e.streams[0]; };
  pc.onicecandidate = e => {
    if (e.candidate)
      ws.send(JSON.stringify({type:'ice', to:peerName, candidate:e.candidate}));
  };
}

async function answer() {
  ws.send(JSON.stringify({type:'answer', to:peerName}));
  document.getElementById('answer-btn').style.display = 'none';
  await startPeerConnection(false);
}

function hangup() {
  ws.send(JSON.stringify({type:'hangup', to:peerName}));
  cleanup();
}

function cleanup() {
  if (pc) { pc.close(); pc = null; }
  if (localStream) { localStream.getTracks().forEach(t=>t.stop()); localStream=null; }
  document.getElementById('remoteAudio').srcObject = null;
  hideCalling();
}

function showCalling(title, showAnswer) {
  document.getElementById('calling-panel').style.display = 'block';
  document.getElementById('calling-title').textContent = title;
  document.getElementById('answer-btn').style.display = showAnswer ? 'inline-block' : 'none';
}

function hideCalling() {
  document.getElementById('calling-panel').style.display = 'none';
}
</script>
</body>
</html>"""

async def _http_handler(reader, writer):
    try:
        await reader.readline()  # 读请求行
        while True:  # 跳过headers
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
        body = _HTML.encode("utf-8")
        writer.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode()
            + body
        )
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()

# ══════════════════════════════════════════════════════
# 主程序 + GUI
# ══════════════════════════════════════════════════════
class PhoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小K家庭电话 - 服务器")
        self.geometry("480x400")
        self.configure(bg=BG)
        self._loop = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        tk.Label(self, text="📞 小K家庭电话", bg=BG, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(pady=(16,4))

        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            lan_ip = "192.168.2.11"

        info = (f"局域网地址：http://{lan_ip}:{HTTP_PORT}\n"
                f"WebSocket：ws://{lan_ip}:{WS_PORT}\n\n"
                f"家人用手机/电脑浏览器打开上面的地址即可通话\n"
                f"无需安装任何软件")
        tk.Label(self, text=info, bg=BG, fg=TEXT, font=("微软雅黑",10),
                 justify="left").pack(padx=20, pady=8)

        tk.Button(self, text="🌐 打开网页客户端", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑",10), padx=16, pady=8,
                  command=lambda: webbrowser.open(f"http://{lan_ip}:{HTTP_PORT}")
                  ).pack(pady=4)

        self.log = scrolledtext.ScrolledText(self, bg=BG2, fg=TEXT,
            font=("微软雅黑",9), height=8, state="disabled", relief="flat")
        self.log.pack(fill="both", expand=True, padx=16, pady=8)

        global _log_fn
        _log_fn = self._log

        threading.Thread(target=self._run_servers, daemon=True).start()

    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _run_servers(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start())

    async def _start(self):
        ws_server = await websockets.serve(_handle, HOST, WS_PORT)
        http_server = await asyncio.start_server(_http_handler, HOST, HTTP_PORT)
        self.after(0, lambda: self._log(f"✓ 服务已启动\n  网页：http://0.0.0.0:{HTTP_PORT}\n  信令：ws://0.0.0.0:{WS_PORT}"))
        await asyncio.gather(ws_server.wait_closed(), http_server.serve_forever())

    def _on_close(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.destroy()

if __name__ == "__main__":
    PhoneApp().mainloop()
