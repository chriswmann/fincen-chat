import { marked } from 'marked';
import './style.css'

type Role = 'user' | 'assistant';

let conversationId: string | null = null;

const form = document.querySelector<HTMLFormElement>('#chat-form')!;
const input = document.querySelector<HTMLFormElement>('#message-input')!;
const messagesContainer = document.querySelector<HTMLFormElement>('#chat-messages')!;

// ── appendMessage ───────────────────────────────────────────────────
// Creates a new message bubble in the chat and returns the DOM element.
// We return the element so that the streaming code can keep appending
// tokens to the same bubble as they arrive.
//
// Parameters:
//   role: Role - either 'user' or 'assistant' (used as a CSS class)
//   content: string - the text to display in the bubble
//
// Return type:
//   HTMLDivElement - the new div, so we can modify it later
function appendMessage(role: Role, content: string): HTMLDivElement {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = content;
  messagesContainer.appendChild(div);

  // Auto-scroll to the bottom so the newest message is always visible
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  return div;
}

interface SSEEvent {
  event: string,
  data: string,
}

// ── parseSSEEvents ──────────────────────────────────────────────────
// Split events by new lines, return complete events and the remaining 
// text.
// 
// Parse SSE events. The events are separated by a new line (`\n\n`).
//
// Parameters:
//   raw: string — the raw SSE.
//
// Return type:
//   SSEEvent - the parsed SSE events
function parseSSEEvents(raw: string): { events: SSEEvent[]; remaining: string } {
  const events: SSEEvent[] = [];
  const parts = raw.split('\n\n');
  const remaining = parts.pop() ?? '';

  for (const part of parts) {
    if (!part.trim()) continue;

    let eventType = 'message';
    let data = '';
    for (const line of part.split('\n')) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7);
      } else if (line.startsWith('data: ')) {
        data = line.slice(6);
      }
    }
    events.push({ event: eventType, data: data });

  }
  return { events, remaining };
}

// ── sendMessage ─────────────────────────────────────────────────────
// Sends the user's message to the backend and reads the streamed
// response, updating the UI as tokens arrive.
//
// Parameters:
//   message: string - the user's message.
//
// Return type:
//   Promise<void> - 
async function sendMessage(message: string): Promise<void> {
  const assistantDiv = appendMessage('assistant', '');

  const submitButton = document.querySelector<HTMLButtonElement>('button')!;
  input.disabled = true;
  submitButton.disabled = true;
  let rawMarkdown = '';
  try {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // `stream: true` so we handle multi-byte characters that might be 
      // split across chunks.
      buffer += decoder.decode(value, { stream: true });
      const { events, remaining } = parseSSEEvents(buffer);
      buffer = remaining;

      for (const sseEvent of events) {
        switch (sseEvent.event) {
          case 'meta': {
            const meta = JSON.parse(sseEvent.data);
            conversationId = meta.conversation_id;
            break;
          }

          case 'token': {
            const token = JSON.parse(sseEvent.data);
            rawMarkdown += token.content;
            assistantDiv.innerHTML = await marked.parse(rawMarkdown);

            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            break;
          }

          case 'done': {
            break;
          }

          case 'error': {
            const error = JSON.parse(sseEvent.data);
            assistantDiv.textContent = `Error: ${error.message}`;
            assistantDiv.className = 'message error';
            break;
          }
        }
      }
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
    assistantDiv.textContent = `Error: ${errorMessage}`;
    assistantDiv.className = 'message error';
  } finally {
    input.disabled = false;
    submitButton.disabled = false;
    input.focus();
  }
}

form.addEventListener('submit', async (e: Event) => {
  // Don't reload page
  e.preventDefault();

  const message = input.value.trim();
  if (!message) return;
  appendMessage('user', message);

  input.value = '';

  await sendMessage(message);
})
