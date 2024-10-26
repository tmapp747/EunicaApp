document.addEventListener('DOMContentLoaded', () => {
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages');

    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
            messageInput.value = '';
        }
    });
});

function appendMessage(username, message, timestamp) {
    const messagesContainer = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'mb-2';
    messageDiv.innerHTML = `
        <small class="text-muted">${timestamp}</small>
        <strong>${username}:</strong> ${message}
    `;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendStatusMessage(message) {
    const messagesContainer = document.getElementById('messages');
    const statusDiv = document.createElement('div');
    statusDiv.className = 'text-center text-muted mb-2';
    statusDiv.textContent = message;
    messagesContainer.appendChild(statusDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
