import { useEffect, useMemo, useState, type ReactNode } from "react";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

type Agent = { id: number; code: string; name: string; department: string; description: string };
type Goal = { id: number; title: string; description?: string };
type Project = { id: number; name: string; description?: string; status: string };
type Task = { id: number; title: string; description?: string; status: string; assigned_agent?: string; project_id?: number; project_name?: string };
type Vendor = { id: number; name: string; category?: string; contact?: string; status: string; notes?: string };
type Metric = { id: number; metric_name: string; value: number; unit?: string; period?: string; notes?: string };
type Transaction = { id: number; type: "INCOME" | "EXPENSE"; category: string; amount: number; description?: string; transaction_date: string };
type Document = { id: number; title: string; content: string; created_at?: string };
type Dashboard = { agents:number; goals:number; projects:number; tasks:number; openTasks:number; vendors:number; knowledge:number; income:number; expense:number; balance:number };
type ActionProposal = { id:string; tool:string; description:string; arguments:Record<string, unknown>; requires_approval?:boolean; status?:"pending"|"approved"|"rejected"|"failed" };

const navigation = ["Dashboard", "AI Command Center", "Goals", "Projects", "Tasks", "Business", "Vendors", "Finance", "Knowledge"];

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) {
    const message = typeof data === "object" && data && "message" in data ? String((data as {message:string}).message) : String(data || `Request failed (${response.status})`);
    throw new Error(message);
  }
  return data as T;
}

function Field({ label, children }: { label:string; children:ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function Empty({ text }: { text:string }) {
  return <div className="empty"><strong>Nothing here yet</strong><span>{text}</span></div>;
}

function PageHeader({ title, description, action }: { title:string; description:string; action?:ReactNode }) {
  return <div className="page-head"><div><h2>{title}</h2><p>{description}</p></div>{action}</div>;
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [page, setPage] = useState("Dashboard");
  const [agent, setAgent] = useState("CEO");
  const [objective, setObjective] = useState("Increase monthly revenue by 20%");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [aiMode, setAiMode] = useState("MOCK");
  const [messagesByAgent, setMessagesByAgent] = useState<Record<string, {role:"user"|"assistant";content:string}[]>>({});
  const [actionsByAgent, setActionsByAgent] = useState<Record<string, ActionProposal[]>>({});

  async function loadCore() {
    try {
      const [a, g, d, s] = await Promise.all([
        api<Agent[]>("/api/agents"),
        api<Goal[]>("/api/goals"),
        api<Dashboard>("/api/dashboard"),
        api<{mode?:string}>("/api/ai/status").catch(() => ({mode:"unknown"})),
      ]);
      setAgents(a); setGoals(g); setDashboard(d); setAiMode(String(s.mode || "unknown").toUpperCase());
    } catch (e) { setToast(e instanceof Error ? e.message : "Unable to load system data"); }
  }

  useEffect(() => { loadCore(); }, []);
  useEffect(() => { if (!toast) return; const t=setTimeout(()=>setToast(""),3500); return ()=>clearTimeout(t); }, [toast]);

  async function run(message?: string) {
    const prompt = (message ?? objective).trim();
    if (!prompt) {
      setToast("Enter an objective or message first");
      return;
    }

    const history = messagesByAgent[agent] || [];
    const nextHistory = [...history, { role: "user" as const, content: prompt }];
    setMessagesByAgent(prev => ({ ...prev, [agent]: nextHistory }));
    setObjective("");
    setLoading(true);

    try {
      const data = await api<Record<string, unknown>>("/api/ai/run", {
        method:"POST",
        body:JSON.stringify({
          agent,
          objective: prompt,
          context: {},
          conversation: history,
        })
      });

      const responseText = typeof data.response === "string"
        ? data.response
        : typeof data.summary === "string"
          ? data.summary
          : JSON.stringify(data, null, 2);

      setMessagesByAgent(prev => ({
        ...prev,
        [agent]: [...(prev[agent] || []), { role: "assistant", content: responseText }]
      }));
      const proposed = Array.isArray(data.actions) ? data.actions as ActionProposal[] : [];
      if (proposed.length) setActionsByAgent(prev => ({ ...prev, [agent]: [...(prev[agent] || []), ...proposed.map(a => ({...a, status:"pending" as const}))] }));
      await loadCore();
    } catch(e) {
      const messageText = e instanceof Error ? e.message : "AI request failed";
      setMessagesByAgent(prev => ({
        ...prev,
        [agent]: [...(prev[agent] || []), { role: "assistant", content: `## AI request failed\n\n${messageText}` }]
      }));
    } finally {
      setLoading(false);
    }
  }

  function clearConversation() {
    setMessagesByAgent(prev => ({ ...prev, [agent]: [] }));
    setActionsByAgent(prev => ({ ...prev, [agent]: [] }));
    setObjective("");
  }

  async function approveAction(action: ActionProposal) {
    try {
      const data = await api<{status:string;result?:unknown;error?:string}>("/api/ai/actions/execute", { method:"POST", body:JSON.stringify({tool:action.tool, arguments:action.arguments}) });
      setActionsByAgent(prev => ({ ...prev, [agent]: (prev[agent] || []).map(a => a.id===action.id ? {...a, status:data.status==="completed"?"approved":"failed"} : a) }));
      setToast(data.status === "completed" ? `${action.tool.replaceAll("_"," ")} completed` : (data.error || "Action failed"));
      await loadCore();
    } catch(e) {
      setActionsByAgent(prev => ({ ...prev, [agent]: (prev[agent] || []).map(a => a.id===action.id ? {...a, status:"failed"} : a) }));
      setToast(e instanceof Error ? e.message : "Action failed");
    }
  }

  function rejectAction(action: ActionProposal) {
    setActionsByAgent(prev => ({ ...prev, [agent]: (prev[agent] || []).map(a => a.id===action.id ? {...a, status:"rejected"} : a) }));
  }

  async function saveGoal() {
    const latestUserMessage = [...(messagesByAgent[agent] || [])].reverse().find(m => m.role === "user")?.content || "";
    const goalText = objective.trim() || latestUserMessage.trim();
    if (!goalText) {
      setToast("Enter an objective before saving a goal");
      return;
    }
    try {
      await api("/api/goals",{method:"POST",body:JSON.stringify({title:goalText,description:"Created from AI-Crew Control Center"})});
      setToast("Goal saved"); await loadCore();
    } catch(e) { setToast(e instanceof Error ? e.message : "Could not save goal"); }
  }

  function openAgent(a:Agent) { setAgent(a.code); setPage("AI Command Center"); window.scrollTo({top:0,behavior:"smooth"}); }

  const pageContent = useMemo(() => {
    switch(page) {
      case "AI Command Center": return <CommandCenter agents={agents} agent={agent} setAgent={setAgent} objective={objective} setObjective={setObjective} result={result} loading={loading} run={run} saveGoal={saveGoal} openAgent={openAgent}
        messages={messagesByAgent[agent] || []} actions={actionsByAgent[agent] || []} approveAction={approveAction} rejectAction={rejectAction} clearConversation={clearConversation}/>;
      case "Goals": return <Goals goals={goals} setToast={setToast}/>;
      case "Projects": return <Projects setToast={setToast}/>;
      case "Tasks": return <Tasks agents={agents} setToast={setToast}/>;
      case "Business": return <Business setToast={setToast}/>;
      case "Vendors": return <Vendors setToast={setToast}/>;
      case "Finance": return <Finance setToast={setToast}/>;
      case "Knowledge": return <Knowledge setToast={setToast}/>;
      default: return <DashboardPage dashboard={dashboard} agents={agents} goals={goals} openAgent={openAgent} goAI={()=>setPage("AI Command Center")} aiMode={aiMode}/>;
    }
  }, [page, agents, goals, dashboard, agent, objective, result, loading, messagesByAgent, actionsByAgent, aiMode]);

  return <div className="shell">
    <aside>
      <div className="brand">AI-Crew</div><div className="tag">AI Operating System</div>
      {navigation.map(item=><button className={`nav ${page===item?"active":""}`} key={item} onClick={()=>setPage(item)}>{item}</button>)}
    </aside>
    <main>
      <header><div><h1>Company Control Center</h1><p>Coordinate AI employees, goals and business execution.</p></div><span className="status">● Local system online</span></header>
      {pageContent}
    </main>
    {toast && <div className="toast">{toast}</div>}
  </div>;
}

function DashboardPage({dashboard,agents,goals,openAgent,goAI,aiMode}:{dashboard:Dashboard|null;agents:Agent[];goals:Goal[];openAgent:(a:Agent)=>void;goAI:()=>void;aiMode:string}) {
  return <>
    <section className="grid metrics">
      <Metric label="AI Employees" value={dashboard?.agents ?? agents.length}/>
      <Metric label="Company Goals" value={dashboard?.goals ?? goals.length}/>
      <Metric label="Open Tasks" value={dashboard?.openTasks ?? 0}/>
      <Metric label="Projects" value={dashboard?.projects ?? 0}/>
      <Metric label="Vendors" value={dashboard?.vendors ?? 0}/>
      <Metric label="Knowledge Docs" value={dashboard?.knowledge ?? 0}/>
      <Metric label="Cash Balance" value={`₹${Number(dashboard?.balance ?? 0).toLocaleString()}`}/>
      <Metric label="AI Mode" value={aiMode}/>
    </section>
    <section className="card command hero-card"><div><h2>AI Workforce</h2><p>Your AI employees are online and ready to receive objectives.</p></div><button onClick={goAI}>Open AI Command Center</button></section>
    <PageHeader title="AI Employees" description="Five specialized digital employees coordinate company execution."/>
    <div className="agents">{agents.map(a=><button className="card agent" key={a.code} onClick={()=>openAgent(a)}><div className="avatar">{a.name[0]}</div><div><h3>{a.name}</h3><small>{a.department}</small><p>{a.description}</p><span>Open Agent →</span></div></button>)}</div>
  </>;
}
function Metric({label,value}:{label:string;value:ReactNode}) { return <div className="card metric"><span>{label}</span><strong>{value}</strong></div>; }

function RichResponse({content}:{content:string}) {
  const lines = content.split(/\r?\n/);
  return <div className="ai-response">
    {lines.map((line, index) => {
      const trimmed = line.trim();
      if (!trimmed) return <div className="response-spacer" key={index}/>;
      if (trimmed.startsWith("### ")) return <h4 key={index}>{formatInline(trimmed.slice(4))}</h4>;
      if (trimmed.startsWith("## ")) return <h3 key={index}>{formatInline(trimmed.slice(3))}</h3>;
      if (trimmed.startsWith("# ")) return <h2 key={index}>{formatInline(trimmed.slice(2))}</h2>;
      if (/^\d+\.\s+/.test(trimmed)) {
        return <div className="response-list-item" key={index}><span className="list-number">{trimmed.match(/^\d+/)?.[0]}.</span><span>{formatInline(trimmed.replace(/^\d+\.\s+/, ""))}</span></div>;
      }
      if (/^[-*]\s+/.test(trimmed)) {
        return <div className="response-list-item" key={index}><span className="list-dot">•</span><span>{formatInline(trimmed.replace(/^[-*]\s+/, ""))}</span></div>;
      }
      if (trimmed.startsWith("|")) return <div className="response-table-row" key={index}>{trimmed}</div>;
      return <p key={index}>{formatInline(trimmed)}</p>;
    })}
  </div>;
}

function formatInline(text:string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2,-2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1,-1)}</code>;
    return <span key={index}>{part}</span>;
  });
}

function CommandCenter({
  agents,agent,setAgent,objective,setObjective,result,loading,run,saveGoal,openAgent,messages,actions,approveAction,rejectAction,clearConversation
}:{
  agents:Agent[];agent:string;setAgent:(x:string)=>void;objective:string;setObjective:(x:string)=>void;
  result:Record<string,unknown>|null;loading:boolean;run:(message?:string)=>void;saveGoal:()=>void;openAgent:(a:Agent)=>void;
  messages:{role:"user"|"assistant";content:string}[];actions:ActionProposal[];approveAction:(a:ActionProposal)=>void;rejectAction:(a:ActionProposal)=>void;clearConversation:()=>void
}) {
 const selected = agents.find(a=>a.code===agent);
 return <>
   <PageHeader title="AI Command Center" description="Work with your AI employees as a real company team."/>
   <section className="card command">
    <div className="command-agent-head">
      <div>
        <div className="eyebrow">ACTIVE AI EMPLOYEE</div>
        <h2>{selected?.name || agent}</h2>
        <p>{selected?.description || "Specialized company AI employee."}</p>
      </div>
      <Badge text={agent}/>
    </div>

    <Field label="AI employee">
      <select value={agent} onChange={e=>setAgent(e.target.value)}>
        {agents.map(a=><option key={a.code} value={a.code}>{a.name}</option>)}
      </select>
    </Field>

    <div className="conversation">
      {messages.length === 0 ? (
        <div className="conversation-empty">
          <div className="avatar large">{selected?.name?.[0] || "A"}</div>
          <strong>Start a conversation with {selected?.name || "your AI employee"}</strong>
          <span>Give the employee a business objective, ask a follow-up, challenge its recommendation, or ask what information it needs.</span>
        </div>
      ) : messages.map((m,i)=>
        <div className={`message ${m.role}`} key={`${m.role}-${i}`}>
          <div className="message-label">{m.role==="user" ? "You" : selected?.name || agent}</div>
          {m.role==="assistant" ? <RichResponse content={m.content}/> : <div className="user-message">{m.content}</div>}
        </div>
      )}
      {loading && <div className="message assistant"><div className="message-label">{selected?.name || agent}</div><div className="thinking"><span/> <span/> <span/> Thinking through the objective...</div></div>}
    </div>

    <Field label={messages.length ? "Continue the conversation" : "Objective / message"}>
      <textarea className="chat-input" value={objective} onChange={e=>setObjective(e.target.value)}
        onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){e.preventDefault();run()}}}
        placeholder={messages.length ? "Ask a follow-up, challenge the plan, or give new information..." : "Example: We need to increase MRR by 20% within 90 days. Build a strategic plan."}/>
    </Field>

    {actions.length > 0 && <section className="approval-panel">
      <div className="eyebrow">PROPOSED COMPANY ACTIONS</div>
      <h3>Human approval required</h3>
      <p>The AI can recommend changes, but AI-Crew will not modify company data until you approve them.</p>
      {actions.map(a=><div className="approval-card" key={a.id}>
        <div><strong>{a.tool.replaceAll("_"," ")}</strong><span>{a.description}</span><pre>{JSON.stringify(a.arguments,null,2)}</pre></div>
        <div className="row-actions">{a.status==="pending" ? <><button className="mini" onClick={()=>approveAction(a)}>Approve</button><button className="mini danger" onClick={()=>rejectAction(a)}>Reject</button></> : <Badge text={a.status || "pending"}/>}</div>
      </div>)}
    </section>}
    <div className="actions">
      <button onClick={()=>run()} disabled={loading || !objective.trim()}>{loading?"Thinking...":"Run AI"}</button>
      <button className="secondary" onClick={saveGoal}>Save as Goal</button>
      {messages.length>0 && <button className="secondary" onClick={clearConversation}>New conversation</button>}
    </div>
    <div className="shortcut-hint">Tip: press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send.</div>
   </section>

   <PageHeader title="AI Workforce" description="Each employee has a different responsibility and decision-making lens."/>
   <div className="agents">{agents.map(a=><button className="card agent" key={a.code} onClick={()=>openAgent(a)}><div className="avatar">{a.name[0]}</div><div><h3>{a.name}</h3><small>{a.department}</small><p>{a.description}</p><span>Open Agent →</span></div></button>)}</div>
 </>;
}

function Goals({goals,setToast}:{goals:Goal[];setToast:(x:string)=>void}) {
 const [form,setForm]=useState({title:"",description:""}); const [editing,setEditing]=useState<number|null>(null);
 const save=async()=>{try{await api(`/api/goals${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({title:"",description:""});setEditing(null);setToast(editing?"Goal updated":"Goal created");window.location.reload();}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 return <><PageHeader title="Goals" description="Define outcomes that guide AI employees and company execution."/>
 <section className="split"><section className="card command"><h3>{editing?"Edit goal":"Create goal"}</h3><Field label="Title"><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Increase monthly revenue by 20%"/></Field><Field label="Description"><textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></Field><div className="actions"><button onClick={save}>{editing?"Update Goal":"Create Goal"}</button>{editing&&<button className="secondary" onClick={()=>setEditing(null)}>Cancel</button>}</div></section>
 <section className="card command"><h3>Company goals</h3>{goals.length?<div className="list">{goals.map(g=><div className="list-row" key={g.id}><div><strong>{g.title}</strong><span>{g.description||"No description"}</span></div><div className="row-actions"><button className="mini" onClick={()=>{setEditing(g.id);setForm({title:g.title,description:g.description||""})}}>Edit</button><button className="mini danger" onClick={async()=>{if(confirm("Delete this goal?")){await api(`/api/goals/${g.id}`,{method:"DELETE"});window.location.reload()}}}>Delete</button></div></div>)}</div>:<Empty text="Create a measurable company outcome."/>}</section></section></>;
}

function Projects({setToast}:{setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Project[]>([]); const [form,setForm]=useState({name:"",description:"",status:"PLANNED"}); const [editing,setEditing]=useState<number|null>(null);
 const load=async()=>setItems(await api<Project[]>("/api/projects")); useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/projects${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({name:"",description:"",status:"PLANNED"});setEditing(null);await load();setToast(editing?"Project updated":"Project created");}catch(e){setToast(e instanceof Error?e.message:"Save failed");}};
 const edit=(x:Project)=>{setEditing(x.id);setForm({name:x.name,description:x.description||"",status:x.status});};
 const del=async(id:number)=>{if(!confirm("Delete this project and its tasks?"))return;await api(`/api/projects/${id}`,{method:"DELETE"});await load();setToast("Project deleted");};
 return <><PageHeader title="Projects" description="Plan initiatives, track status and organize execution."/>
 <section className="split"><section className="card command"><h3>{editing?"Edit project":"Create project"}</h3><Field label="Name"><input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="AI growth initiative"/></Field><Field label="Description"><textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></Field><Field label="Status"><select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option>PLANNED</option><option>ACTIVE</option><option>ON_HOLD</option><option>COMPLETED</option></select></Field><div className="actions"><button onClick={save}>{editing?"Update":"Create Project"}</button>{editing&&<button className="secondary" onClick={()=>{setEditing(null);setForm({name:"",description:"",status:"PLANNED"})}}>Cancel</button>}</div></section>
 <section className="card command"><h3>Project portfolio</h3>{items.length?<div className="list">{items.map(x=><div className="list-row" key={x.id}><div><strong>{x.name}</strong><span>{x.description||"No description"}</span></div><Badge text={x.status}/><div className="row-actions"><button className="mini" onClick={()=>edit(x)}>Edit</button><button className="mini danger" onClick={()=>del(x.id)}>Delete</button></div></div>)}</div>:<Empty text="Create your first company initiative."/>}</section></section></>;
}

function Tasks({agents,setToast}:{agents:Agent[];setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Task[]>([]); const [projects,setProjects]=useState<Project[]>([]); const [form,setForm]=useState({title:"",description:"",status:"TODO",assignedAgent:"",projectId:""}); const [editing,setEditing]=useState<number|null>(null);
 const load=async()=>{const [t,p]=await Promise.all([api<Task[]>("/api/tasks"),api<Project[]>("/api/projects")]);setItems(t);setProjects(p)}; useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/tasks${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify({...form,projectId:form.projectId||null})});setForm({title:"",description:"",status:"TODO",assignedAgent:"",projectId:""});setEditing(null);await load();setToast(editing?"Task updated":"Task created")}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 const edit=(x:Task)=>{setEditing(x.id);setForm({title:x.title,description:x.description||"",status:x.status,assignedAgent:x.assigned_agent||"",projectId:x.project_id?String(x.project_id):""})};
 const del=async(id:number)=>{if(!confirm("Delete this task?"))return;await api(`/api/tasks/${id}`,{method:"DELETE"});await load();setToast("Task deleted")};
 return <><PageHeader title="Tasks" description="Turn objectives into assignable, trackable work."/>
 <section className="split"><section className="card command"><h3>{editing?"Edit task":"Create task"}</h3><Field label="Title"><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Prepare Q4 revenue analysis"/></Field><Field label="Description"><textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></Field><div className="form-grid"><Field label="Status"><select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option>TODO</option><option>IN_PROGRESS</option><option>BLOCKED</option><option>DONE</option></select></Field><Field label="Project"><select value={form.projectId} onChange={e=>setForm({...form,projectId:e.target.value})}><option value="">No project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></Field></div><Field label="Assigned AI employee"><select value={form.assignedAgent} onChange={e=>setForm({...form,assignedAgent:e.target.value})}><option value="">Unassigned</option>{agents.map(a=><option key={a.code} value={a.code}>{a.name}</option>)}</select></Field><div className="actions"><button onClick={save}>{editing?"Update":"Create Task"}</button>{editing&&<button className="secondary" onClick={()=>setEditing(null)}>Cancel</button>}</div></section>
 <section className="card command"><h3>Execution queue</h3>{items.length?<div className="list">{items.map(x=><div className="list-row" key={x.id}><div><strong>{x.title}</strong><span>{x.project_name||"No project"} · {x.assigned_agent||"Unassigned"}</span></div><Badge text={x.status}/><div className="row-actions"><button className="mini" onClick={()=>edit(x)}>Edit</button><button className="mini danger" onClick={()=>del(x.id)}>Delete</button></div></div>)}</div>:<Empty text="Tasks created here will become the execution queue."/>}</section></section></>;
}

function Business({setToast}:{setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Metric[]>([]); const [summary,setSummary]=useState<Record<string,number>>({}); const [form,setForm]=useState({metricName:"",value:"",unit:"",period:"",notes:""}); const [editing,setEditing]=useState<number|null>(null);
 const load=async()=>{const [m,s]=await Promise.all([api<Metric[]>("/api/business/metrics"),api<Record<string,number>>("/api/business/summary")]);setItems(m);setSummary(s)}; useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/business/metrics${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({metricName:"",value:"",unit:"",period:"",notes:""});setEditing(null);await load();setToast("Business metric saved")}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 const edit=(x:Metric)=>{setEditing(x.id);setForm({metricName:x.metric_name,value:String(x.value),unit:x.unit||"",period:x.period||"",notes:x.notes||""})};
 return <><PageHeader title="Business" description="Track company KPIs, execution health and operating metrics."/>
 <div className="grid four"><Metric label="Projects" value={summary.projects??0}/><Metric label="Open Tasks" value={summary.openTasks??0}/><Metric label="Completed Tasks" value={summary.completedTasks??0}/><Metric label="Vendors" value={summary.vendors??0}/></div>
 <section className="split"><section className="card command"><h3>{editing?"Edit KPI":"Add KPI"}</h3><Field label="Metric"><input value={form.metricName} onChange={e=>setForm({...form,metricName:e.target.value})} placeholder="Monthly revenue"/></Field><div className="form-grid"><Field label="Value"><input type="number" value={form.value} onChange={e=>setForm({...form,value:e.target.value})}/></Field><Field label="Unit"><input value={form.unit} onChange={e=>setForm({...form,unit:e.target.value})} placeholder="INR / % / count"/></Field></div><Field label="Period"><input value={form.period} onChange={e=>setForm({...form,period:e.target.value})} placeholder="September 2026"/></Field><Field label="Notes"><textarea value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></Field><button onClick={save}>{editing?"Update KPI":"Add KPI"}</button></section>
 <section className="card command"><h3>Company KPIs</h3>{items.length?<div className="list">{items.map(x=><div className="list-row" key={x.id}><div><strong>{x.metric_name}: {Number(x.value).toLocaleString()} {x.unit||""}</strong><span>{x.period||"Current"} · {x.notes||"No notes"}</span></div><div className="row-actions"><button className="mini" onClick={()=>edit(x)}>Edit</button><button className="mini danger" onClick={async()=>{await api(`/api/business/metrics/${x.id}`,{method:"DELETE"});await load()}}>Delete</button></div></div>)}</div>:<Empty text="Add revenue, growth, conversion, customer or operational KPIs."/>}</section></section></>;
}

function Vendors({setToast}:{setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Vendor[]>([]); const [form,setForm]=useState({name:"",category:"",contact:"",status:"ACTIVE",notes:""}); const [editing,setEditing]=useState<number|null>(null);
 const load=async()=>setItems(await api<Vendor[]>("/api/vendors")); useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/vendors${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({name:"",category:"",contact:"",status:"ACTIVE",notes:""});setEditing(null);await load();setToast("Vendor saved")}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 return <><PageHeader title="Vendors" description="Manage external partners, service providers and supplier relationships."/>
 <section className="split"><section className="card command"><h3>{editing?"Edit vendor":"Add vendor"}</h3><Field label="Name"><input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="Vendor name"/></Field><div className="form-grid"><Field label="Category"><input value={form.category} onChange={e=>setForm({...form,category:e.target.value})}/></Field><Field label="Status"><select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}><option>ACTIVE</option><option>ONBOARDING</option><option>PAUSED</option><option>INACTIVE</option></select></Field></div><Field label="Contact"><input value={form.contact} onChange={e=>setForm({...form,contact:e.target.value})}/></Field><Field label="Notes"><textarea value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})}/></Field><div className="actions"><button onClick={save}>{editing?"Update":"Add Vendor"}</button>{editing&&<button className="secondary" onClick={()=>setEditing(null)}>Cancel</button>}</div></section>
 <section className="card command"><h3>Vendor directory</h3>{items.length?<div className="list">{items.map(x=><div className="list-row" key={x.id}><div><strong>{x.name}</strong><span>{x.category||"General"} · {x.contact||"No contact"} · {x.notes||""}</span></div><Badge text={x.status}/><div className="row-actions"><button className="mini" onClick={()=>{setEditing(x.id);setForm({name:x.name,category:x.category||"",contact:x.contact||"",status:x.status,notes:x.notes||""})}}>Edit</button><button className="mini danger" onClick={async()=>{if(confirm("Delete this vendor?")){await api(`/api/vendors/${x.id}`,{method:"DELETE"});await load()}}}>Delete</button></div></div>)}</div>:<Empty text="Add the companies your AI workforce depends on."/>}</section></section></>;
}

function Finance({setToast}:{setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Transaction[]>([]); const [summary,setSummary]=useState({income:0,expense:0,balance:0}); const [form,setForm]=useState({type:"EXPENSE",category:"",amount:"",description:"",transactionDate:new Date().toISOString().slice(0,10)}); const [editing,setEditing]=useState<number|null>(null);
 const load=async()=>{const [t,s]=await Promise.all([api<Transaction[]>("/api/finance/transactions"),api<typeof summary>("/api/finance/summary")]);setItems(t);setSummary(s)}; useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/finance/transactions${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({...form,category:"",amount:"",description:""});setEditing(null);await load();setToast("Transaction saved")}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 return <><PageHeader title="Finance" description="Track income, expenses and the operating cash position."/>
 <div className="grid three"><Metric label="Income" value={`₹${Number(summary.income).toLocaleString()}`}/><Metric label="Expenses" value={`₹${Number(summary.expense).toLocaleString()}`}/><Metric label="Balance" value={`₹${Number(summary.balance).toLocaleString()}`}/></div>
 <section className="split"><section className="card command"><h3>{editing?"Edit transaction":"Record transaction"}</h3><Field label="Type"><select value={form.type} onChange={e=>setForm({...form,type:e.target.value})}><option>EXPENSE</option><option>INCOME</option></select></Field><div className="form-grid"><Field label="Category"><input value={form.category} onChange={e=>setForm({...form,category:e.target.value})} placeholder="Software"/></Field><Field label="Amount"><input type="number" min="0" step="0.01" value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})}/></Field></div><Field label="Date"><input type="date" value={form.transactionDate} onChange={e=>setForm({...form,transactionDate:e.target.value})}/></Field><Field label="Description"><textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></Field><div className="actions"><button onClick={save}>{editing?"Update":"Record"}</button>{editing&&<button className="secondary" onClick={()=>setEditing(null)}>Cancel</button>}</div></section>
 <section className="card command"><h3>Ledger</h3>{items.length?<div className="list">{items.map(x=><div className="list-row" key={x.id}><div><strong className={x.type==="INCOME"?"positive":"negative"}>{x.type==="INCOME"?"+":"-"} ₹{Number(x.amount).toLocaleString()} · {x.category}</strong><span>{x.transaction_date} · {x.description||"No description"}</span></div><div className="row-actions"><button className="mini" onClick={()=>{setEditing(x.id);setForm({type:x.type,category:x.category,amount:String(x.amount),description:x.description||"",transactionDate:x.transaction_date})}}>Edit</button><button className="mini danger" onClick={async()=>{if(confirm("Delete this transaction?")){await api(`/api/finance/transactions/${x.id}`,{method:"DELETE"});await load()}}}>Delete</button></div></div>)}</div>:<Empty text="Record the first income or expense to start your ledger."/>}</section></section></>;
}

function Knowledge({setToast}:{setToast:(x:string)=>void}) {
 const [items,setItems]=useState<Document[]>([]); const [form,setForm]=useState({title:"",content:""}); const [q,setQ]=useState(""); const [editing,setEditing]=useState<number|null>(null);
 const load=async(query="")=>setItems(await api<Document[]>(query?`/api/knowledge/search?q=${encodeURIComponent(query)}`:"/api/knowledge/documents")); useEffect(()=>{load().catch(e=>setToast(e.message));},[]);
 const save=async()=>{try{await api(`/api/knowledge/documents${editing?`/${editing}`:""}`,{method:editing?"PUT":"POST",body:JSON.stringify(form)});setForm({title:"",content:""});setEditing(null);await load(q);setToast("Knowledge document saved")}catch(e){setToast(e instanceof Error?e.message:"Save failed")}};
 return <><PageHeader title="Knowledge" description="Build a searchable company memory for people and AI employees." action={<input className="search" value={q} onChange={e=>{setQ(e.target.value);load(e.target.value).catch(err=>setToast(err.message))}} placeholder="Search knowledge..."/>}/>
 <section className="split"><section className="card command"><h3>{editing?"Edit document":"Add knowledge"}</h3><Field label="Title"><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Company onboarding guide"/></Field><Field label="Content"><textarea className="large-text" value={form.content} onChange={e=>setForm({...form,content:e.target.value})} placeholder="Policies, product knowledge, procedures, decisions..."/></Field><div className="actions"><button onClick={save}>{editing?"Update":"Add to Knowledge"}</button>{editing&&<button className="secondary" onClick={()=>setEditing(null)}>Cancel</button>}</div></section>
 <section className="card command"><h3>Company memory</h3>{items.length?<div className="knowledge-list">{items.map(x=><article className="knowledge" key={x.id}><div className="knowledge-top"><h4>{x.title}</h4><div className="row-actions"><button className="mini" onClick={()=>{setEditing(x.id);setForm({title:x.title,content:x.content})}}>Edit</button><button className="mini danger" onClick={async()=>{if(confirm("Delete this document?")){await api(`/api/knowledge/documents/${x.id}`,{method:"DELETE"});await load(q)}}}>Delete</button></div></div><p>{x.content}</p></article>)}</div>:<Empty text="Add company policies, product docs and operational knowledge."/>}</section></section></>;
}

function Badge({text}:{text:string}) { return <span className="badge">{text.replaceAll("_"," ")}</span>; }
