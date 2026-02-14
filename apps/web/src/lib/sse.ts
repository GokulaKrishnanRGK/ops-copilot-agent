import { ChatEvent } from "../types";

const TERMINAL_EVENT_TYPES = new Set(["agent_run.completed", "agent_run.failed", "error"]);

type StreamChatOptions = {
  maxRetries?: number;
  retryDelayMs?: number;
  onRetry?: (attempt: number, error: unknown) => void;
};

type StreamChatResult = {
  terminalReceived: boolean;
  attempts: number;
};

class StreamHttpError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`stream failed (${status})`);
    this.status = status;
  }
}

class StreamAttemptError extends Error {
  readonly eventCount: number;
  readonly causeError: unknown;

  constructor(causeError: unknown, eventCount: number) {
    super(causeError instanceof Error ? causeError.message : "stream attempt failed");
    this.eventCount = eventCount;
    this.causeError = causeError;
  }
}

function parseDataBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  const data = dataLines.join("\n");
  if (!data) {
    return null;
  }
  return { event, data };
}

function isRetriableHttpStatus(status: number): boolean {
  if (status >= 500) {
    return true;
  }
  return status === 408 || status === 429;
}

function isRetriableError(error: unknown): boolean {
  if (error instanceof StreamHttpError) {
    return isRetriableHttpStatus(error.status);
  }
  return true;
}

async function delay(ms: number): Promise<void> {
  await new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function streamChatAttempt(
  url: string,
  body: { message: string },
  onEvent: (event: ChatEvent) => void
): Promise<{ terminalReceived: boolean; eventCount: number }> {
  let terminalReceived = false;
  let eventCount = 0;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new StreamHttpError(response.status);
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
        const nextEvent = { ...payload, type: parsed.event || payload.type };
        eventCount += 1;
        if (TERMINAL_EVENT_TYPES.has(nextEvent.type)) {
          terminalReceived = true;
        }
        onEvent(nextEvent);
      }
    }

    if (buffer.trim()) {
      const parsed = parseDataBlock(buffer);
      if (parsed) {
        const payload = JSON.parse(parsed.data) as ChatEvent;
        const nextEvent = { ...payload, type: parsed.event || payload.type };
        eventCount += 1;
        if (TERMINAL_EVENT_TYPES.has(nextEvent.type)) {
          terminalReceived = true;
        }
        onEvent(nextEvent);
      }
    }

    return { terminalReceived, eventCount };
  } catch (error) {
    throw new StreamAttemptError(error, eventCount);
  }
}

export async function streamChat(
  url: string,
  body: { message: string },
  onEvent: (event: ChatEvent) => void,
  options?: StreamChatOptions
): Promise<StreamChatResult> {
  const maxRetries = options?.maxRetries ?? 2;
  const retryDelayMs = options?.retryDelayMs ?? 400;

  let attempt = 0;
  while (true) {
    try {
      const result = await streamChatAttempt(url, body, onEvent);
      return {
        terminalReceived: result.terminalReceived,
        attempts: attempt + 1,
      };
    } catch (error) {
      if (!(error instanceof StreamAttemptError)) {
        throw error;
      }

      const canRetryByAttempt = attempt < maxRetries;
      const canRetryByProgress = error.eventCount === 0;
      const canRetryByError = isRetriableError(error.causeError);
      if (!(canRetryByAttempt && canRetryByProgress && canRetryByError)) {
        throw error.causeError;
      }

      attempt += 1;
      options?.onRetry?.(attempt, error.causeError);
      await delay(retryDelayMs * attempt);
    }
  }
}
