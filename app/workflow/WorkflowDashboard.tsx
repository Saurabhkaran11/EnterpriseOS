"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ID = "executive-customer-review";
type Step = { id:string; title:string; description:string; status:string; application:string; riskLevel:string; requiresApproval:boolean; startedAt:string|null; completedAt:string|null; output:string|null; error:string|null };
type Report = { customerAtRisk:string; contractValue:string; riskExplanation:string; relatedEngineeringIssues:string[]; recommendedActions:string[]; draftCustomerResponse:string; proposedMeetingAgenda:string[]; verificationScore:number };
type ComputerUse = { currentGoal:string; currentPage:string; latestAction:string; extractedResult:string|null; confidence:number|null; providerMode:string; actionsTaken:number; screenshotReference:string|null; fallbackReason:string|null };
type ReasoningState = { status:string; model:string; riskScore:number|null; verification:{verified:boolean;confidence:number;explanation:string;missingEvidence:string[]}|null; fallbackReason:string|null };
type StorageState = { status:string; mode:string; locations:{json:string;markdown:string}|null; fallbackReason:string|null };
type Workflow = { id:string; name:string; goal:string; status:string; currentStepId:string|null; steps:Step[]; report:Report|null; integrations:{name:string;capability:string;status:string}[]; computerUse:ComputerUse; reasoning:ReasoningState; artifactStorage:StorageState; executionMode:{requested:string;resolved:string;fallbackReasons:string[]}; estimatedDurationSeconds:number };

export function WorkflowDashboard(){
  const [flow,setFlow]=useState<Workflow|null>(null); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  const [customGoal, setCustomGoal] = useState("");
  const [customProblem, setCustomProblem] = useState("");
  const request=useCallback(async(path:string,method="GET")=>{ const r=await fetch(`${API}${path}`,{method}); if(!r.ok) throw new Error((await r.json()).detail||"Request failed"); return r.json(); },[]);
  const load=useCallback(async()=>{try{setError("");setFlow(await request(`/api/workflows/${ID}`));}catch{try{setFlow(await request("/api/workflows/demo","POST"));}catch{setError("The workflow service is unavailable. Start the backend and try again.");}}},[request]);
  useEffect(()=>{let active=true;request(`/api/workflows/${ID}`).then(value=>{if(active)setFlow(value)}).catch(()=>request("/api/workflows/demo","POST").then(value=>{if(active)setFlow(value)}).catch(()=>{if(active)setError("The workflow service is unavailable. Start the backend and try again.")}));return()=>{active=false}},[request]);
  useEffect(()=>{if(!flow||!["PLANNING","RUNNING"].includes(flow.status))return; const timer=setTimeout(async()=>{try{const data=await request(`/api/workflows/${ID}/events`);setFlow(data.workflow)}catch{setError("Execution update failed. Your progress is safely stored; retry to continue.")}},7000);return()=>clearTimeout(timer)},[flow,request]);
  async function act(action:"start"|"approve"|"reject"|"cancel"|"reset"){setBusy(true);setError("");try{const path=action==="reset"?"/api/workflows/demo":`/api/workflows/${ID}/${action}`;setFlow(await request(path,"POST"))}catch(e){setError(e instanceof Error?e.message:"Action failed") }finally{setBusy(false)}}
  
  async function handleStart() {
    setBusy(true);
    setError("");
    try {
      if (customGoal.trim() || customProblem.trim()) {
        const initRes = await fetch(`${API}/api/workflows/${ID}/initialize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ goal: customGoal, name: customProblem })
        });
        if (!initRes.ok) throw new Error("Goal planning failed. Try a simpler prompt.");
        const initWorkflow = await initRes.json();
        setFlow(initWorkflow);
      }
      const startRes = await fetch(`${API}/api/workflows/${ID}/start`, { method: "POST" });
      if (!startRes.ok) throw new Error("Start execution failed");
      setFlow(await startRes.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start workflow");
    } finally {
      setBusy(false);
    }
  }

  const current=useMemo(()=>flow?.steps.find(s=>s.id===flow.currentStepId)||null,[flow]);
  if(!flow)return <main className="workflow-loading"><div className="brand-mark">E</div><p>{error||"Preparing EnterpriseOS…"}</p>{error&&<button className="btn" onClick={load}>Try again</button>}</main>;
  return <main className="judge-shell">
    <header className="judge-header"><div className="judge-brand"><div className="brand-mark">E</div><div><b>EnterpriseOS</b><span>Judge Demo Mode</span></div></div><div className="integration-row" aria-label="Integration status" style={{display: "flex", alignItems: "center", gap: "10px"}}>{flow.integrations.map(x=><div className="integration" key={x.name} data-testid={`integration-${x.name.toLowerCase().replace(" ","-")}`}><span className="integration-dot"/><b>{x.name}</b><span>{x.capability}</span><em>{x.status}</em></div>)}<form onSubmit={async (e) => {
          e.preventDefault();
          const target = e.currentTarget;
          const name = (target.elements.namedItem("intName") as HTMLInputElement).value.trim();
          const cap = (target.elements.namedItem("intCap") as HTMLInputElement).value.trim();
          if(!name || !cap) return;
          try {
            const r = await fetch(`${API}/api/integrations?name=${encodeURIComponent(name)}&capability=${encodeURIComponent(cap)}`, { method: "POST" });
            if (r.ok) {
              const updatedInts = await r.json();
              setFlow(prev => prev ? { ...prev, integrations: updatedInts } : null);
              target.reset();
            }
          } catch(err) {
            console.error(err);
          }
        }} style={{display: "flex", gap: 4, alignItems: "center", background: "hsla(223, 47%, 20%, 0.4)", padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border-color)"}}><input name="intName" placeholder="Name…" style={{background: "transparent", border: "none", color: "white", width: 60, fontSize: "0.75rem"}} required/><input name="intCap" placeholder="Role…" style={{background: "transparent", border: "none", color: "white", width: 60, fontSize: "0.75rem"}} required/><button type="submit" className="btn btn-primary" style={{padding: "2px 6px", fontSize: "0.75rem"}}>+</button></form></div><div className="header-statuses"><div className={`mode-indicator mode-${flow.executionMode.resolved.toLowerCase()}`} data-testid="execution-mode">{flow.executionMode.resolved}</div><div className={`flow-status status-${flow.status.toLowerCase()}`} data-testid="workflow-status"><i/>{flow.status.replace("_"," ")}</div></div></header>
    <section className="goal-panel" data-testid="workflow-goal"><div><div className="eyebrow">The problem</div>{flow.status === "IDLE" ? <input className="problem-input" defaultValue={flow.name} onChange={e=>setCustomProblem(e.target.value)} style={{background:"transparent",border:"none",borderBottom:"1px dashed var(--line)",color:"var(--ink)",fontSize:"28px",fontWeight:700,width:"100%",padding:"4px 0",outline:"none",letterSpacing:"-1.1px"}} placeholder="Enter the problem statement..."/> : <h1>{flow.name}</h1>}<div className="objective-box" data-testid="business-objective"><span>Business objective</span>{flow.status === "IDLE" ? <textarea className="goal-input" defaultValue={flow.goal} onChange={e=>setCustomGoal(e.target.value)} style={{width:"100%",background:"hsla(223, 47%, 20%, 0.3)",border:"1px solid var(--border-color)",color:"white",padding:"8px 12px",borderRadius:6,fontSize:"0.9rem",marginTop:6,resize:"vertical",minHeight:60}} placeholder="Enter custom business objective..."/> : <p>{flow.goal}</p>}</div></div><div className="judge-actions">
      {flow.status==="IDLE"&&<button className="btn btn-primary" onClick={handleStart} disabled={busy} data-testid="start-demo" aria-label="Start Executive Customer Review demo">Start Demo <span>→</span></button>}
      {flow.status==="AWAITING_APPROVAL"&&<><button className="btn btn-primary" onClick={()=>act("approve")} disabled={busy} data-testid="approve-workflow">Approve</button><button className="btn" onClick={()=>act("reject")} disabled={busy} data-testid="reject-workflow">Reject</button></>}
      {!["IDLE","COMPLETED","FAILED","CANCELLED"].includes(flow.status)&&<button className="btn" onClick={()=>act("cancel")} disabled={busy} data-testid="cancel-workflow">Cancel</button>}
      <button className="btn btn-quiet" onClick={()=>act("reset")} disabled={busy} data-testid="reset-workflow">Reset Demo</button>
      <button className="btn btn-quiet" onClick={()=>document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()} data-testid="presentation-mode" aria-label="Toggle fullscreen presentation mode">Present ⛶</button>
    </div></section>
    <section className="architecture-panel" aria-label="EnterpriseOS architecture" data-testid="architecture-panel"><span>User Goal</span><i>→</i><span>Workflow Engine</span><i>→</i><span>H Company Computer Use</span><i>→</i><span>NVIDIA Reasoning</span><i>→</i><span>Human Approval</span><i>→</i><span>AWS S3 Artifact</span></section>
    {error&&<div className="workflow-error" role="alert">{error}</div>}
    <div className="judge-grid">
      <section className="timeline-panel" aria-labelledby="timeline-title"><div className="panel-label"><span id="timeline-title">Execution plan</span><b>{flow.steps.filter(s=>s.status==="COMPLETED").length}/{flow.steps.length}</b></div><div className="timeline" data-testid="workflow-timeline">{flow.steps.map((s,i)=><div className={`timeline-step step-${s.status.toLowerCase()}`} key={s.id} data-testid={`workflow-step-${s.id}`}><div className="step-node">{s.status==="COMPLETED"?"✓":i+1}</div><div className="step-copy"><div><b>{s.title}</b>{s.requiresApproval&&<span className="approval-tag">Approval</span>}</div><span>{s.application} · {s.riskLevel} risk</span>{s.output&&<p>{s.output}</p>}{s.error&&<p className="step-error">{s.error}</p>}</div></div>)}</div></section>
      <div className="execution-stack">
        <section className="current-panel" data-testid="current-action"><div className="panel-label"><span>Current action</span><b>Live</b></div>{current?<><div className="current-app">{current.application}</div><h2>{current.title}</h2><p>{current.description}</p>{flow.status==="AWAITING_APPROVAL"&&<div className="approval-callout"><b>Human decision required</b><span>Approve to schedule the internal review, or reject to stop before any calendar action.</span></div>}</>:<div className="no-action"><span>◎</span><b>{flow.status==="COMPLETED"?"Workflow complete":flow.status==="IDLE"?"Ready to begin":"Execution stopped"}</b><p>{flow.status==="IDLE"?"Start the deterministic demonstration when the judges are ready.":"No action is currently running."}</p></div>}</section>
        <section className="preview-panel" data-testid="application-preview"><div className="preview-chrome"><div><i/><i/><i/></div><span>{current?.application||"EnterpriseOS"} Preview</span><em>Controlled app</em></div><ApplicationPreview step={current}/><ActivityFeed activity={flow.computerUse}/></section>
      </div>
      <section className={`final-panel ${flow.report?"report-ready":""}`} data-testid="final-report-panel"><div className="panel-label"><span>Final report</span>{flow.report&&<b>Verified</b>}</div><IntegrationOutcomes reasoning={flow.reasoning} storage={flow.artifactStorage}/>{flow.report?<ReportView report={flow.report}/>:<div className="report-placeholder"><div className="report-glyph">E</div><b>Report pending</b><p>The verified executive brief will appear here after the workflow completes.</p></div>}</section>
    </div>
  </main>
}

function ApplicationPreview({step}:{step:Step|null}){const app=step?.application||"";if(app==="Inbox")return <div className="mock-app"><div className="mock-toolbar">Inbox <span>5 messages</span></div><MockRow hot title="Dr. Maya Patel · Acme Health" sub="Urgent: payment failures affecting patients"/><MockRow hot={step?.id==="identify-customer"} title="Priya Raman · Sales" sub="Acme renewal confidence has dropped"/><MockRow title="Marcus Chen · Sales" sub="Northstar expansion moved to legal"/></div>;if(app==="CRM")return <div className="mock-app"><div className="mock-toolbar">Account portfolio <span>$1.82M monitored</span></div><MockRow hot title="Acme Health · $640,000" sub="At risk · Renewal Aug 23 · 3 open issues"/><MockRow title="Northstar Retail · $480,000" sub="Healthy · Renewal Nov 14"/><MockRow title="BluePeak Logistics · $390,000" sub="Watch · Renewal Sep 30"/></div>;if(app==="Task Tracker")return <div className="mock-app"><div className="mock-toolbar">Engineering issues <span>Acme Health</span></div><MockRow hot title="Resolve payment processing timeout" sub="Blocked · Critical · Nina Shah"/><MockRow hot title="Correct claims export rounding" sub="In progress · High · Leo Wong"/><MockRow title="Prepare incident RCA" sub="In progress · High"/></div>;if(app==="Calendar")return <div className="mock-app"><div className="mock-toolbar">Monday, July 13 <span>3 slots</span></div><div className="mock-slot hot"><b>9:00 AM</b><span>Acme Health executive review · 45m</span></div><div className="mock-slot"><b>11:30 AM</b><span>Engineering escalation triage · 30m</span></div></div>;if(["Reasoning","Composer","Approval","Executive Report"].includes(app))return <div className="mock-thinking"><div className="reason-mark">{app==="Approval"?"!":"✦"}</div><b>{app}</b><p>{step?.output||step?.description}</p><div className="reason-lines"><i/><i/><i/></div></div>;return <div className="mock-thinking"><div className="reason-mark">E</div><b>Business applications ready</b><p>Records will be highlighted as the workflow moves between tools.</p></div>}
function MockRow({hot,title,sub}:{hot?:boolean,title:string,sub:string}){return <div className={`mock-row ${hot?"hot":""}`}><span className="mock-avatar">{title[0]}</span><div><b>{title}</b><p>{sub}</p></div>{hot&&<em>Matched</em>}</div>}
function ActivityFeed({activity:a}:{activity:ComputerUse}){return <div className="activity-feed" data-testid="computer-use-activity"><div className="activity-heading"><div><span className="activity-pulse"/> Computer-use activity</div><b>{a.providerMode}</b></div><dl><div><dt>Current goal</dt><dd>{a.currentGoal}</dd></div><div><dt>Current page</dt><dd>{a.currentPage.replace("http://localhost:3000","")||"/"}</dd></div><div><dt>Latest action</dt><dd>{a.latestAction}</dd></div><div><dt>Extracted result</dt><dd>{a.extractedResult||"Waiting for source data…"}</dd></div><div><dt>Confidence</dt><dd>{a.confidence?`${Math.round(a.confidence*100)}%`:"—"}</dd></div></dl>{a.fallbackReason&&<p className="fallback-note">Real provider unavailable · continued safely in Mock mode</p>}</div>}
function IntegrationOutcomes({reasoning:r,storage:s}:{reasoning:ReasoningState;storage:StorageState}){const location=s.locations?.markdown||null;return <div className="integration-outcomes" data-testid="integration-outcomes"><div><span>NVIDIA reasoning</span><b>{r.status}</b></div><div><span>Risk score</span><b>{r.riskScore??"—"}{r.riskScore!==null&&"/100"}</b></div><div><span>Verification</span><b>{r.verification?`${Math.round(r.verification.confidence*100)}%`:"—"}</b></div><div><span>Artifact storage</span><b>{s.mode} · {s.status}</b></div>{location&&<div className="artifact-location"><span>Final report location</span><code title={location}>{location}</code></div>}</div>}
function ReportView({report:r}:{report:Report}){return <div className="report-view"><div className="report-score"><div><span>Verification score</span><b>{r.verificationScore}</b><em>/100</em></div><p>All findings cross-checked against source records.</p></div><ReportBlock label="Customer at risk"><h2>{r.customerAtRisk}</h2><strong>{r.contractValue}</strong><p>{r.riskExplanation}</p></ReportBlock><ReportBlock label="Engineering issues"><ul>{r.relatedEngineeringIssues.map(x=><li key={x}>{x}</li>)}</ul></ReportBlock><ReportBlock label="Recommended actions"><ol>{r.recommendedActions.map(x=><li key={x}>{x}</li>)}</ol></ReportBlock><ReportBlock label="Draft customer response"><blockquote>“{r.draftCustomerResponse}”</blockquote></ReportBlock><ReportBlock label="Proposed agenda"><ul>{r.proposedMeetingAgenda.map(x=><li key={x}>{x}</li>)}</ul></ReportBlock></div>}
function ReportBlock({label,children}:{label:string,children:React.ReactNode}){return <div className="final-block"><div className="eyebrow">{label}</div>{children}</div>}
