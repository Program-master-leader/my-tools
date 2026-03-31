#!/usr/bin/env python3
"""
小K家庭电话 v2
- 服务器：跑在主机上，局域网+外网均可用
- 网页客户端：浏览器打开即用（WebRTC直连，局域网无延迟）
- Windows客户端：phone_client.py，开机自启托盘常驻，来电自动弹窗

依赖：pip install websockets
"""
import asyncio, json, os, threading, webbrowser, socket
import tkinter as tk
from tkinter import scrolledtext
import websockets

HOST = "0.0.0.0"
WS_PORT  = 8765
HTTP_PORT = 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_clients: dict = {}   # name -> ws
_calls:   dict = {}   # name -> peer_name

BG="#1e1e2e"; BG2="#2a2a3e"; ACCENT="#7c9ef8"; ACCENT2="#a6e3a1"
DANGER="#f38ba8"; TEXT="#cdd6f4"

def _get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "192.168.2.11"

LAN_IP = _get_lan_ip()

# ══════════════════════════════════════════════════════
# 信令服务器
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
                await _broadcast({"type":"online","users":list(_clients.keys())})
                _log(f"📱 {name} 上线")

            elif t == "call":
                target = msg["to"]
                if target in _clients:
                    await _clients[target].send(json.dumps({"type":"incoming","from":name}))
                else:
                    await ws.send(json.dumps({"type":"error","msg":f"{target} 不在线"}))

            elif t == "answer":
                caller = msg["to"]
                if caller in _clients:
                    _calls[caller] = name; _calls[name] = caller
                    await _clients[caller].send(json.dumps({"type":"answered","from":name}))

            elif t == "reject":
                if msg["to"] in _clients:
                    await _clients[msg["to"]].send(json.dumps({"type":"rejected","from":name}))

            elif t == "hangup":
                peer = _calls.pop(name, None)
                if peer: _calls.pop(peer, None)
                if peer and peer in _clients:
                    await _clients[peer].send(json.dumps({"type":"hangup","from":name}))

            # WebRTC 信令透传
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
            await _broadcast({"type":"online","users":list(_clients.keys())})
            _log(f"📴 {name} 下线")

async def _broadcast(msg):
    if _clients:
        data = json.dumps(msg, ensure_ascii=False)
        await asyncio.gather(*[c.send(data) for c in _clients.values()],
                             return_exceptions=True)

_log_fn = print
def _log(msg): _log_fn(msg)

# ══════════════════════════════════════════════════════
# 网页客户端（修复音频：用 mdns/局域网直连 ICE）
# ══════════════════════════════════════════════════════
def _make_html():
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小K家庭电话</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#1e1e2e;color:#cdd6f4;font-family:'微软雅黑',sans-serif;
     display:flex;flex-direction:column;align-items:center;min-height:100vh;padding:20px}}
h1{{color:#7c9ef8;margin:20px 0 10px;font-size:1.4em}}
#login,#main{{width:100%;max-width:400px}}
input{{width:100%;padding:12px;background:#2a2a3e;border:1px solid #45475a;
      border-radius:8px;color:#cdd6f4;font-size:1em;margin:8px 0}}
button{{width:100%;padding:12px;border:none;border-radius:8px;font-size:1em;
       cursor:pointer;margin:6px 0;font-family:'微软雅黑',sans-serif}}
.btn-p{{background:#7c9ef8;color:#1e1e2e}}
.btn-s{{background:#a6e3a1;color:#1e1e2e}}
.btn-d{{background:#f38ba8;color:#1e1e2e}}
#status{{color:#a6e3a1;margin:8px 0;font-size:.9em;text-align:center}}
.user-item{{display:flex;justify-content:space-between;align-items:center;
           padding:10px 14px;background:#2a2a3e;border-radius:8px;margin:6px 0}}
.call-btn{{padding:8px 18px;background:#7c9ef8;color:#1e1e2e;border:none;
          border-radius:6px;cursor:pointer}}
#panel{{display:none;text-align:center;padding:20px;background:#2a2a3e;
        border-radius:12px;margin:16px 0}}
#panel h2{{margin-bottom:16px;color:#7c9ef8}}
</style>
</head>
<body>
<h1>📞 小K家庭电话</h1>
<div id="login">
  <input id="ni" placeholder="输入你的名字（爸爸/妈妈/儿子）"/>
  <button class="btn-p" onclick="login()">进入</button>
</div>
<div id="main" style="display:none">
  <div id="status">连接中...</div>
  <div id="users"></div>
  <div id="panel">
    <h2 id="pt">...</h2>
    <button class="btn-s" id="ab" style="display:none" onclick="answer()">接听</button>
    <button class="btn-d" onclick="hangup()">挂断</button>
  </div>
</div>
<audio id="ra" autoplay playsinline></audio>
<script>
const WS_PORT={WS_PORT};
let ws,pc,ls,me,peer;

function login(){{
  me=document.getElementById('ni').value.trim();
  if(!me)return alert('请输入名字');
  document.getElementById('login').style.display='none';
  document.getElementById('main').style.display='block';
  conn();
}}

function conn(){{
  ws=new WebSocket('ws://'+location.hostname+':'+WS_PORT);
  ws.onopen=()=>ws.send(JSON.stringify({{type:'register',name:me}}));
  ws.onmessage=async e=>{{
    const m=JSON.parse(e.data);
    if(m.type==='online') renderUsers(m.users);
    else if(m.type==='incoming') incoming(m.from);
    else if(m.type==='answered') await startCall(false,m.from);
    else if(m.type==='rejected') {{alert(m.from+'拒绝了');hidePanel();}}
    else if(m.type==='hangup') {{alert('对方已挂断');cleanup();}}
    else if(m.type==='offer') await onOffer(m);
    else if(m.type==='answer_sdp') await pc.setRemoteDescription({{type:'answer',sdp:m.sdp}});
    else if(m.type==='ice') pc&&m.candidate&&pc.addIceCandidate(m.candidate);
    else if(m.type==='error') alert(m.msg);
  }};
  ws.onclose=()=>{{document.getElementById('status').textContent='断开，重连中...';setTimeout(conn,3000);}};
}}

function renderUsers(users){{
  document.getElementById('status').textContent='在线：'+me;
  const d=document.getElementById('users');
  const others=users.filter(u=>u!==me);
  d.innerHTML=others.length?'':'<div style="color:#6c7086;text-align:center;padding:20px">暂无其他成员在线</div>';
  others.forEach(u=>{{
    d.innerHTML+=`<div class="user-item"><span>👤 ${{u}}</span>
    <button class="call-btn" onclick="call('${{u}}')">📞 拨打</button></div>`;
  }});
}}

async function call(target){{
  peer=target;
  ws.send(JSON.stringify({{type:'call',to:target}}));
  showPanel('正在呼叫 '+target+'...',false);
  await initPC(true);
}}

function incoming(from){{
  peer=from;
  showPanel('📞 '+from+' 来电',true);
}}

async function answer(){{
  ws.send(JSON.stringify({{type:'answer',to:peer}}));
  document.getElementById('ab').style.display='none';
  await initPC(false);
}}

async function startCall(isCaller,from){{
  // 对方接听，我是主叫，发offer
  const offer=await pc.createOffer();
  await pc.setLocalDescription(offer);
  ws.send(JSON.stringify({{type:'offer',to:peer,sdp:offer.sdp}}));
}}

async function onOffer(m){{
  if(!pc) await initPC(false);
  await pc.setRemoteDescription({{type:'offer',sdp:m.sdp}});
  const ans=await pc.createAnswer();
  await pc.setLocalDescription(ans);
  ws.send(JSON.stringify({{type:'answer_sdp',to:m.from,sdp:ans.sdp}}));
}}

async function initPC(isCaller){{
  // 局域网直连：不用STUN，直接用host候选
  ls=await navigator.mediaDevices.getUserMedia({{audio:{{echoCancellation:true,noiseSuppression:true,autoGainControl:true}}}});
  pc=new RTCPeerConnection({{iceServers:[],iceTransportPolicy:'all'}});
  ls.getTracks().forEach(t=>pc.addTrack(t,ls));
  pc.ontrack=e=>{{
    const ra=document.getElementById('ra');
    ra.srcObject=e.streams[0];
    ra.play().catch(()=>{{}});
  }};
  pc.onicecandidate=e=>{{
    if(e.candidate) ws.send(JSON.stringify({{type:'ice',to:peer,candidate:e.candidate}}));
  }};
  pc.oniceconnectionstatechange=()=>{{
    document.getElementById('status').textContent='通话状态：'+pc.iceConnectionState;
  }};
  if(isCaller){{
    // 等对方接听后再发offer（在startCall里）
  }}
}}

function hangup(){{
  ws.send(JSON.stringify({{type:'hangup',to:peer}}));
  cleanup();
}}

function cleanup(){{
  if(pc){{pc.close();pc=null;}}
  if(ls){{ls.getTracks().forEach(t=>t.stop());ls=null;}}
  document.getElementById('ra').srcObject=null;
  hidePanel();
}}

function showPanel(title,showAnswer){{
  document.getElementById('panel').style.display='block';
  document.getElementById('pt').textContent=title;
  document.getElementById('ab').style.display=showAnswer?'inline-block':'none';
}}
function hidePanel(){{document.getElementById('panel').style.display='none';}}
</script>
</body></html>"""

async def _http_handler(reader, writer):
    try:
        await reader.readline()
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""): break
        body = _make_html().encode("utf-8")
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        await writer.drain()
    except Exception: pass
    finally: writer.close()

# ══════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════
class PhoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("小K家庭电话 - 服务器")
        self.geometry("500x420"); self.configure(bg=BG)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        global _log_fn; _log_fn = self._log
        threading.Thread(target=self._run, daemon=True).start()

    def _build_ui(self):
        tk.Label(self, text="📞 小K家庭电话", bg=BG, fg=ACCENT,
                 font=("微软雅黑",14,"bold")).pack(pady=(16,4))
        url = f"http://{LAN_IP}:{HTTP_PORT}"
        info = (f"局域网地址：{url}\n"
                f"家人用手机/电脑浏览器打开上面地址即可通话\n"
                f"Windows电脑可运行 phone_client.py 实现托盘常驻")
        tk.Label(self, text=info, bg=BG, fg=TEXT, font=("微软雅黑",10),
                 justify="left").pack(padx=20, pady=8)
        tk.Button(self, text="🌐 打开网页客户端", bg=ACCENT, fg=BG,
                  relief="flat", font=("微软雅黑",10), padx=16, pady=8,
                  command=lambda: webbrowser.open(f"http://{LAN_IP}:{HTTP_PORT}")
                  ).pack(pady=4)
        self.log_box = scrolledtext.ScrolledText(self, bg=BG2, fg=TEXT,
            font=("微软雅黑",9), height=10, state="disabled", relief="flat")
        self.log_box.pack(fill="both", expand=True, padx=16, pady=8)

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg+"\n"); self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._start())

    async def _start(self):
        ws_srv  = await websockets.serve(_handle, HOST, WS_PORT)
        http_srv = await asyncio.start_server(_http_handler, HOST, HTTP_PORT)
        self.after(0, lambda: self._log(
            f"✓ 服务启动\n  网页：http://{LAN_IP}:{HTTP_PORT}\n  信令：ws://{LAN_IP}:{WS_PORT}"))
        await asyncio.gather(ws_srv.wait_closed(), http_srv.serve_forever())

    def _on_close(self): self.destroy()

if __name__ == "__main__":
    PhoneApp().mainloop()
