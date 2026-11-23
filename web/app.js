const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');
const messages = document.querySelector('#messages');
const suggestions = document.querySelector('#suggestions');
const conversation = document.querySelector('.conversation');
const isFile = location.protocol === 'file:';
let sessionId = crypto.randomUUID();
if (isFile) {
  document.querySelector('#local-note').hidden = false;
  document.querySelector('#chat-form').hidden = true;
  document.querySelector('#suggestions').hidden = true;
  document.querySelector('#mode-label').textContent = 'Abra pelo servidor';
} else {
  sessionId = sessionStorage.getItem('emporio-session') || sessionId;
  sessionStorage.setItem('emporio-session', sessionId);
  fetch('/mode').then(response => response.json()).then(data => {
    const location = {openai: 'IA hospedada', ollama: 'IA local'}[data.mode];
    document.querySelector('#mode-label').textContent = location ? `${location} · ${data.model}` : 'Modo indisponível';
  }).catch(() => {
    document.querySelector('#mode-label').textContent = 'Modo indisponível';
  });
}

function addMessage(role, text) {
  const item = document.createElement('div');
  item.className = `message ${role}`;
  if (role === 'assistant') {
    const label = document.createElement('span');
    label.className = 'speaker';
    label.textContent = 'EMPÓRIO';
    item.append(label);
  }
  const paragraph = document.createElement('p');
  paragraph.textContent = text;
  item.append(paragraph);
  messages.append(item);
  conversation.scrollTop = conversation.scrollHeight;
  return item;
}

async function send(text) {
  if (!text.trim() || sendButton.disabled) return;
  addMessage('user', text.trim());
  suggestions.hidden = true;
  input.value = '';
  sendButton.disabled = true;
  const pending = document.createElement('div');
  pending.className = 'message assistant typing';
  pending.setAttribute('aria-label', 'Assistente preparando resposta');
  pending.innerHTML = '<i></i><i></i><i></i>';
  messages.append(pending);
  conversation.scrollTop = conversation.scrollHeight;
  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sessionId, message: text.trim()})
    });
    if (!response.ok) throw new Error('O atendimento está indisponível no momento. Tente novamente em instantes.');
    const data = await response.json();
    pending.remove();
    addMessage('assistant', data.answer);
  } catch (error) {
    pending.remove();
    addMessage('assistant', error.message);
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => { event.preventDefault(); send(input.value); });
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(input.value); }
});
suggestions.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-prompt]');
  if (button) send(button.dataset.prompt);
});
