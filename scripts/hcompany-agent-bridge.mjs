#!/usr/bin/env node
import { HaiAgentsClient } from "hai-agents";

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);

function output(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

try {
  const input = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
  const client = new HaiAgentsClient({
    apiKey: process.env.HAI_API_KEY || process.env.HCOMPANY_API_KEY,
    baseUrl: input.baseUrl || process.env.HCOMPANY_BASE_URL || "https://agp.hcompany.ai",
  });

  if (input.operation === "start") {
    const session = await client.startSession({
      agent: input.model || "h/web-surfer-pro",
      messages: input.objective,
      maxSteps: input.maxActions,
      maxTimeS: input.timeoutSeconds,
      queue: false,
      overrides: input.startingUrl
        ? { "agent.environments[kind=web].start_url": input.startingUrl }
        : undefined,
    });
    const details = await session.get();
    output({ id: session.id, status: details.status?.status, agentViewUrl: details.agentViewUrl ?? null });
  } else if (input.operation === "status") {
    const session = client.session(input.executionId);
    const [status, details, changes] = await Promise.all([
      session.status(),
      session.get(),
      session.changes({ fromIndex: 0, includeEvents: true, waitForSeconds: 0 }),
    ]);
    output({
      id: input.executionId,
      status: status.status,
      steps: status.steps ?? 0,
      error: status.error ?? changes?.error ?? null,
      errorCode: status.errorCode ?? changes?.errorCode ?? null,
      outcome: status.outcome ?? changes?.outcome ?? null,
      answer: changes?.answer ?? details.latestAnswer ?? null,
      events: changes?.newEvents ?? [],
      agentViewUrl: details.agentViewUrl ?? null,
    });
  } else if (input.operation === "cancel") {
    await client.session(input.executionId).cancel();
    output({ id: input.executionId, status: "interrupted" });
  } else if (input.operation === "health") {
    const quota = await client.quota.getTokenQuota();
    output({ healthy: true, quota });
  } else {
    throw new Error(`Unsupported bridge operation: ${input.operation}`);
  }
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  output({ error: message, statusCode: error?.statusCode ?? null });
  process.exitCode = 1;
}
