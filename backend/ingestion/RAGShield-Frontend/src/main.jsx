import React,{useMemo,useRef,useState} from "react";
import ReactDOM from "react-dom/client";
import {ArrowUp,Check,ChevronDown,Copy,FileText,FolderOpen,Loader2,Moon,Paperclip,Plus,Shield,ShieldCheck,Sparkles,User,X,AlertTriangle,Database,LockKeyhole,UploadCloud} from "lucide-react";
import "./styles.css";

const API=import.meta.env.VITE_API_BASE||"http://127.0.0.1:8000";
const MAP={user_001:"tenant_a",user_002:"tenant_b",user_003:"tenant_c"};
const chats=["Leave policy","Project overview","Security guidelines","HR handbook","Benefits information"];

async function json(r){const t=await r.text();try{return t?JSON.parse(t):{}}catch{return{detail:t}}}
function sources(s){if(!s)return[];if(Array.isArray(s))return s;return Object.entries(s).map(([k,v])=>({filename:k,...(typeof v==="object"?v:{})}));}

function App(){
 const [user,setUser]=useState("user_001"),[on,setOn]=useState(true),[tab,setTab]=useState("graph");
 const [q,setQ]=useState(""),[msgs,setMsgs]=useState([{id:"w",role:"assistant",text:"Ask questions about your documents. RAGShield will keep the retrieval and response path protected.",safe:true,sources:[]}]);
 const [docs,setDocs]=useState([]),[logs,setLogs]=useState([]),[busy,setBusy]=useState(false),[uploading,setUploading]=useState(false),[prog,setProg]=useState([0,0]),[err,setErr]=useState("");
 const input=useRef(null),tenant=MAP[user];
 const last=useMemo(()=>[...msgs].reverse().find(x=>x.role==="assistant"),[msgs]);

 async function upload(list){
  const all=[...list], ok=all.filter(f=>/\.(txt|pdf)$/i.test(f.name));
  if(!ok.length)return;
  setErr("");setUploading(true);setProg([0,ok.length]);
  setLogs(all.filter(f=>!/\.(txt|pdf)$/i.test(f.name)).map(f=>({name:f.name,status:"SKIPPED"})));
  for(const f of ok){
   setLogs(x=>[...x,{name:f.name,status:"UPLOADING"}]);
   try{
    const form=new FormData();form.append("file",f);form.append("tenant_id",tenant);
    let r=await fetch(API+"/documents/upload",{method:"POST",body:form}),d=await json(r);
    if(!r.ok)throw Error(d.detail||"Upload failed");
    if(d.status==="PENDING_SCAN"&&d.document_id){
      r=await fetch(API+"/documents/"+encodeURIComponent(d.document_id)+"/scan",{method:"POST"});
      d=await json(r);if(!r.ok)throw Error(d.detail||"Scan failed");
    }
    const status=String(d.status||"PROCESSED").toUpperCase();
    setDocs(x=>[{id:d.document_id||crypto.randomUUID(),name:f.name,tenant,status,sha256:d.sha256||""},...x]);
    setLogs(x=>x.map(a=>a.name===f.name&&a.status==="UPLOADING"?{...a,status}:a));
   }catch(e){setLogs(x=>x.map(a=>a.name===f.name&&a.status==="UPLOADING"?{...a,status:"ERROR",reason:e.message}:a))}
   setProg(x=>[x[0]+1,x[1]]);
  }
  setUploading(false);
 }

 async function ask(e){
  e?.preventDefault();const text=q.trim();if(!text||busy)return;
  setQ("");setErr("");setMsgs(x=>[...x,{id:crypto.randomUUID(),role:"user",text}]);setBusy(true);
  try{
   const r=await fetch(API+"/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:user,query:text})});
   const d=await json(r);if(!r.ok)throw Error(d.detail||"RAGShield request failed");
   setMsgs(x=>[...x,{id:crypto.randomUUID(),role:"assistant",text:d.answer||"Request blocked by RAGShield.",safe:d.safe===true,blocked:d.blocked===true,threats:d.threats||[],sources:sources(d.sources)}]);
  }catch(e){setErr(e.message);setMsgs(x=>[...x,{id:crypto.randomUUID(),role:"assistant",text:"I couldn't reach the RAGShield backend. Make sure FastAPI is running on port 8000.",safe:false,blocked:true,sources:[]}] )}
  setBusy(false);
 }

 function reset(){setMsgs([{id:"w",role:"assistant",text:"Ask questions about your documents. RAGShield will keep the retrieval and response path protected.",safe:true,sources:[]}]);setQ("");setErr("")}

 return <div className="app">
  <aside className="side">
   <div className="brand"><div className="logo"><Shield size={27}/></div><div><b>RAGShield</b><small>Secure. Grounded. Yours.</small></div></div>
   <button className="new" onClick={reset}><Plus/> New Chat</button>
   <label>Recent</label>
   {chats.map((x,i)=><button className={"chat "+(!i?"sel":"")} key={x} onClick={!i?reset:undefined}><FileText/>{x}</button>)}
   <div className="bottom"><ShieldCheck/> Built for safer AI</div>
  </aside>

  <main>
   <header>
    <strong className="mobile-title">RAGShield</strong>
    <div className="head-actions">
     <div className="toggle-box"><div><b>RAGShield</b><small>{on?"Security layer active":"Visualization mode"}</small></div>
      <button className={"switch "+(on?"on":"")} onClick={()=>setOn(!on)}><span>{on?"ON":"OFF"}</span><i/></button>
     </div>
     <button className="moon"><Moon/></button>
     <div className="user"><User/><select value={user} onChange={e=>setUser(e.target.value)}>
      <option value="user_001">user_001 · tenant_a</option><option value="user_002">user_002 · tenant_b</option><option value="user_003">user_003 · tenant_c</option>
     </select><ChevronDown/></div>
    </div>
   </header>

   <div className="grid">
    <section className="chat-panel">
     <div className="hero"><div className="orb"/><h1>How can I help you today?</h1><p>Ask questions about your documents. RAGShield will keep the retrieval and response path safe.</p>
      <div className="tenant"><LockKeyhole/> Authorized tenant: <b>{tenant}</b></div>
     </div>
     <div className="messages">
      {msgs.map(m=><Message key={m.id} m={m}/>)}
      {busy&&<div className="message"><div className="avatar shield"><Shield/></div><div><b>RAGShield</b><div className="typing">● ● ●</div></div></div>}
     </div>
     {err&&<div className="error"><AlertTriangle/> <span>{err}</span><button onClick={()=>setErr("")}><X/></button></div>}
     <form className="composer" onSubmit={ask}>
      <button type="button" onClick={()=>input.current?.click()}><Paperclip/></button><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Ask a question about your documents..." disabled={busy}/>
      <button className="send" disabled={!q.trim()||busy}>{busy?<Loader2 className="spin"/>:<ArrowUp/>}</button>
     </form>
     <input ref={input} hidden type="file" multiple webkitdirectory="" directory="" accept=".txt,.pdf" onChange={e=>{upload(e.target.files);e.target.value=""}}/>
     <div className="hint"><button onClick={()=>input.current?.click()}><FolderOpen/> Upload a folder</button><span>PDF / TXT · each file is scanned before indexing</span></div>
     {logs.length>0&&<div className="upload"><div className="upload-head"><b>{uploading?"Scanning documents…":"Folder processing complete"}</b><span>{prog[0]}/{prog[1]} files processed</span></div><div className="bar"><i style={{width:(prog[1]?prog[0]/prog[1]*100:0)+"%"}}/></div>
      {logs.slice(-8).map((x,i)=><div className="up-row" key={i}><FileText/>{x.name}<strong className={x.status.toLowerCase()}>{x.status}</strong></div>)}
     </div>}
    </section>

    <aside className="security">
     <div className="tabs"><button className={tab==="graph"?"active":""} onClick={()=>setTab("graph")}>Execution Graph</button><button className={tab==="sources"?"active":""} onClick={()=>setTab("sources")}>Sources</button></div>
     {tab==="graph"?<Graph on={on}/>:<Sources docs={docs} sources={last?.sources||[]} tenant={tenant}/>}
     <div className="difference"><Sparkles/><div><b>See the difference.</b><p>Toggle RAGShield to visualize the protected execution path.</p></div></div>
     <div className="stats"><div>Tenant<b>{tenant}</b></div><div>Indexed<b>{docs.filter(d=>d.status!=="QUARANTINED").length}</b></div><div>Quarantined<b>{docs.filter(d=>d.status==="QUARANTINED").length}</b></div></div>
    </aside>
   </div>
  </main>
 </div>
}

function Message({m}){
 if(m.role==="user")return <div className="message usermsg"><div className="avatar usericon"><User/></div><div><b>You</b><div className="bubble">{m.text}</div></div></div>;
 return <div className="message"><div className={"avatar shield "+(m.safe===false?"bad":"")} >{m.safe===false?<AlertTriangle/>:<Shield/>}</div><div className="answerbox"><div className="name">RAGShield {m.safe===true&&<em>✓ SECURED</em>}{m.blocked&&<em className="blocked">⚠ BLOCKED</em>}</div><div className={"answer "+(m.safe===false?"badtext":"")}>{m.text}</div>
  {m.threats?.length>0&&<div className="threats"><b>Detected threats</b>{m.threats.map(t=><span key={t}>{t}</span>)}</div>}
  {m.sources?.length>0&&<div className="src"><label>Sources</label>{m.sources.slice(0,5).map((s,i)=><div key={i}><FileText/>{s.filename||s.file_name||s.name||"Source "+(i+1)}{(s.page||s.page_number)&&<small>p. {s.page||s.page_number}</small>}</div>)}</div>}
  {m.id!=="w"&&<div className="foot"><span className={m.safe===false?"red":""}>{m.safe===false?<AlertTriangle/>:<ShieldCheck/>} {m.safe===false?"Response protected":"Secured by RAGShield"}</span><button onClick={()=>navigator.clipboard?.writeText(m.text)}><Copy/></button></div>}
 </div></div>
}

function Graph({on}){
 const steps=[["User Query","Incoming request",User],["Retrieval Guard","Threat + tenant check",ShieldCheck],["Vector Search","Authorized documents only",Database],["LLM","Generate grounded answer",Sparkles],["Output Guard","Safety + grounding",ShieldCheck],["Safe Response","Released to user",Check]];
 return <div className="graph"><div className="modes"><div className={"mode "+(on?"chosen":"")}><i/> <div><b>RAGShield ON</b><small>Secured execution</small></div></div><div className={"mode off "+(!on?"chosen":"")}><i/> <div><b>RAGShield OFF</b><small>Direct execution visualization</small></div></div></div>
  <div className={"flow "+(!on?"dim":"")}>{steps.map(([a,b,I],i)=><React.Fragment key={a}><div className={"step "+(on?"protected":"")}><I/><div><b>{a}</b><small>{b}</small></div></div>{i<steps.length-1&&<div className="line"/>}</React.Fragment>)}</div></div>
}
function Sources({docs,sources,tenant}){return <div className="sources-view"><div className="sv-head"><div><h3>Authorized Sources</h3><p>Only documents belonging to {tenant} are eligible for retrieval.</p></div><LockKeyhole/></div>{sources.length>0&&<><label>Last response</label>{sources.map((s,i)=><div className="doc" key={i}><FileText/>{s.filename||s.name||"Source"}<Check/></div>)}</>}<label>Uploaded this session</label>{docs.filter(d=>d.tenant===tenant).length?<>{docs.filter(d=>d.tenant===tenant).map(d=><div className="doc" key={d.id}><FileText/>{d.name}<b className={d.status==="QUARANTINED"?"red":""}>{d.status}</b></div>)}</>:<div className="empty"><UploadCloud/><p>No documents uploaded yet.</p></div>}</div>}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);