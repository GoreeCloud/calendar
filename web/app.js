"use strict";
// No external JavaScript, analytics, or third-party calendar account is required.
const $ = id => document.getElementById(id);
const state = {
  token: sessionStorage.getItem("gc-calendar-token"),
  calendars: [], events: [], tasks: [], view: "month",
  anchor: new Date(), hidden: new Set(), editing: null, editingTask: null, taskFilter: "open", editingCalendar: null, sharingCalendar: null, loading: false
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
    response = await fetch("/api/v1"+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),cache:"no-store",redirect:"error"});
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
  if(old&&notify)fetch("/api/v1/logout",{method:"POST",headers:{"Authorization":"Bearer "+old},redirect:"error"}).catch(()=>{});
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
    checkLiveReminders();
  } catch(error){board.replaceChildren(el("p","empty",error.message));$("sync-state").textContent="● Offline";toast(error.message);}
  finally{state.loading=false;}
}
function calendarRole(id){return state.calendars.find(c=>c.id===id)?.role||"owner";}
function canEdit(id){return ["owner","edit"].includes(calendarRole(id));}
function renderCalendarList(){
  ["calendar-list","mobile-calendar-list"].forEach(id=>{
    const list=$(id);list.replaceChildren();
    state.calendars.forEach(c=>{
      const row=el("div","calendar-row");
      const label=el("label","calendar-item");label.style.margin="0";
      const check=el("input");check.type="checkbox";check.checked=!state.hidden.has(c.id);
      check.setAttribute("aria-label","Show "+c.name);
      check.addEventListener("change",()=>{
        if(check.checked)state.hidden.delete(c.id);else state.hidden.add(c.id);
        renderCalendarList();render();
      });
      const dot=el("span","calendar-dot");dot.style.backgroundColor=c.color;
      const caption=el("span","calendar-caption",c.name);
      label.append(check,dot,caption);row.append(label);
      if(c.role==="owner"){
        const share=el("button","share-action","Share");
        share.type="button";share.setAttribute("aria-label","Share "+c.name);
        share.addEventListener("click",()=>openShare(c));
        const settings=el("button","share-action","Edit");
        settings.type="button";settings.setAttribute("aria-label","Edit "+c.name+" settings");
        settings.addEventListener("click",()=>openCalendarSettings(c));
        row.append(share,settings);
      }else{
        const tag=el("span","share-role",c.role==="edit"?"Editor":c.role==="freebusy"?"Availability only":"Read only");
        row.append(tag);
      }
      list.append(row);
    });
  });
}
async function loadMembers(){
  const cid=state.sharingCalendar?.id;
  if(!cid)return;
  const box=$("share-members");box.replaceChildren(el("p","muted","Loading members…"));
  try{
    const {members}=await api("/calendars/"+cid+"/members");
    if(state.sharingCalendar?.id!==cid)return;
    box.replaceChildren();
    if(!members.length){box.append(el("p","muted","Only you have access."));return;}
    members.forEach(member=>{
      const row=el("div","member-row");
      const name=el("div");name.append(el("strong",null,member.email),
        el("small",null,member.role==="freebusy"?"Availability only":member.role==="read"?"Read-only access":"Can edit"));
      const remove=el("button","danger","Remove");remove.type="button";
      remove.setAttribute("aria-label","Remove "+member.email);
      remove.addEventListener("click",async()=>{
        if(!confirm("Remove calendar access for "+member.email+"?"))return;
        try{
          await api("/calendars/"+cid+"/members/"+encodeURIComponent(member.user_id),{method:"DELETE"});
          await loadMembers();toast("Member access revoked.");
        }catch(error){toast(error.message);}
      });
      row.append(name,remove);box.append(row);
    });
  }catch(error){box.replaceChildren(el("p","error",error.message));}
}
function openShare(calendar){
  if(calendar.role!=="owner")return;
  state.sharingCalendar=calendar;
  $("share-calendar-name").textContent=calendar.name;
  $("share-email").value="";$("share-role").value="freebusy";
  $("share-dialog").showModal();
  loadMembers();
}
function visibleEvents(){return state.events.filter(e=>!state.hidden.has(e.calendar_id));}
function colorFor(id){return state.calendars.find(c=>c.id===id)?.color||"#6475de";}
function eventChip(event){
  const b=el("button","event-pill",event.title);b.type="button";b.style.borderLeftColor=colorFor(event.calendar_id);
  b.title=event.title+" • "+(event.all_day?"All day":timeText(event.start_at));b.addEventListener("click",e=>{e.stopPropagation();openEvent(event);});
  return b;
}
function eventsOn(date) {
  const key=dateKey(date),from=byDay(date).getTime(),until=addDays(date,1).getTime();
  return visibleEvents().filter(e=>{
    if(e.all_day)return e.start_at.slice(0,10)<=key && e.end_at.slice(0,10)>key;
    return new Date(e.start_at).getTime()<until && new Date(e.end_at).getTime()>from;
  });
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
      const content=el("span");content.append(el("strong",null,e.title),el("small",null,(e.all_day?"All day":timeText(e.start_at)+" – "+timeText(e.end_at))+(e.location?" · "+e.location:"")));
      row.append(mark,content);row.addEventListener("click",()=>openEvent(e));section.append(row);added++;
    });root.append(section);
  }
  if(!added)root.append(emptyView("Nothing on the horizon","You're all caught up for the next 30 days."));
  $("main-view").replaceChildren(root);
}
function emptyView(title,detail){const box=el("div","empty");box.append(el("span","empty-symbol","◷"),el("h2",null,title),el("p",null,detail));return box;}
function renderTasks(){
  const root=el("section","task-board"),head=el("div","task-header");head.append(el("h2",null,"Your to-dos"));
  const filter=el("select","task-filter");
  filter.setAttribute("aria-label","Filter tasks");
  [["open","To do"],["all","All tasks"],["today","Due today"],["overdue","Overdue"],["completed","Completed"]].forEach(([value,label])=>{
    const option=el("option",null,label);option.value=value;filter.append(option);
  });
  filter.value=state.taskFilter;
  filter.addEventListener("change",()=>{state.taskFilter=filter.value;renderTasks();});
  const add=el("button","primary","＋ Add task");add.addEventListener("click",()=>openTask());
  head.append(filter,add);root.append(head);
  const todayStart=byDay(new Date()).getTime(),tomorrow=addDays(new Date(),1).getTime();
  const selected=state.tasks.filter(task=>{
    if(state.hidden.has(task.calendar_id))return false;
    const due=task.due_at?Date.parse(task.due_at):NaN;
    if(state.taskFilter==="open")return !task.done;
    if(state.taskFilter==="completed")return Boolean(task.done);
    if(state.taskFilter==="today")return !task.done&&due>=todayStart&&due<tomorrow;
    if(state.taskFilter==="overdue")return !task.done&&due<todayStart;
    return true;
  }).sort((a,b)=>Number(a.done)-Number(b.done)||(a.priority??3)-(b.priority??3)||
      String(a.due_at||"9999").localeCompare(String(b.due_at||"9999")));
  if(!selected.length)root.append(emptyView("No matching tasks","Try another filter or add a task."));
  const ul=el("ul","task-list");
  selected.forEach(t=>{
    const row=el("li","task-row"),check=el("input");
    check.type="checkbox";check.checked=!!t.done;check.disabled=!canEdit(t.calendar_id);
    check.setAttribute("aria-label","Complete "+t.title);
    check.addEventListener("change",async()=>{try{await api("/tasks/"+t.id,{method:"PATCH",body:{done:check.checked}});await refresh();}catch(error){check.checked=!check.checked;toast(error.message);}});
    const name=el("span","task-text"+(t.done?" completed":""),t.title);
    const tier=t.priority??3;
    const priorityText=["","P1 · Urgent","P2 · High","P3 · Normal","P4 · Low"][tier]||"P3 · Normal";
    name.append(el("small","task-priority-marker priority-"+tier,priorityText));
    if(t.due_at)name.append(el("small",null,"Due "+new Date(t.due_at).toLocaleString()));
    const del=el("button",null,"Delete");del.setAttribute("aria-label","Delete "+t.title);
    del.addEventListener("click",async()=>{if(!confirm("Delete this task?"))return;try{await api("/tasks/"+t.id,{method:"DELETE"});await refresh();}catch(error){toast(error.message);}});
    row.append(check,name);
    if(canEdit(t.calendar_id)){
      const edit=el("button",null,"Edit");edit.setAttribute("aria-label","Edit "+t.title);
      edit.addEventListener("click",()=>openTask(t));
      row.append(edit,del);
    }
    ul.append(row);
  });
  root.append(ul);$("main-view").replaceChildren(root);
}
function fillCalendars(select,includeReadOnly=false){
  select.replaceChildren();
  state.calendars.filter(c=>includeReadOnly||canEdit(c.id)).forEach(c=>{
    const option=el("option",null,c.name);option.value=c.id;select.append(option);
  });
}
function openEvent(event=null,date=new Date()){
  if(!event&&!state.calendars.some(c=>canEdit(c.id))){toast("No editable calendar is available.");return;}
  state.editing=event;
  const readOnly=Boolean(event&&!canEdit(event.calendar_id));
  fillCalendars($("event-calendar"),readOnly);
  $("event-dialog-title").textContent=readOnly?"Read-only event":event?.recurrence?"Edit recurring series":event?"Edit event":"New event";
  $("event-title").value=event?.title||"";
  const eventStart=event?.series_start_at||event?.start_at;
  const eventEnd=event?.series_end_at||event?.end_at;
  let start=event?new Date(eventStart):new Date(date.getFullYear(),date.getMonth(),date.getDate(),9,0);
  let end=event?new Date(eventEnd):new Date(start.getTime()+60*60*1000);
  $("event-start").value=event?.all_day?eventStart.slice(0,10)+"T00:00":localField(start);
  $("event-end").value=event?.all_day?eventEnd.slice(0,10)+"T00:00":localField(end);
  $("event-repeat").value=event?.recurrence?.freq||"NONE";
  $("repeat-interval").value=event?.recurrence?.interval||1;
  $("repeat-count").value=event?.recurrence?.count||12;
  $("repeat-fields").hidden=$("event-repeat").value==="NONE";
  $("event-all-day").checked=Boolean(event?.all_day);
  $("event-calendar").value=event?.calendar_id||state.calendars[0]?.id||"";
  $("event-reminder").value=event?.reminder_minutes==null?"":String(event.reminder_minutes);
  $("event-location").value=event?.location||"";
  $("event-description").value=event?.description||"";
  $("event-delete").hidden=!event||readOnly;
  $("event-skip").hidden=!event?.recurrence||!event?.occurrence_start_at||readOnly;
  $("event-skipped").hidden=!event?.recurrence||readOnly;
  $("event-save").hidden=readOnly;
  $("event-form").querySelectorAll("input,textarea,select").forEach(control=>control.disabled=readOnly);
  $("event-dialog").showModal();$("event-title").focus();
}
function openTask(task=null){
  if(task&&!canEdit(task.calendar_id)){toast("This task belongs to a read-only calendar.");return;}
  if(!task&&!state.calendars.some(c=>canEdit(c.id))){toast("No editable calendar is available.");return;}
  state.editingTask=task;
  fillCalendars($("task-calendar"),Boolean(task));
  $("task-dialog-title").textContent=task?"Edit task":"New task";
  $("task-save").textContent=task?"Save task":"Add task";
  $("task-title").value=task?.title||"";
  $("task-due").value=task?.due_at?localField(new Date(task.due_at)):"";
  $("task-priority").value=String(task?.priority??3);
  $("task-calendar").value=task?.calendar_id||state.calendars.find(c=>canEdit(c.id))?.id||"";
  $("task-calendar").disabled=Boolean(task);
  $("task-dialog").showModal();$("task-title").focus();
}
async function saveEvent(evt){
  evt.preventDefault();
  const allDay=$("event-all-day").checked;
  const startLocal=$("event-start").value,endLocal=$("event-end").value;
  if(!startLocal||!endLocal){toast("Choose valid start and end dates.");return;}
  let start,end;
  if(allDay){
    const date=startLocal.slice(0,10);
    let endDate=endLocal.slice(0,10);
    if(endDate<=date){
      const next=new Date(date+"T00:00:00Z");next.setUTCDate(next.getUTCDate()+1);
      endDate=next.toISOString().slice(0,10);
    }
    start=new Date(date+"T00:00:00Z");end=new Date(endDate+"T00:00:00Z");
  }else{
    start=new Date(startLocal);end=new Date(endLocal);
  }
  if(!Number.isFinite(start.getTime())||!Number.isFinite(end.getTime())||!(end>start)){
    toast("End time must be after start time.");return;
  }
  const body={title:$("event-title").value,calendar_id:$("event-calendar").value,
    description:$("event-description").value,location:$("event-location").value,
    start_at:start.toISOString(),end_at:end.toISOString(),all_day:allDay,
    reminder_minutes:$("event-reminder").value===""?null:Number($("event-reminder").value)};
  const frequency=$("event-repeat").value;
  if(frequency!=="NONE"){
    const interval=Number($("repeat-interval").value),count=Number($("repeat-count").value);
    if(!Number.isInteger(interval)||interval<1||interval>24||!Number.isInteger(count)||count<2||count>366){
      toast("Repeat interval must be 1–24 and occurrences 2–366.");return;
    }
    body.recurrence={freq:frequency,interval,count,
      tzid:allDay?null:(state.editing?.recurrence?.tzid||Intl.DateTimeFormat().resolvedOptions().timeZone||null)};
  }else if(state.editing?.recurrence){
    body.recurrence=null;
  }
  try{
    if(state.editing){body.version=state.editing.version;await api("/events/"+state.editing.id,{method:"PATCH",body});}
    else await api("/events",{method:"POST",body});
    $("event-dialog").close();await refresh();toast("Event saved.");
  }catch(error){toast(error.message);}
}
async function exportCalendar(){
  const cid=state.calendars.find(c=>!state.hidden.has(c.id)&&c.role!=="freebusy")?.id;
  if(!cid){toast("Select a visible calendar first.");return;}
  try{
    const response=await fetch("/api/v1/export.ics?calendar_id="+encodeURIComponent(cid),{headers:{Authorization:"Bearer "+state.token},redirect:"error"});
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
      body:JSON.stringify({email:$("login-email").value,password:$("login-password").value}),redirect:"error"});
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
$("mobile-calendars").addEventListener("click",()=>$("calendars-dialog").showModal());
function openCalendarSettings(calendar){
  if(calendar.role!=="owner")return;
  state.editingCalendar=calendar;
  $("settings-calendar-name").value=calendar.name;
  $("settings-calendar-description").value=calendar.description||"";
  $("settings-calendar-color").value=calendar.color;
  $("calendar-settings-dialog").showModal();
}
$("calendar-settings-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const calendar=state.editingCalendar;
  if(!calendar||calendar.role!=="owner")return;
  const save=$("settings-calendar-save");
  save.disabled=true;
  try{
    await api("/calendars/"+calendar.id,{method:"PATCH",body:{
      name:$("settings-calendar-name").value,
      description:$("settings-calendar-description").value,
      color:$("settings-calendar-color").value
    }});
    $("calendar-settings-dialog").close();
    await refresh();toast("Calendar settings saved.");
  }catch(error){toast(error.message);}
  finally{save.disabled=false;}
});
$("settings-calendar-delete").addEventListener("click",async()=>{
  const calendar=state.editingCalendar;
  if(!calendar||calendar.role!=="owner")return;
  if(!confirm("Permanently delete "+calendar.name+" and all of its events and tasks? This cannot be undone."))return;
  const button=$("settings-calendar-delete");
  button.disabled=true;
  try{
    await api("/calendars/"+calendar.id,{method:"DELETE"});
    state.hidden.delete(calendar.id);
    $("calendar-settings-dialog").close();
    await refresh();toast("Calendar deleted.");
  }catch(error){toast(error.message);}
  finally{button.disabled=false;}
});
$("share-form").addEventListener("submit",async e=>{
  e.preventDefault();
  if(!state.sharingCalendar)return;
  try{
    await api("/calendars/"+state.sharingCalendar.id+"/members",{method:"POST",
      body:{email:$("share-email").value.trim(),role:$("share-role").value}});
    $("share-email").value="";
    await loadMembers();toast("Calendar access updated.");
  }catch(error){toast(error.message);}
});
$("event-form").addEventListener("submit",saveEvent);
$("event-repeat").addEventListener("change",()=>$("repeat-fields").hidden=$("event-repeat").value==="NONE");
$("calendar-form").addEventListener("submit",async e=>{
  e.preventDefault();try{await api("/calendars",{method:"POST",body:{name:$("calendar-name").value,color:$("calendar-color").value}});
  $("calendar-dialog").close();$("calendar-name").value="";await refresh();toast("Calendar created.");}catch(error){toast(error.message);}
});
$("task-form").addEventListener("submit",async e=>{
  e.preventDefault();
  const title=$("task-title").value;
  const due_at=$("task-due").value?new Date($("task-due").value).toISOString():null;
  const priority=Number($("task-priority").value);
  try{
    if(state.editingTask){
      await api("/tasks/"+state.editingTask.id,{method:"PATCH",body:{title,due_at,priority}});
    }else{
      await api("/tasks",{method:"POST",body:{title,due_at,priority,calendar_id:$("task-calendar").value}});
    }
    $("task-dialog").close();await refresh();toast("Task saved.");
  }catch(error){toast(error.message);}
});
$("event-skip").addEventListener("click",async()=>{
  const event=state.editing;
  if(!event?.recurrence||!event.occurrence_start_at)return;
  if(!confirm("Skip only this occurrence? The remaining series will stay scheduled."))return;
  try{
    await api("/events/"+event.id+"/exclusions",{method:"POST",body:{
      occurrence_start_at:event.occurrence_start_at,version:event.version}});
    $("event-dialog").close();await refresh();toast("This date was skipped.");
  }catch(error){toast(error.message);}
});
$("event-skipped").addEventListener("click",async()=>{
  const event=state.editing;
  if(!event?.recurrence)return;
  $("event-dialog").close();$("skipped-dialog").showModal();
  const box=$("skipped-list");box.replaceChildren(el("p","muted","Loading skipped dates…"));
  try{
    const {exclusions}=await api("/events/"+event.id+"/exclusions");
    box.replaceChildren();
    if(!exclusions.length){box.append(el("p","muted","No dates are skipped."));return;}
    exclusions.forEach(instant=>{
      const row=el("div","member-row");
      const caption=el("span",null,new Date(instant).toLocaleString());
      const restore=el("button","secondary","Restore date");
      restore.addEventListener("click",async()=>{
        try{
          const result=await api("/events/"+event.id+"/exclusions?"+
            new URLSearchParams({occurrence_start_at:instant,version:String(event.version)}),{method:"DELETE"});
          event.version=result.version;row.remove();await refresh();toast("Date restored.");
        }catch(error){toast(error.message);}
      });
      row.append(caption,restore);box.append(row);
    });
  }catch(error){box.replaceChildren(el("p","error",error.message));}
});
$("event-delete").addEventListener("click",async()=>{
  if(!state.editing||!confirm("Delete this event?"))return;
  try{await api("/events/"+state.editing.id,{method:"DELETE"});$("event-dialog").close();await refresh();toast("Event deleted.");}
  catch(error){toast(error.message);}
});
document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>$(b.dataset.close).close()));
function renderSearch(result){
  const root=$("search-results");root.replaceChildren();
  const {events,tasks}=result;
  if(!events.length&&!tasks.length){root.append(el("p","muted","No matching events or tasks."));return;}
  const heading=el("p","search-summary",events.length+" event(s) · "+tasks.length+" task(s)");
  root.append(heading);
  if(events.length){
    root.append(el("h3",null,"Events"));
    events.forEach(event=>{
      const row=el("button","search-result");
      const date=event.all_day?event.start_at.slice(0,10):shortDate(new Date(event.start_at));
      row.append(el("strong",null,event.title),el("small",null,date+(event.location?" · "+event.location:"")));
      row.addEventListener("click",async()=>{
        $("search-dialog").close();
        state.anchor=event.all_day?new Date(event.start_at.slice(0,10)+"T12:00:00"):new Date(event.start_at);
        state.view="agenda";
        await refresh();
      });
      root.append(row);
    });
  }
  if(tasks.length){
    root.append(el("h3",null,"Tasks"));
    tasks.forEach(task=>{
      const row=el("button","search-result");
      row.append(el("strong",null,task.title),el("small",null,task.done?"Completed":"To do"));
      row.addEventListener("click",()=>{
        $("search-dialog").close();state.view="tasks";render();
      });
      root.append(row);
    });
  }
}
const notifiedReminders=new Set();
let browserAlertsEnabled=false;
// Browser reminders are opportunistic while this tab is open, not background push.
function checkLiveReminders(){
  if(!state.token)return;
  const now=Date.now();
  for(const event of visibleEvents()){
    if(event.reminder_minutes===null||event.reminder_minutes===undefined)continue;
    const due=Date.parse(event.start_at)-Number(event.reminder_minutes)*60000;
    if(!Number.isFinite(due)||due>now||due<now-120000)continue;
    const key=event.id+":"+(event.occurrence_start_at||event.start_at)+":"+event.reminder_minutes;
    if(notifiedReminders.has(key))continue;
    notifiedReminders.add(key);
    const message="Reminder: "+event.title+(event.all_day?" (all day)":" at "+timeText(event.start_at));
    toast(message);
    if(browserAlertsEnabled&&"Notification" in window&&Notification.permission==="granted"){
      try{new Notification("GoreeCloud Calendar",{body:message,tag:key});}catch{/*toast remains visible*/}
    }
  }
}
$("enable-alerts").addEventListener("click",async()=>{
  if(!("Notification" in window)){toast("This browser does not support desktop notifications.");return;}
  try{
    const permission=await Notification.requestPermission();
    browserAlertsEnabled=permission==="granted";
    toast(browserAlertsEnabled?"Browser alerts enabled while this tab is open.":"Browser alert permission was not granted.");
  }catch{toast("Browser alerts are not available in this context.");}
});
setInterval(checkLiveReminders,30000);
let availabilityRequest=0;
function availabilityDay(value){
  if(!/^\d{4}-\d\d-\d\d$/.test(value))throw new Error("Choose a valid date.");
  const [year,month,day]=value.split("-").map(Number);
  const start=new Date(year,month-1,day);
  if(dateKey(start)!==value)throw new Error("Choose a valid calendar date.");
  const end=new Date(year,month-1,day+1);
  return {start,end};
}
function availabilityClock(value){
  return new Intl.DateTimeFormat(undefined,{hour:"numeric",minute:"2-digit",timeZoneName:"short"}).format(new Date(value));
}
function availabilitySegments(intervals,start,end){
  const slots=[],lower=start.getTime(),upper=end.getTime();
  let cursor=lower;
  for(const item of intervals){
    const begin=Math.max(lower,Date.parse(item.start_at));
    const finish=Math.min(upper,Date.parse(item.end_at));
    if(!Number.isFinite(begin)||!Number.isFinite(finish)||finish<=begin)continue;
    if(begin>cursor)slots.push({kind:"free",start:cursor,end:begin});
    if(finish>cursor)slots.push({kind:"busy",start:Math.max(begin,cursor),end:finish});
    cursor=Math.max(cursor,finish);
  }
  if(cursor<upper)slots.push({kind:"free",start:cursor,end:upper});
  return slots;
}
function showAvailability(data,start,end){
  const root=$("availability-results");root.replaceChildren();
  const summary=el("p","availability-summary",data.busy.length+
    (data.busy.length===1?" occupied interval":" occupied intervals")+" on this date");
  const list=el("ul","availability-intervals");
  for(const slot of availabilitySegments(data.busy,start,end)){
    const li=el("li","availability-interval "+slot.kind);
    const label=el("strong",null,slot.kind==="busy"?"Busy":"Unscheduled");
    const times=el("span",null,availabilityClock(slot.start)+" – "+availabilityClock(slot.end));
    li.append(label,times);list.append(li);
  }
  root.append(summary,list);
}
$("availability-btn").addEventListener("click",()=>{
  const select=$("availability-calendar");select.replaceChildren();
  for(const calendar of state.calendars){
    const option=el("option",null,calendar.name+" ("+
      (calendar.role==="freebusy"?"free/busy":calendar.role==="read"?"read-only":calendar.role)+")");
    option.value=calendar.id;select.append(option);
  }
  if(!state.calendars.length){toast("No calendars are accessible.");return;}
  select.value=state.calendars.find(c=>!state.hidden.has(c.id))?.id||state.calendars[0].id;
  $("availability-date").value=dateKey(state.anchor);
  $("availability-results").replaceChildren();
  $("availability-dialog").showModal();
});
$("availability-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const cid=$("availability-calendar").value,seq=++availabilityRequest;
  const root=$("availability-results");root.replaceChildren(el("p","muted","Checking availability…"));
  try{
    const {start,end}=availabilityDay($("availability-date").value);
    const query=new URLSearchParams({calendar_id:cid,start:start.toISOString(),end:end.toISOString()});
    const result=await api("/availability?"+query);
    if(seq!==availabilityRequest||!$("availability-dialog").open)return;
    showAvailability(result,start,end);
  }catch(error){
    if(seq===availabilityRequest)root.replaceChildren(el("p","error",error.message));
  }
});
$("search-btn").addEventListener("click",()=>{
  $("search-query").value="";$("search-results").replaceChildren();
  $("search-dialog").showModal();$("search-query").focus();
});
$("search-form").addEventListener("submit",async e=>{
  e.preventDefault();
  const q=$("search-query").value.trim();
  if(q.length<2){toast("Use at least two characters.");return;}
  $("search-results").replaceChildren(el("div","skeleton"));
  try{
    const results=await api("/search?q="+encodeURIComponent(q));
    renderSearch(results);
  }catch(error){$("search-results").replaceChildren(el("p","error",error.message));}
});
$("import-btn").addEventListener("click",()=>$("import-file").click());
$("import-file").addEventListener("change",async ()=>{
  const input=$("import-file"),file=input.files?.[0];input.value="";
  if(!file)return;
  const cid=state.calendars.find(c=>!state.hidden.has(c.id)&&canEdit(c.id))?.id;
  if(!cid){toast("Choose a visible calendar to import into.");return;}
  if(file.size>55000){toast("Import at most 55 KB and 100 events per file.");return;}
  try{
    const result=await api("/import.ics",{method:"POST",body:{calendar_id:cid,ics:await file.text()}});
    await refresh();toast("Imported "+result.imported+" event(s); skipped "+result.skipped+" duplicate(s).");
  }catch(error){toast(error.message);}
});
$("export-btn").addEventListener("click",exportCalendar);
window.addEventListener("online",()=>{if(state.token)refresh();});
start();
