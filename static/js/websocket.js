const socket = io();
let currentBandId = null;

socket.on('connect', () => {
    console.log('Connected to WebSocket server');
});

socket.on('message', (data) => {
    appendMessage(data.username, data.message, data.timestamp);
});

socket.on('status', (data) => {
    appendStatusMessage(data.msg);
});

function joinBandChat(bandId, bandName) {
    if (currentBandId) {
        socket.emit('leave', { band_id: currentBandId });
    }
    
    currentBandId = bandId;
    socket.emit('join', { band_id: bandId });
    
    document.getElementById('current-band').textContent = bandName;
    document.getElementById('messages').innerHTML = '';
    document.getElementById('message-form').classList.remove('d-none');
}

function sendMessage(message) {
    if (currentBandId) {
        socket.emit('message', {
            message: message,
            band_id: currentBandId
        });
    }
}
