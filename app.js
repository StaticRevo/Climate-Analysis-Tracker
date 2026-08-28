const $ = id => document.getElementById(id);
let currentRows = [];
let stationCatalog = {};
const fmt = (n, digits=1) => n == null || Number.isNaN(n) ? "—" : Number(n).toFixed(digits);
if (localStorage.getItem("weather-atlas-theme") === "dark") document.body.classList.add("dark");
function stationId(){const value=$("station").value.trim();const match=Object.entries(stationCatalog).find(([,station])=>station.name===value);return match?match[0]:value}
function renderStationOptions(query=""){const list=$("station-list"), matches=Object.entries(stationCatalog).filter(([,station])=>station.name.toLowerCase().includes(query.trim().toLowerCase())).sort(([,a],[,b])=>a.name.localeCompare(b.name));list.innerHTML="";if(!matches.length){list.innerHTML='<div class="station-empty">No matching cities</div>';return}matches.forEach(([id,station])=>{const option=document.createElement("button");option.type="button";option.className="station-option";option.role="option";option.textContent=station.name;option.dataset.stationId=id;option.onclick=()=>{ $("station").value=station.name;closeStationList();loadData() };list.appendChild(option)})}
function closeStationList(){$("station-list").classList.remove("open");$("station").setAttribute("aria-expanded","false")}
function setupStationPicker(){const input=$("station");renderStationOptions();input.onfocus=()=>{$("station-list").classList.add("open");input.setAttribute("aria-expanded","true");renderStationOptions(input.value)};input.oninput=()=>{$("station-list").classList.add("open");input.setAttribute("aria-expanded","true");renderStationOptions(input.value)};input.onkeydown=e=>{if(e.key==="Enter"){e.preventDefault();const first=$("station-list").querySelector(".station-option");if(first)first.click()}if(e.key==="Escape")closeStationList()};document.addEventListener("click",e=>{if(!e.target.closest(".station-picker"))closeStationList()})}
async function loadStations(){try{stationCatalog=await (await fetch("api/stations")).json()}catch(e){stationCatalog=await staticStations()}setupStationPicker()}
function setStatus(text, error=false){$("status").textContent=text;$("status").style.color=error?"#c65331":""}
function dateRange(years){const end=new Date(); if(years===40)return ["1980-01-01",end.toISOString().slice(0,10)]; const start=new Date(end); start.setFullYear(end.getFullYear()-years); return [start.toISOString().slice(0,10),end.toISOString().slice(0,10)]}
async function loadData(){
  const start=$("start").value,end=$("end").value;
  if(!start||!end||end<start){setStatus("Choose a valid date range.",true);return}
  setStatus("Loading observations…");
  const span=(new Date(end)-new Date(start))/86400000;
  const granularity=span>3650?"monthly":"daily";
  try{
    const res=await fetch(`api/weather?station=${encodeURIComponent(stationId())}&start=${start}&end=${end}&granularity=${granularity}`);
    if(!res.ok)throw new Error("API unavailable");
    const payload=await res.json(); currentRows=payload.data.filter(d=>d.temp!=null||d.prcp!=null);
    render(payload, start, end);
    setStatus(`${currentRows.length.toLocaleString()} observations · ${payload.fallback?"Showing representative demo data (Meteostat unavailable)":"Meteostat observations loaded"}`);
  }catch(e){currentRows=staticWeather(start,end,granularity);render({station:stationCatalog[stationId()]||STATIC_STATIONS["16597"],fallback:true},start,end);setStatus(`${currentRows.length.toLocaleString()} demo observations · Live API unavailable`)}
}
function render(payload,start,end){
  const rows=currentRows, temps=rows.map(r=>r.temp).filter(Number.isFinite), rain=rows.map(r=>r.prcp).filter(Number.isFinite);
  const avg=temps.reduce((a,b)=>a+b,0)/(temps.length||1), total=rain.reduce((a,b)=>a+b,0), hot=rows.reduce((a,b)=>a.temp>b.temp?a:b,rows[0]||{});
  $("avgTemp").textContent=fmt(avg)+"°"; $("totalRain").textContent=fmt(total,0);
  $("warmest").textContent=fmt(hot.temp)+"°"; $("warmestDate").textContent=hot.date||"Highest observed temperature";
  const yearly={}; rows.forEach(r=>{const y=r.date.slice(0,4);(yearly[y]??=[]).push(r.temp)});
  const years=Object.keys(yearly).sort(); const first=yearly[years[0]]?.filter(Number.isFinite),last=yearly[years.at(-1)]?.filter(Number.isFinite);
  const change=(last?.reduce((a,b)=>a+b,0)/(last?.length||1))-(first?.reduce((a,b)=>a+b,0)/(first?.length||1));
  $("change").textContent=(change>=0?"+":"")+fmt(change)+"°"; $("rangeLabel").textContent=`${start} — ${end} · ${payload.station.name}`;
  $("insightText").textContent=change>=0?`Average temperature is ${fmt(change)}°C warmer in ${years.at(-1)} than in ${years[0]}. The warmest reading reached ${fmt(hot.temp)}°C.`:`Average temperature is ${fmt(Math.abs(change))}°C cooler in ${years.at(-1)} than in ${years[0]}.`;
  drawChart(rows);
}
function drawChart(rows){
  const svg=$("chart"), W=1000,H=360,p={l:48,r:20,t:18,b:40}, vals=rows.map(r=>r.temp).filter(Number.isFinite);
  if(!vals.length){svg.innerHTML="";return} const min=Math.floor(Math.min(...vals)-2),max=Math.ceil(Math.max(...vals)+2), x=i=>p.l+i/(rows.length-1||1)*(W-p.l-p.r), y=v=>p.t+(max-v)/(max-min)*(H-p.t-p.b);
  let out=`<defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#f06d38" stop-opacity=".25"/><stop offset="1" stop-color="#f06d38" stop-opacity="0"/></linearGradient></defs>`;
  for(let i=0;i<5;i++){const v=min+(max-min)*i/4, yy=y(v);out+=`<line class="gridline" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text class="axis" x="0" y="${yy+4}">${v}°</text>`}
  const pts=rows.map((r,i)=>Number.isFinite(r.temp)?`${x(i)},${y(r.temp)}`:null).filter(Boolean);
  out+=`<path class="area" d="M ${pts[0]} L ${pts.join(" L ")} L ${x(rows.length-1)},${H-p.b} L ${p.l},${H-p.b} Z"/><polyline class="line" points="${pts.join(" ")}"/>`;
  [0,.25,.5,.75,1].forEach(t=>{const i=Math.min(rows.length-1,Math.floor(t*(rows.length-1)));out+=`<text class="axis" text-anchor="${t===0?"start":t===1?"end":"middle"}" x="${x(i)}" y="${H-10}">${rows[i].date.slice(0,7)}</text>`}); svg.innerHTML=out;
}
document.querySelectorAll("[data-range]").forEach(b=>b.onclick=()=>{const [s,e]=dateRange(+b.dataset.range);$("start").value=s;$("end").value=e;document.querySelectorAll("[data-range]").forEach(x=>x.classList.remove("active"));b.classList.add("active");loadData()});
$("load").onclick=loadData; $("station").onchange=loadData; $("themeToggle").onclick=()=>{document.body.classList.toggle("dark");localStorage.setItem("weather-atlas-theme",document.body.classList.contains("dark")?"dark":"light")};
loadStations().then(loadData);
