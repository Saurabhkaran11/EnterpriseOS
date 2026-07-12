import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }), { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } }, { waitUntil() {}, passThroughOnException() {} });
}

test("server-renders the EnterpriseOS judge dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>EnterpriseOS — AI Business Operator<\/title>/i);
  assert.match(html, /Preparing EnterpriseOS/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("ships stable judge controls, modes, and architecture", async () => {
  const [dashboard, backend, env] = await Promise.all([
    readFile(new URL("../app/workflow/WorkflowDashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../backend/app.py", import.meta.url), "utf8"),
    readFile(new URL("../.env.example", import.meta.url), "utf8"),
  ]);
  for (const id of ["start-demo", "approve-workflow", "reject-workflow", "cancel-workflow", "reset-workflow", "presentation-mode", "execution-mode", "architecture-panel"]) assert.match(dashboard, new RegExp(`data-testid=\\"${id}\\"`));
  assert.match(dashboard, /7000/);
  assert.match(backend, /"LIVE", "HYBRID", "DEMO"/);
  assert.match(env, /ENTERPRISEOS_MODE=DEMO/);
  assert.match(dashboard, /H Company Computer Use/);
  assert.match(dashboard, /NVIDIA Reasoning/);
  assert.match(dashboard, /AWS S3 Artifact/);
});

test("keeps every workspace route renderable", async () => {
  for (const route of ["inbox", "crm", "tasks", "calendar", "report"]) {
    const response = await render(`/workspace/${route}`);
    assert.equal(response.status, 200, route);
  }
});
