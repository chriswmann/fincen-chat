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

interface ResponseMeta {
  entities: {
    name: string, entity_type: string | null;
    country: string | null
  }[];
  confidence: 'high' | 'medium' | 'low';
  data_found: boolean;
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

  const submitButton = getElement<HTMLButtonElement>('button');
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

          case 'response_meta': {
            const meta: ResponseMeta = JSON.parse(sseEvent.data);

            appendMetaFooter(assistantDiv, meta.entities, meta.confidence);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            break;
          }

          case 'structured_response': {
            const resp = JSON.parse(sseEvent.data);
            assistantDiv.innerHTML = await marked.parse(resp.answer); // render the reason text
            appendMetaFooter(assistantDiv, resp.entities, resp.confidence); // add the low-confidence badge
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

function appendMetaFooter(assistantDiv: HTMLDivElement, entities: ResponseMeta['entities'], confidence: ResponseMeta['confidence']): void {
  const metaDiv = document.createElement('div');
  metaDiv.className = 'response-meta';
  const badge = document.createElement('span');
  badge.className = `confidence confidence--${confidence}`;
  badge.textContent = `${confidence}`;
  metaDiv.appendChild(badge);

  if (entities.length > 0) {
    const entitiesSpan = document.createElement('span');
    entitiesSpan.className = 'entities-label';
    entitiesSpan.textContent = `Entities: ${entities.map(e => e.name).join(', ')}`;
    metaDiv.appendChild(entitiesSpan);
  }
  assistantDiv.appendChild(metaDiv);
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

// --- Investigation mode ---
const chatTab = getElement<HTMLButtonElement>("#chat-tab");
const investigationTab = getElement<HTMLButtonElement>("#investigation-tab");
const chatPanel = getElement<HTMLDivElement>("#chat-panel");
const investigationPanel = getElement<HTMLDivElement>("#investigation-panel");

chatTab.addEventListener("click", () => {
  chatTab.classList.add("active");
  investigationTab.classList.remove("active");
  chatPanel.removeAttribute("hidden");
  investigationPanel.setAttribute("hidden", "");
});

investigationTab.addEventListener("click", () => {
  investigationTab.classList.add("active");
  chatTab.classList.remove("active");
  investigationPanel.removeAttribute("hidden");
  chatPanel.setAttribute("hidden", "");
});

// --- Investigation logic ---
const investigationSubmitButton = getElement<HTMLButtonElement>("#investigation-submit-button");
const investigationInputDiv = getElement<HTMLTextAreaElement>("#investigation-input");
const investigationStatusDiv = getElement<HTMLDivElement>("#investigation-status");
const investigationReportDiv = getElement<HTMLDivElement>("#investigation-report");

async function submitInvestigation(query: string): Promise<string | null> {
  // Disable UI during submission
  investigationInputDiv.disabled = true;
  investigationSubmitButton.disabled = true;
  investigationStatusDiv.textContent = "Starting investigation...";
  investigationStatusDiv.className = "";
  investigationReportDiv.innerHTML = "";


  try {
    const response = await fetch("/api/v1/investigations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    return data.investigation_id;
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : "Unknown Error";
    investigationStatusDiv.textContent = `Error: ${errorMessage}`;
    investigationStatusDiv.className = "investigationError";
    // Re-enable UI on failure
    investigationInputDiv.disabled = false;
    investigationSubmitButton.disabled = false;
  }
  return null;
}

async function pollStatus(investigationId: string): Promise<string> {
  const response = await fetch(`/api/v1/investigations/${investigationId}/status`);
  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }
  return response.json();
}

async function getResult(investigationId: string): Promise<string> {
  const response = await fetch(`/api/v1/investigations/${investigationId}/result`);
  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }
  return response.json();
}

let pollingInterval: number | null = null;

// Handle on the 'Investigate' button click
investigationSubmitButton.addEventListener("click", async (e: Event) => {
  e.preventDefault();
  const query = investigationInputDiv.value.trim();
  if (!query) return;

  const investigationId = await submitInvestigation(query);
  if (!investigationId) return;

  // Clear interval if one already exists
  if (pollingInterval) clearInterval(pollingInterval);

  // Start polling for status updates every two seconds
  pollingInterval = window.setInterval(async () => {
    try {
      const statusData = await pollStatus(investigationId);

      if (statusData.status === "failed") {
        investigationStatusDiv.textContent = "Investigation failed.";
        investigationStatusDiv.className = "investigationError";
        clearInterval(pollingInterval!);
        investigationInputDiv.disabled = false;
        investigationSubmitButton.disabled = false;
        return;
      }

      investigationStatusDiv.textContent = `Status: ${statusData.status} (Step ${statusData.progresss} of ${statusData.total_steps} || ` ? `})`;

      if (statusData.status === "complete") {
        clearInterval(pollingInterval!);
        investigationStatusDiv.textContent = "Investigation completed.";

        // Fetch and display the final report
        const report = await getResult(investigationId);
        renderReport(report);

        investigationInputDiv.disabled = false;
        investigationSubmitButton.disabled = false;
        investigationInputDiv.value = "";
      } catch (err) {
        clearInterval(pollingInterval!);
        const errorMessage = err instanceof Error ? err.message | "Unknown Error";
        investigationStatusDiv.textContent = `Polling Error: ${errorMessage}`;
        investigationStatusDiv.className = "investigationError";
        investigationInputDiv.disabled = false;
        investigationSubmitButton.disabled = false;
      }
    }
  }, 2000);
});

// Render the final report into the #investigation-report div
async function renderReport(report: any) {
  let markdown = `# ${report.title}\n\n`;
  markdown += `**Confidence Score:** ${report.confidence}\n\n`;

  markdown += `## Executive Summary\n${report.executive_summary}\n\n`;
  markdown += `## Detailed Findings\n${report.detailed_findings}\n\n`;

  markdown += "## Key Entitiies Involved\n";
  if (report.entities_involved && report.entities_involved.length > 0) {
    report.entities_involved.forEach((e: any) => {
      markdown += `* ${e.name} (${e.type || "Unknown"})\n`;
    });
  } else {
    markdown += " - None identified\n";
  }
  markdown += "\n";
  markdown += "## Risk Indicators\n";
  if (report.risk_indicators && report.risk_indicators.length > 0) {
    report.risk_indicators.forEach((r: string) => {
      markdown += ` - ${r}\n`;
    });
  } else {
    markdown += " - None identified\n";
  }
  markdown += "\n";

  markdown += "## Recommendations\n";
  if (report.recommendations && report.recommendations.length > 0) {
    report.recommendations.forEach((r: string) => {
      markdown += ` - ${r}\n`;
    });
  } else {
    markdown += " - None identified\n";
  }
  markdown += "\n";

  // Render the markdown to the #investigation-report div
  investigationReportDiv.innerHTML = await marked.parse(markdown);
}


function getElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`Element with selector ${selector} not found`);
  return element;
}