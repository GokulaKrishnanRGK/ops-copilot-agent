import { ChatEvent } from "../types";

function parseDataBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let event = "message";
  let data = "";
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }
  if (!data) {
    return null;
  }
  return { event, data };
}

export async function streamChat(
  url: string,
  body: { message: string },
  onEvent: (event: ChatEvent) => void
): Promise<void> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`stream failed (${response.status})`);
  }
  if (!response.body) {
    throw new Error("empty stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const parsed = parseDataBlock(chunk);
      if (!parsed) {
        continue;
      }
      const payload = JSON.parse(parsed.data) as ChatEvent;
      onEvent({ ...payload, type: parsed.event || payload.type });
    }
  }
}
