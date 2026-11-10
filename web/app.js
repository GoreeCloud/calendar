"use strict";
// No external JavaScript, analytics, or third-party calendar account is required.
const $ = id => document.getElementById(id);
const state = {
  token: sessionStorage.getItem("gc-calendar-token"),
  calendars: [], events: [], tasks: [], view: "month",
  anchor: new Date(), hidden: new Set(), editing: null, loading: false
};
const byDay = d => new Date(d.getFullYear(),d.getMonth(),d.getDate());
const addDays = (d,n) => {const v=byDay(d);v.setDate(v.getDate()+n);return v;};
const dateKey = d => [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-");
const shortDate = d => new Intl.DateTimeFormat(undefined,{month:"short",day:"numeric"}).format(d);
const fullDate = d => new Intl.DateTimeFormat(undefined,{weekday:"long",month:"long",day:"numeric"}).format(d);
const timeText = s => new Intl.DateTimeFormat(undefined,{hour:"numeric",minute:"2-digit"}).format(new Date(s));
const localField = d => [dateKey(d),"T",String(d.getHours()).padStart(2,"0"),":",String(d.getMinutes()).padStart(2,"0")].join("");
const el = (tag,cls,text) => {const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
let toastTimer;
function toast(message) {const box=$("toast");box.textContent=message;box.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>box.hidden=true,4000);}
async function api(path,{method="GET",body}={}) {
  const headers = {"Authorization":"Bearer "+state.token};
  if(body!==undefined)headers["Content-Type"]="application/json";
  let response;
  try {
    response = await fetch("/api/v1"+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),cache:"no-store"});
  } catch {throw new Error("Connection unavailable. Your changes were not sent.");}
  if(response.status===401 && path!=="/login"){signOut(false);throw new Error("Your session expired. Sign in again.");}
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||"Request failed");
  return data;
}
function signedIn(yes){
  $("auth-screen").hidden=yes;$("app-shell").hidden=!yes;
  if(!yes)$("login-password").value="";
}
function signOut(notify=true){
  const old=state.token;state.token=null;sessionStorage.removeItem("gc-calendar-token");signedIn(false);
  if(old&&notify)fetch("/api/v1/logout",{method:"POST",headers:{"Authorization":"Bearer "+old}}).catch(()=>{});
}
async function start(){
  if(!state.token){signedIn(false);return;}
  try {const me=await api("/me");$("account-email").textContent=me.email;$("avatar").textContent=me.email.slice(0,1).toUpperCase();signedIn(true);await refresh();}
  catch(error){if(state.token){signOut(false);$("login-error").textContent=error.message;}}
}
async function refresh(){
  if(state.loading)return;
  state.loading=true;
  const board=$("main-view");board.replaceChildren(el("div","skeleton"));
  $("sync-state").textContent="● Syncing";
  try{
    const rangeStart=new Date(state.anchor.getFullYear(),state.anchor.getMonth()-2,1);
    const rangeEnd=new Date(state.anchor.getFullYear(),state.anchor.getMonth()+3,1);
    const [cal,eve,tasks]=await Promise.all([
      api("/calendars"),
      api("/events?start="+encodeURIComponent(rangeStart.toISOString())+"&end="+encodeURIComponent(rangeEnd.toISOString())),
      api("/tasks")
    ]);
    state.calendars=cal.calendars;state.events=eve.events;state.tasks=tasks.tasks;
    renderCalendarList();render();$("sync-state").textContent="● Connected";
  } catch(error){board.replaceChildren(el("p","empty",error.message));$("sync-state").textContent="● Offline";toast(error.message);}
  finally{state.loading=false;}
}
function renderCalendarList(){
  const list=$("calendar-list");list.replaceChildren();
  state.calendars.forEach(c=>{
    const label=el("label","calendar-item");label.style.margin="0";
    const check=el("input");check.type="checkbox";check.checked=!state.hidden.has(c.id);check.setAttribute("aria-label","Show "+c.name);
    check.addEventListener("change",()=>{if(check.checked)state.hidden.delete(c.id);else state.hidden.add(c.id);render();});
    const dot=el("span","calendar-dot");dot.style.backgroundColor=c.color;
    label.append(check,dot,el("span",null,c.name));list.append(label);
  });
}
function visibleEvents(){return state.events.filter(e=>!state.hidden.has(e.calendar_id));}
function colorFor(id){return state.calendars.find(c=>c.id===id)?.color||"#6475de";}
function eventChip(event){
  const b=el("button","event-pill",event.title);b.type="button";b.style.borderLeftColor=colorFor(event.calendar_id);
  b.title=event.title+" • "+timeText(event.start_at);b.addEventListener("click",e=>{e.stopPropagation();openEvent(event);});
  return b;
}
function eventsOn(date) {
  const from=byDay(date).getTime(),until=addDays(date,1).getTime();
  return visibleEvents().filter(e=>new Date(e.start_at).getTime()<until&&new Date(e.end_at).getTime()>from);
}
function setHeader(){
  const date=state.anchor,format=new Intl.DateTimeFormat(undefined,{month:"long",year:"numeric"});
  $("period-title").textContent=state.view==="tasks"?"Your tasks":state.view==="month"?format.format(date):state.view==="week"?"Week of "+shortDate(weekStart(date)):"Upcoming agenda";
  $("toolbar-caption").textContent=state.view==="tasks"?"Keep moving, one thing at a time.":"A little space for everything that matters.";
  document.querySelectorAll("[data-view]").forEach(b=>{const active=b.dataset.view===state.view;b.classList.toggle("active",active);b.setAttribute("aria-current",active?"page":"false");});
}
function weekStart(date){const d=byDay(date);d.setDate(d.getDate()-d.getDay());return d;}
function render(){setHeader();if(state.view==="month")renderMonth();else if(state.view==="week")renderWeek();else if(state.view==="agenda")renderAgenda();else renderTasks();}
function renderMonth(){
  const root=el("div","calendar-board"),grid=el("div","month-grid");
  ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].forEach(s=>grid.append(el("div","weekday",s)));
  const first=weekStart(new Date(state.anchor.getFullYear(),state.anchor.getMonth(),1));
  const today=dateKey(new Date());
  for(let i=0;i<42;i++){
    const date=addDays(first,i),events=eventsOn(date),day=el("div","day");
    if(date.getMonth()!==state.anchor.getMonth())day.classList.add("outside");
    if(dateKey(date)===today)day.classList.add("today");
    const number=el("button","day-number",String(date.getDate()));number.type="button";number.setAttribute("aria-label","Add event on "+fullDate(date));
    number.addEventListener("click",()=>openEvent(null,date));day.append(number);
    events.slice(0,3).forEach(e=>day.append(eventChip(e)));
    if(events.length>3)day.append(el("span","more-label","+"+(events.length-3)+" more"));
    grid.append(day);
  }
  root.append(grid);$("main-view").replaceChildren(root);
}
function renderWeek(){
  const root=el("div","calendar-board"),grid=el("div","week-board");
  const first=weekStart(state.anchor);
  for(let i=0;i<7;i++){
    const d=addDays(first,i),col=el("section","week-column"),date=el("div","week-date",new Intl.DateTimeFormat(undefined,{weekday:"short"}).format(d));
    date.append(el("strong",null,String(d.getDate())));
    col.append(date);const list=el("div","week-events");
    const events=eventsOn(d);
    events.forEach(e=>list.append(eventChip(e)));
    if(!events.length){const empty=el("button","secondary","＋ Add event");empty.addEventListener("click",()=>openEvent(null,d));list.append(empty);}
    col.append(list);grid.append(col);
  }
  root.append(grid);$("main-view").replaceChildren(root);
}
function renderAgenda(){
  const root=el("div","agenda-board");let added=0;
  for(let i=0;i<30;i++){
    const d=addDays(state.anchor,i),events=eventsOn(d);
    if(!events.length)continue;
    const section=el("section","agenda-section");section.append(el("h2","agenda-heading",fullDate(d)));
    events.forEach(e=>{
      const row=el("button","agenda-row");const mark=el("span","agenda-mark");mark.style.background=colorFor(e.calendar_id);
      const content=el("span");content.append(el("strong",null,e.title),el("small",null,timeText(e.start_at)+" – "+timeText(e.end_at)+(e.location?" · "+e.location:"")));
      row.append(mark,content);row.addEventListener("click",()=>openEvent(e));section.append(row);added++;
    });root.append(section);
  }
  if(!added)root.append(emptyView("Nothing on the horizon","You're all caught up for the next 30 days."));
  $("main-view").replaceChildren(root);
}
function emptyView(title,detail){const box=el("div","empty");box.append(el("span","empty-symbol","◷"),el("h2",null,title),el("p",null,detail));return box;}
function renderTasks(){
  const root=el("section","task-board"),head=el("div","task-header");head.append(el("h2",null,"Your to-dos"));
  const add=el("button","primary","＋ Add task");add.addEventListener("click",()=>openTask());head.append(add);root.append(head);
  if(!state.tasks.length)root.append(emptyView("A clear to-do list","Create a task when inspiration strikes."));
  const ul=el("ul","task-list");
  state.tasks.filter(t=>!state.hidden.has(t.calendar_id)).forEach(t=>{
    const row=el("li","task-row"),check=el("input");check.type="checkbox";check.checked=!!t.done;check.setAttribute("aria-label","Complete "+t.title);
    check.addEventListener("change",async()=>{try{await api("/tasks/"+t.id,{method:"PATCH",body:{done:check.checked}});await refresh();}catch(error){check.checked=!check.checked;toast(error.message);}});
    const name=el("span","task-text"+(t.done?" completed":""),t.title);
    if(t.due_at)name.append(el("small",null,"Due "+new Date(t.due_at).toLocaleString()));
    const del=el("button",null,"Delete");del.setAttribute("aria-label","Delete "+t.title);
    del.addEventListener("click",async()=>{if(!confirm("Delete this task?"))return;try{await api("/tasks/"+t.id,{method:"DELETE"});await refresh();}catch(error){toast(error.message);}});
    row.append(check,name,del);ul.append(row);
  });
  root.append(ul);$("main-view").replaceChildren(root);
}
function fillCalendars(select){
  select.replaceChildren();state.calendars.forEach(c=>{const option=el("option",null,c.name);option.value=c.id;select.append(option);});
}
function openEvent(event=null,date=new Date()){
  state.editing=event;fillCalendars($("event-calendar"));
  $("event-dialog-title").textContent=event?"Edit event":"New event";
  $("event-title").value=event?.title||"";
  let start=event?new Date(event.start_at):new Date(date.getFullYear(),date.getMonth(),date.getDate(),9,0);
  let end=event?new Date(event.end_at):new Date(start.getTime()+60*60*1000);
  $("event-start").value=localField(start);$("event-end").value=localField(end);
  $("event-calendar").value=event?.calendar_id||state.calendars[0]?.id||"";
  $("event-location").value=event?.location||"";
  $("event-description").value=event?.description||"";
  $("event-delete").hidden=!event;$("event-dialog").showModal();$("event-title").focus();
}
function openTask(){
  fillCalendars($("task-calendar"));"task-title";
  $("task-title").value="";$("task-due").value="";$("task-dialog").showModal();$("task-title").focus();
}
async function saveEvent(evt){
  evt.preventDefault();
  const start=new Date($("event-start").value),end=new Date($("event-end").value);
  if(!(end>start)){toast("End time must be after start time.");return;}
  const body={title:$("event-title").value,calendar_id:$("event-calendar").value,
    description:$("event-description").value,location:$("event-location").value,
    start_at:start.toISOString(),end_at:end.toISOString(),all_day:false};
  try{
    if(state.editing){body.version=state.editing.version;await api("/events/"+state.editing.id,{method:"PATCH",body});}
    else await api("/events",{method:"POST",body});
    $("event-dialog").close();await refresh();toast("Event saved.");
  }catch(error){toast(error.message);}
}
async function exportCalendar(){
  const cid=state.calendars.find(c=>!state.hidden.has(c.id))?.id;
  if(!cid){toast("Select a visible calendar first.");return;}
  try{
    const response=await fetch("/api/v1/export.ics?calendar_id="+encodeURIComponent(cid),{headers:{Authorization:"Bearer "+state.token}});
    if(!response.ok)throw new Error("Unable to export calendar");
    const blob=await response.blob(),url=URL.createObjectURL(blob),a=el("a");
    a.href=url;a.download="goreecloud-calendar.ics";document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);
    toast("Calendar exported.");
  }catch(error){toast(error.message);}
}
$("login-form").addEventListener("submit",async evt=>{
  evt.preventDefault();$("login-error").textContent="";
  try{
    const r=await fetch("/api/v1/login",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({email:$("login-email").value,password:$("login-password").value})});
    const data=await r.json();if(!r.ok)throw new Error(data.error||"Sign-in failed");
    state.token=data.token;sessionStorage.setItem("gc-calendar-token",state.token);await start();
  }catch(error){$("login-error").textContent=error.message;}
});
$("sign-out").addEventListener("click",()=>signOut());
$("mobile-signout").addEventListener("click",()=>signOut());
$("mobile-new-calendar").addEventListener("click",()=>$("calendar-dialog").showModal());
$("today-btn").addEventListener("click",()=>{state.anchor=new Date();refresh();});
$("prev-btn").addEventListener("click",()=>{const d=state.anchor;if(state.view==="month")d.setMonth(d.getMonth()-1);else d.setDate(d.getDate()-(state.view==="week"?7:30));refresh();});
$("next-btn").addEventListener("click",()=>{const d=state.anchor;if(state.view==="month")d.setMonth(d.getMonth()+1);else d.setDate(d.getDate()+(state.view==="week"?7:30));refresh();});
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{state.view=b.dataset.view;render();}));
["new-event","toolbar-create","mobile-create"].forEach(id=>$(id).addEventListener("click",()=>openEvent()));
$("new-calendar").addEventListener("click",()=>$("calendar-dialog").showModal());
$("event-form").addEventListener("submit",saveEvent);
$("calendar-form").addEventListener("submit",async e=>{
  e.preventDefault();try{await api("/calendars",{method:"POST",body:{name:$("calendar-name").value,color:$("calendar-color").value}});
  $("calendar-dialog").close();$("calendar-name").value="";await refresh();toast("Calendar created.");}catch(error){toast(error.message);}
});
$("task-form").addEventListener("submit",async e=>{
  e.preventDefault();try{await api("/tasks",{method:"POST",body:{title:$("task-title").value,calendar_id:$("task-calendar").value,due_at:$("task-due").value?new Date($("task-due").value).toISOString():null}});
  $("task-dialog").close();await refresh();toast("Task added.");}catch(error){toast(error.message);}
});
$("event-delete").addEventListener("click",async()=>{
  if(!state.editing||!confirm("Delete this event?"))return;
  try{await api("/events/"+state.editing.id,{method:"DELETE"});$("event-dialog").close();await refresh();toast("Event deleted.");}
  catch(error){toast(error.message);}
});
document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>$(b.dataset.close).close()));
$("export-btn").addEventListener("click",exportCalendar);
window.addEventListener("online",()=>{if(state.token)refresh();});
start();
