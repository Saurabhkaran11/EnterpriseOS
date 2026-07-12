"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Inbox = { id:string; sender:string; company:string; subject:string; preview:string; category:string; priority:string; received_at:string; read:boolean };
type Account = { id:string; name:string; contract_value:number; health:string; renewal_date:string; open_issues:number; owner:string };
type Task = { id:string; title:string; account:string; status:string; priority:string; assignee:string; due_date:string };
type Slot = { id:string; date:string; start_time:string; end_time:string; purpose:string; available:boolean };
type DemoState = { inbox:Inbox[]; accounts:Account[]; tasks:Task[]; calendar:Slot[] };
type ExecutiveReport = { customerAtRisk:string; contractValue:string; riskExplanation:string; relatedEngineeringIssues:string[]; recommendedActions:string[]; draftCustomerResponse:string; proposedMeetingAgenda:string[]; verificationScore:number };
type WorkspaceLink = { id:string; name:string; count:string };
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const titles:Record<string,[string,string,string]> = {
  overview:["Command center","Good morning, Alex.","Here’s what needs your attention across the business today."],
  inbox:["Communications","Inbox","Customer signals and internal updates, prioritized by business impact."],
  crm:["Revenue","Accounts","Monitor account health, renewal risk, and relationship ownership."],
  tasks:["Delivery","Task Tracker","Cross-functional work, connected to customer and revenue impact."],
  calendar:["Schedule","Calendar","Available time for the conversations that move work forward."],
  report:["Intelligence","Executive Report","A concise operating brief generated from the latest business signals."],
};
const badge = (value:string) => `badge badge-${value === "critical" || value === "at risk" || value === "blocked" ? "red" : value === "high" || value === "watch" || value === "in progress" ? "amber" : value === "healthy" || value === "done" ? "green" : "gray"}`;
const dollars = (n:number) => new Intl.NumberFormat("en-US", { style:"currency", currency:"USD", maximumFractionDigits:0 }).format(n);export function Workspace({ section }: { section:string }) {
  const [data,setData] = useState<DemoState|null>(null); const [error,setError] = useState(""); const [resetting,setResetting] = useState(false); const [query,setQuery] = useState("");
  const [report, setReport] = useState<ExecutiveReport|null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceLink[]>([]);

  const load = useCallback(async () => {
    try {
      setError("");
      const [rState, rFlow, rWorkspaces] = await Promise.all([
        fetch(`${API}/api/demo/state`).then(r => { if(!r.ok) throw new Error(); return r.json(); }),
        fetch(`${API}/api/workflows/executive-customer-review`).then(r => r.ok ? r.json() : null),
        fetch(`${API}/api/workspaces`).then(r => r.ok ? r.json() : [])
      ]);
      setData(rState);
      setWorkspaces(rWorkspaces);
      if (rFlow && rFlow.report) {
        setReport(rFlow.report);
      } else {
        setReport(null);
      }
    } catch {
      setError("EnterpriseOS could not reach the local service. Start the backend, then try again.");
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(`${API}/api/demo/state`).then(r => { if(!r.ok) throw new Error(); return r.json(); }),
      fetch(`${API}/api/workflows/executive-customer-review`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/api/workspaces`).then(r => r.ok ? r.json() : [])
    ]).then(([rState, rFlow, rWorkspaces]) => {
      if (active) {
        setData(rState);
        setWorkspaces(rWorkspaces);
        if (rFlow && rFlow.report) setReport(rFlow.report);
      }
    }).catch(() => {
      if (active) setError("EnterpriseOS could not reach the local service. Start the backend, then try again.");
    });
    return () => { active = false; };
  }, []);

  async function reset(){ setResetting(true); try { const r=await fetch(`${API}/api/demo/reset`,{method:"POST"}); if(!r.ok) throw new Error(); const s = await r.json(); setData(s); setQuery(""); setReport(null); const w = await fetch(`${API}/api/workspaces`).then(res => res.json()); setWorkspaces(w); } catch { setError("The demo could not be reset. Please try again."); } finally { setResetting(false); } }

  async function handleMutation(actionType: "book" | "toggle", id: string) {
    try {
      const path = actionType === "book" ? `/api/calendar/${id}/book` : `/api/tasks/${id}/toggle`;
      const response = await fetch(`${API}${path}`, { method: "POST" });
      if (!response.ok) throw new Error();
      const updatedState = await response.json();
      setData(updatedState);
      
      const rFlow = await fetch(`${API}/api/workflows/executive-customer-review`).then(r => r.ok ? r.json() : null);
      if (rFlow && rFlow.report) setReport(rFlow.report);
    } catch {
      setError("Failed to update status. Please try again.");
    }
  }

  const [eyebrow,title,subhead]=titles[section] || ["Custom workspace", section.replace("-", " "), "Your custom integrated tool."];
  return <div className="shell">
    <aside className="sidebar" style={{display: "flex", flexDirection: "column"}}><div className="brand"><div className="brand-mark">E</div><span>EnterpriseOS</span></div><div className="nav-label">Workspace</div><nav className="nav" aria-label="Workspace navigation" style={{flex: 1, overflowY: "auto"}}>
      {workspaces.map(x => <Link key={x.id} href={`/workspace/${x.id}`} className={section===x.id?"active":""} data-testid={`nav-${x.id}`} aria-label={`Open ${x.name}`}><span>{x.name}</span>{x.count&&<span className="count">{x.count}</span>}</Link>)}
    </nav>
    <div className="add-tool-box" style={{padding: "12px 14px", borderTop: "1px solid var(--border-color)", margin: "8px 0"}}>
      <span className="nav-label" style={{display: "block", marginBottom: 6, fontSize: "0.7rem", color: "var(--text-secondary)"}}>Add custom workspace</span>
      <form onSubmit={async (e) => {
        e.preventDefault();
        const target = e.currentTarget;
        const name = (target.elements.namedItem("toolName") as HTMLInputElement).value.trim();
        if (!name) return;
        const id = name.toLowerCase().replace(/\s+/g, "-");
        try {
          const r = await fetch(`${API}/api/workspaces?id=${encodeURIComponent(id)}&name=${encodeURIComponent(name)}`, { method: "POST" });
          if (r.ok) {
            setWorkspaces(await r.json());
            target.reset();
          }
        } catch (err) {
          console.error(err);
        }
      }} style={{display: "flex", gap: 6}}>
        <input name="toolName" placeholder="Tool name…" style={{background: "hsla(223, 47%, 20%, 0.5)", border: "1px solid var(--border-color)", color: "white", padding: "4px 8px", borderRadius: 4, fontSize: "0.8rem", flex: 1}} required />
        <button type="submit" className="btn btn-primary" style={{padding: "4px 10px", fontSize: "0.8rem"}}>+</button>
      </form>
    </div>
    <div className="agent-card" style={{marginTop: "auto"}}><div className="agent-status"><span className="pulse"/> AI operator online</div><p>Monitoring 19 signals across your business. Last sync just now.</p></div></aside>
    <main className="main"><header className="topbar"><div className="crumb">EnterpriseOS&nbsp; / &nbsp;<strong>{section === "overview" ? "Overview" : title}</strong></div><div className="top-actions"><button className="btn" onClick={reset} disabled={resetting} data-testid="reset-demo" aria-label="Reset all demo data">{resetting?"Resetting…":"Reset demo"}</button><div className="avatar" aria-label="Alex Morgan profile">AM</div></div></header>
    <div className="content"><div className="section-toolbar"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="subhead">{subhead}</p></div>{["inbox","crm","tasks"].includes(section)&&<input className="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder={`Search ${section}…`} aria-label={`Search ${section}`} data-testid={`search-${section}`}/>}</div>
      {error?<div className="card error" role="alert">{error}<br/><button className="btn" onClick={load} data-testid="retry-load">Try again</button></div>:!data?<div className="card loading" role="status">Loading business data…</div>:render(section,data,query,report,handleMutation)}
    </div></main>
  </div>;
}

function render(section:string,d:DemoState,q:string,report:ExecutiveReport|null,onMutation:(action:"book"|"toggle",id:string)=>void){
  if(section==="overview") return <><div className="metrics"><Metric label="Revenue monitored" value="$1.82M" foot="4 active accounts"/><Metric label="Renewal at risk" value="$640K" foot="Acme Health · 42 days" danger/><Metric label="Open priorities" value="6" foot="2 customer-blocking"/><Metric label="AI actions today" value="12" foot="↑ 18% this week"/></div><div className="grid-main"><div className="card"><div className="card-head"><div><div className="card-title">Priority inbox</div><div className="card-kicker">Ranked by customer and revenue impact</div></div><Link className="link" href="/workspace/inbox">View all →</Link></div><InboxRows rows={d.inbox.slice(0,4)}/></div><div className="card risk-card" data-testid="risk-brief-acme-health"><div className="card-head"><div><div className="card-title">Account risk brief</div><div className="card-kicker">AI-generated · just now</div></div><span className="badge badge-red">Critical</span></div><div className="risk-body"><div className="risk-account">ACME HEALTH</div><div className="risk-value">$640,000 renewal</div><p>Executive attention recommended. Payment timeouts and reporting defects are now affecting renewal confidence.</p><ul className="risk-list"><li>3 unresolved product issues</li><li>Champion sentiment declining</li><li>Renewal decision in 42 days</li></ul><Link href="/workspace/crm" className="btn" style={{display:"block",textAlign:"center",textDecoration:"none",marginTop:18}}>Open account</Link></div></div></div></>;
  if(section==="inbox"){ const rows=d.inbox.filter(x=>(x.subject+x.company+x.sender).toLowerCase().includes(q.toLowerCase())); return <div className="card"><div className="card-head"><div><div className="card-title">All messages</div><div className="card-kicker">{rows.length} conversations</div></div></div>{rows.length?<InboxRows rows={rows}/>:<Empty/>}</div> }
  if(section==="crm"){ const rows=d.accounts.filter(x=>(x.name+x.owner).toLowerCase().includes(q.toLowerCase())); return <div className="card table-card"><div className="card-head"><div><div className="card-title">Account portfolio</div><div className="card-kicker">{dollars(rows.reduce((a,x)=>a+x.contract_value,0))} total contract value</div></div></div>{rows.length?<div className="table-scroll"><table><thead><tr><th>Account</th><th>Value</th><th>Health</th><th>Renewal</th><th>Issues</th><th>Owner</th></tr></thead><tbody>{rows.map(x=><tr key={x.id} data-testid={`crm-account-${x.id}`}><td><b>{x.name}</b></td><td className="money">{dollars(x.contract_value)}</td><td><span className={badge(x.health)}>{x.health}</span></td><td>{x.renewal_date}</td><td>{x.open_issues}</td><td><div className="person"><span className="mini-avatar">{x.owner.split(" ").map(n=>n[0]).join("")}</span>{x.owner}</div></td></tr>)}</tbody></table></div>:<Empty/>}</div> }
  if(section==="tasks"){ const rows=d.tasks.filter(x=>(x.title+x.account+x.assignee).toLowerCase().includes(q.toLowerCase())); return <div className="card table-card"><div className="card-head"><div><div className="card-title">Active work</div><div className="card-kicker">Sorted by customer impact</div></div></div>{rows.length?<div className="table-scroll"><table><thead><tr><th>Task</th><th>Account</th><th>Status</th><th>Priority</th><th>Assignee</th><th>Due</th></tr></thead><tbody>{rows.map(x=><tr key={x.id} data-testid={`task-${x.id}`}><td><b>{x.title}</b></td><td>{x.account}</td><td><span className={badge(x.status)} style={{cursor:"pointer"}} onClick={()=>onMutation("toggle", x.id)} title="Click to toggle status">{x.status}</span></td><td><span className={badge(x.priority)}>{x.priority}</span></td><td>{x.assignee}</td><td>{x.due_date}</td></tr>)}</tbody></table></div>:<Empty/>}</div> }
  if(section==="calendar") return <div className="calendar">{d.calendar.filter(x=>x.available).map(x=><button key={x.id} className="slot" data-testid={`calendar-slot-${x.id}`} onClick={()=>onMutation("book", x.id)} aria-label={`Book ${x.purpose} on ${x.date} at ${x.start_time}`}><div className="slot-date">{x.date}</div><div className="slot-time">{x.start_time}–{x.end_time}</div><div className="slot-purpose">{x.purpose}</div></button>)}</div>;
  
  if(section==="report") {
    if(report) {
      return <article className="card report" data-testid="executive-report">
        <div className="eyebrow">Dynamically Generated operating brief</div>
        <h2>Operating brief</h2>
        <p>{report.riskExplanation}</p>
        <div className="report-block">
          <h3>What changed</h3>
          <ul>
            <li>{report.customerAtRisk} is currently at high renewal risk ({report.contractValue} contract value).</li>
            <li>{report.relatedEngineeringIssues.length} engineering issues are linked to this account:</li>
            {report.relatedEngineeringIssues.map((issue: string) => <li key={issue} style={{marginLeft: 20, listStyleType: "circle"}}>{issue}</li>)}
          </ul>
        </div>
        <div className="report-block">
          <h3>Recommended decisions</h3>
          <ol>
            {report.recommendedActions.map((action: string, i: number) => (
              <li key={i}>{action}</li>
            ))}
          </ol>
        </div>
        <div className="report-block">
          <h3>Proposed review agenda</h3>
          <ul>
            {report.proposedMeetingAgenda.map((item: string) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="report-block">
          <h3>Business outlook</h3>
          <p><b>$1.82M</b> in monitored contract value · <b>{report.contractValue}</b> at immediate risk · Verification score: <b>{report.verificationScore}/100</b></p>
        </div>
      </article>;
    }
    return <article className="card report" data-testid="executive-report"><div className="eyebrow">Sunday, July 12 · Generated at 8:32 AM</div><h2>Operating brief</h2><p>Revenue remains stable, but the Acme Health renewal requires coordinated executive action this week. EnterpriseOS has connected the escalation, product defects, and account sentiment into one priority response.</p><div className="report-block"><h3>What changed</h3><ul><li>Acme Health escalated recurring payment timeouts after three affected billing runs.</li><li>Two engineering tasks are active; the timeout fix is currently blocked in QA.</li><li>Northstar Retail moved from watch to healthy following a successful adoption review.</li></ul></div><div className="report-block"><h3>Recommended decisions</h3><ol><li>Book the executive review slot with Acme Health for Monday morning.</li><li>Assign a QA owner to unblock the payment timeout hotfix today.</li><li>Prepare renewal protection terms before the customer conversation.</li></ol></div><div className="report-block"><h3>Business outlook</h3><p><b>$1.82M</b> in monitored contract value · <b>$640K</b> at immediate risk · <b>3</b> accounts healthy or improving.</p></div></article>;
  }

  return <div className="card" style={{padding: 24}}>
    <h2>{section.replace("-", " ").toUpperCase()} Workspace</h2>
    <p style={{color: "var(--text-secondary)", marginTop: 8}}>This is a custom tool workspace integrated into EnterpriseOS. The agent can monitor and read tables populated here.</p>
    <div className="empty" style={{marginTop: 24}}>No database records loaded for this tool yet.</div>
  </div>;
}
function Metric({label,value,foot,danger}:{label:string,value:string,foot:string,danger?:boolean}){ return <div className="metric"><div className="metric-label">{label}<span>↗</span></div><div className={`metric-value ${danger?"danger":""}`}>{value}</div><div className="metric-foot">{foot}</div></div> }
function InboxRows({rows}:{rows:Inbox[]}){ return <div className="rows">{rows.map(x=><div className="row" key={x.id} data-testid={`inbox-row-${x.id}`}><div><div className="row-title">{x.sender} <span className="muted">· {x.company}</span></div><div className="row-sub"><b>{x.subject}</b> — {x.preview}</div></div><div style={{textAlign:"right"}}><span className={badge(x.priority)}>{x.priority}</span><div className="row-sub">{x.received_at}</div></div></div>)}</div> }
function Empty(){ return <div className="empty">No matching records. Try a different search.</div> }
