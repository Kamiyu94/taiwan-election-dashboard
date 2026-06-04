#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 detail_candidates.csv 打包成單一、自給自足、可離線開啟的互動儀表板 dashboard.html。
- 內嵌 Chart.js 與全部資料,雙擊即可用瀏覽器開
- 左側勾選:選舉類別 / 年度 / 地區 / 政黨 / 當選與否 / 姓名搜尋(可交叉)
- 主畫面:KPI、各政黨總得票數、各政黨得票佔比趨勢、各政黨當選席次、明細表

用法: python3 build_dashboard.py   → 產出 dashboard.html
"""

import csv
import json

DETAIL_CSV = "detail_candidates.csv"
VENDOR_JS = "vendor/chart.umd.min.js"
OUT = "dashboard.html"


def to_num(s):
    s = (s or "").strip().replace(",", "")
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def load_rows():
    rows = []
    with open(DETAIL_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({
                "y": r["選舉年度"],
                "c": r["選舉類別"],
                "r": r["地區"],
                "n": r["號次"],
                "nm": r["姓名"],
                "sx": r["性別"],
                "b": r["出生年次"],
                "p": r["推薦政黨"] or "未填",
                "v": to_num(r["得票數"]) or 0,
                "vr": to_num(r["得票率"]),
                "w": 1 if r["當選否"].strip().upper() == "Y" else 0,
                "inc": 1 if r["是否現任"].strip().upper() == "Y" else 0,
                "mate": r["副手姓名"],
                "d": r["投票日期"],
            })
    return rows


def main():
    rows = load_rows()
    data_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    with open(VENDOR_JS, encoding="utf-8") as f:
        chartjs = f.read()

    html = TEMPLATE
    html = html.replace("/*__CHARTJS__*/", chartjs)
    html = html.replace("/*__DATA__*/", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[*] 已產出 {OUT}({len(rows)} 筆候選人資料,可直接用瀏覽器開啟)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>歷屆選舉政黨得票 互動儀表板</title>
<style>
  :root{
    --bg:#f4f6f8; --panel:#fff; --ink:#1f2933; --muted:#647387;
    --line:#e3e8 ;--line:#e3e8ee; --accent:#2b6cb0; --shadow:0 1px 3px rgba(0,0,0,.08);
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;
       background:var(--bg);color:var(--ink);font-size:14px}
  header{background:#1a2b45;color:#fff;padding:14px 22px;display:flex;align-items:baseline;gap:14px}
  header h1{font-size:18px;margin:0;font-weight:700}
  header .sub{color:#a9b8d0;font-size:12.5px}
  .layout{display:flex;align-items:flex-start}
  /* 側邊篩選 */
  aside{width:268px;flex:0 0 268px;padding:16px;position:sticky;top:0;max-height:100vh;overflow:auto}
  aside .grp{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;box-shadow:var(--shadow)}
  aside .grp>h3{margin:0;padding:10px 12px;font-size:13px;border-bottom:1px solid var(--line);
                display:flex;justify-content:space-between;align-items:center;cursor:pointer}
  aside .grp .tools{font-size:11px;color:var(--accent);font-weight:400}
  aside .grp .tools a{cursor:pointer;margin-left:8px}
  .opts{max-height:210px;overflow:auto;padding:6px 12px 10px}
  .opt{display:flex;align-items:center;gap:7px;padding:2px 0;font-size:13px;cursor:pointer}
  .opt input{accent-color:var(--accent)}
  .opt .sw{width:9px;height:9px;border-radius:2px;flex:0 0 9px}
  .opt .cnt{margin-left:auto;color:var(--muted);font-size:11px}
  .searchbox{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:7px;font-size:13px}
  .seg{display:flex;border:1px solid var(--line);border-radius:7px;overflow:hidden;margin:8px 12px}
  .seg button{flex:1;border:0;background:#fff;padding:7px 0;cursor:pointer;font-size:12.5px;color:var(--muted)}
  .seg button.on{background:var(--accent);color:#fff}
  .resetbtn{width:calc(100% - 24px);margin:0 12px 4px;padding:8px;border:1px solid var(--line);
            background:#fff;border-radius:7px;cursor:pointer;color:var(--muted)}
  /* 主畫面 */
  main{flex:1;padding:16px 20px 40px;min-width:0}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow)}
  .kpi .v{font-size:25px;font-weight:700;letter-spacing:.5px}
  .kpi .l{color:var(--muted);font-size:12.5px;margin-top:2px}
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow);min-width:0}
  .card h2{font-size:14px;margin:0 0 10px}
  .card.full{grid-column:1 / -1}
  .chartwrap{position:relative;height:300px}
  .chartwrap.tall{height:360px}
  table{width:100%;border-collapse:collapse;font-size:12.5px}
  th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
  th{position:sticky;top:0;background:#f0f3f7;cursor:pointer;user-select:none}
  th.sorted::after{content:" \25Be";color:var(--accent)}
  th.sorted.asc::after{content:" \25B4"}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  .chip{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:11px}
  .win{color:#1b9431;font-weight:700}
  .tablewrap{max-height:520px;overflow:auto}
  .muted{color:var(--muted)}
  .tabletools{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .pill{background:#eef2f7;border-radius:20px;padding:3px 10px;font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>歷屆選舉 · 政黨得票互動儀表板</h1>
  <span class="sub">資料來源:政大選舉研究中心 · 行政首長類選舉(總統/省市長/縣市長)候選人得票</span>
</header>

<div class="layout">
  <aside id="filters">
    <input class="searchbox" id="nameSearch" placeholder="🔍 搜尋候選人姓名…" style="margin-bottom:12px">
    <button class="resetbtn" id="resetBtn">↺ 清除所有篩選</button>
    <div class="grp" data-key="c"><h3>選舉類別 <span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3><div class="opts"></div></div>
    <div class="grp" data-key="y"><h3>年度 <span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3><div class="opts"></div></div>
    <div class="grp" data-key="p"><h3>政黨 <span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3><div class="opts"></div></div>
    <div class="grp" data-key="r"><h3>地區 <span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3><div class="opts"></div></div>
    <div class="grp" data-key="w"><h3>當選與否</h3>
      <div class="seg" id="winSeg"><button data-w="all" class="on">全部</button><button data-w="1">僅當選</button><button data-w="0">僅落選</button></div>
    </div>
  </aside>

  <main>
    <div class="kpis">
      <div class="kpi"><div class="v" id="kRaces">–</div><div class="l">場次(選舉×類別)</div></div>
      <div class="kpi"><div class="v" id="kCand">–</div><div class="l">候選人(組)數</div></div>
      <div class="kpi"><div class="v" id="kVotes">–</div><div class="l">總得票數</div></div>
      <div class="kpi"><div class="v" id="kWin">–</div><div class="l">當選席次</div></div>
    </div>

    <div class="cards">
      <div class="card"><h2>各政黨總得票數</h2><div class="chartwrap"><canvas id="chVotes"></canvas></div></div>
      <div class="card"><h2>各政黨當選席次</h2><div class="chartwrap"><canvas id="chSeats"></canvas></div></div>
      <div class="card full"><h2>各政黨得票佔比趨勢(該黨得票 ÷ 當期全部得票)</h2><div class="chartwrap tall"><canvas id="chTrend"></canvas></div></div>
      <div class="card full">
        <div class="tabletools">
          <h2 style="margin:0">候選人明細</h2>
          <span class="pill" id="rowCount"></span>
        </div>
        <div class="tablewrap">
          <table id="tbl"><thead></thead><tbody></tbody></table>
        </div>
      </div>
    </div>
  </main>
</div>

<script>/*__CHARTJS__*/</script>
<script>
const DATA = /*__DATA__*/;

// ---- 政黨配色 ----
const PARTY_COLORS = {
  "中國國民黨":"#1f4e9c","民主進步黨":"#1b9431","無黨籍及未經政黨推薦":"#9aa0a6",
  "親民黨":"#f7841f","新黨":"#f5c400","台灣民眾黨":"#28c8c8","台灣團結聯盟":"#b53f97",
  "時代力量":"#ffb000","建國黨":"#2bbf6a","綠黨":"#7cb342","新國民黨連線":"#5b8def",
  "未填":"#c0c7d0","其他":"#cbd2da"
};
function hashColor(s){let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))&0xffffff;
  return "hsl("+(h%360)+",55%,55%)";}
function pColor(p){return PARTY_COLORS[p]||hashColor(p);}

// ---- 篩選狀態 ----
const DIMS=["c","y","p","r"];
const LABELS={c:"選舉類別",y:"年度",p:"政黨",r:"地區"};
const state={c:new Set(),y:new Set(),p:new Set(),r:new Set(),w:"all",q:""};

function distinct(key){return [...new Set(DATA.map(d=>d[key]))];}
function sortVals(key,vals){
  if(key==="y")return vals.sort();
  // 政黨/類別/地區:依資料量多寡排序,常用的在前
  const cnt={};DATA.forEach(d=>cnt[d[key]]=(cnt[d[key]]||0)+1);
  return vals.sort((a,b)=>cnt[b]-cnt[a]);
}

// 建立勾選清單(預設全選)
function buildFilters(){
  DIMS.forEach(key=>{
    const vals=sortVals(key,distinct(key));
    vals.forEach(v=>state[key].add(v));
    const box=document.querySelector('.grp[data-key="'+key+'"] .opts');
    const cnt={};DATA.forEach(d=>cnt[d[key]]=(cnt[d[key]]||0)+1);
    box.innerHTML=vals.map(v=>{
      const sw=(key==="p")?'<span class="sw" style="background:'+pColor(v)+'"></span>':'';
      return '<label class="opt"><input type="checkbox" data-key="'+key+'" value="'+encodeURIComponent(v)+'" checked>'
        +sw+'<span>'+v+'</span><span class="cnt">'+cnt[v]+'</span></label>';
    }).join("");
  });
  document.querySelectorAll('.opt input').forEach(cb=>cb.addEventListener("change",e=>{
    const k=e.target.dataset.key,v=decodeURIComponent(e.target.value);
    if(e.target.checked)state[k].add(v);else state[k].delete(v);
    render();
  }));
  document.querySelectorAll('.grp .tools a').forEach(a=>a.addEventListener("click",e=>{
    const grp=e.target.closest('.grp'),key=grp.dataset.key,all="all" in e.target.dataset;
    grp.querySelectorAll('.opt input').forEach(cb=>{cb.checked=all;
      const v=decodeURIComponent(cb.value);if(all)state[key].add(v);else state[key].delete(v);});
    render();
  }));
  document.querySelectorAll('#winSeg button').forEach(b=>b.addEventListener("click",e=>{
    document.querySelectorAll('#winSeg button').forEach(x=>x.classList.remove("on"));
    e.target.classList.add("on");state.w=e.target.dataset.w;render();
  }));
  document.getElementById("nameSearch").addEventListener("input",e=>{state.q=e.target.value.trim();render();});
  document.getElementById("resetBtn").addEventListener("click",()=>{
    DIMS.forEach(k=>{distinct(k).forEach(v=>state[k].add(v));});
    state.w="all";state.q="";
    document.querySelectorAll('.opt input').forEach(cb=>cb.checked=true);
    document.querySelectorAll('#winSeg button').forEach((b,i)=>b.classList.toggle("on",i===0));
    document.getElementById("nameSearch").value="";render();
  });
}

function filtered(){
  return DATA.filter(d=>
    state.c.has(d.c)&&state.y.has(d.y)&&state.p.has(d.p)&&state.r.has(d.r)
    &&(state.w==="all"||String(d.w)===state.w)
    &&(state.q===""||(d.nm&&d.nm.includes(state.q))||(d.mate&&d.mate.includes(state.q)))
  );
}

const fmt=n=>n.toLocaleString("en-US");
let charts={};

function aggParty(rows){
  const m={};
  rows.forEach(d=>{m[d.p]=m[d.p]||{votes:0,seats:0};m[d.p].votes+=d.v;m[d.p].seats+=d.w;});
  return Object.entries(m).map(([p,o])=>({p,...o})).sort((a,b)=>b.votes-a.votes);
}
// 圖表只顯示前 N 黨,其餘併「其他」
function topN(arr,n,valkey){
  if(arr.length<=n)return arr;
  const top=arr.slice(0,n),rest=arr.slice(n);
  const other={p:"其他",votes:0,seats:0};
  rest.forEach(o=>{other.votes+=o.votes;other.seats+=o.seats;});
  return [...top,other];
}

function drawBar(id,labels,vals,colors,axis){
  if(charts[id])charts[id].destroy();
  charts[id]=new Chart(document.getElementById(id),{
    type:"bar",
    data:{labels,datasets:[{data:vals,backgroundColor:colors,borderRadius:4}]},
    options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+fmt(c.parsed.x)+(axis||"")}}},
      scales:{x:{ticks:{callback:v=>v>=10000?(v/10000)+"萬":v}}}}
  });
}

function render(){
  const rows=filtered();
  // KPI
  document.getElementById("kRaces").textContent=new Set(rows.map(d=>d.y+"|"+d.c)).size;
  document.getElementById("kCand").textContent=fmt(rows.length);
  const tot=rows.reduce((s,d)=>s+d.v,0);
  document.getElementById("kVotes").textContent=fmt(tot);
  document.getElementById("kWin").textContent=fmt(rows.reduce((s,d)=>s+d.w,0));

  // 各政黨總得票
  const agg=aggParty(rows), aggV=topN(agg,12);
  drawBar("chVotes",aggV.map(o=>o.p),aggV.map(o=>o.votes),aggV.map(o=>pColor(o.p)),"");
  // 各政黨席次
  const aggS=[...agg].filter(o=>o.seats>0).sort((a,b)=>b.seats-a.seats);
  const aggS2=topN(aggS,12);
  drawBar("chSeats",aggS2.map(o=>o.p),aggS2.map(o=>o.seats),aggS2.map(o=>pColor(o.p))," 席");

  drawTrend(rows,agg);
  drawTable(rows);
}

// 得票佔比趨勢:x=年度,series=前 6 黨,y= 該黨當年得票 / 當年全部得票
function drawTrend(rows,agg){
  const years=[...new Set(rows.map(d=>d.y))].sort();
  const topParties=agg.slice(0,6).map(o=>o.p);
  const totByYear={};years.forEach(y=>totByYear[y]=0);
  rows.forEach(d=>{totByYear[d.y]+=d.v;});
  const ds=topParties.map(p=>{
    const byYear={};years.forEach(y=>byYear[y]=0);
    rows.filter(d=>d.p===p).forEach(d=>byYear[d.y]+=d.v);
    return {label:p,borderColor:pColor(p),backgroundColor:pColor(p),tension:.25,spanGaps:true,
      data:years.map(y=>totByYear[y]?+(byYear[y]/totByYear[y]*100).toFixed(2):null)};
  });
  if(charts.chTrend)charts.chTrend.destroy();
  charts.chTrend=new Chart(document.getElementById("chTrend"),{
    type:"line",data:{labels:years,datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:c=>" "+c.dataset.label+": "+(c.parsed.y==null?"—":c.parsed.y+"%")}}},
      scales:{y:{title:{display:true,text:"得票佔比 %"},ticks:{callback:v=>v+"%"}}}}
  });
}

// ---- 明細表(可排序)----
const COLS=[
  {k:"y",t:"年度"},{k:"c",t:"類別"},{k:"r",t:"地區"},{k:"n",t:"號次",num:1},
  {k:"nm",t:"姓名"},{k:"p",t:"推薦政黨"},{k:"v",t:"得票數",num:1},
  {k:"vr",t:"得票率%",num:1},{k:"w",t:"當選"},{k:"inc",t:"現任"}
];
let sortKey="v",sortAsc=false;
function drawTable(rows){
  const thead=document.querySelector("#tbl thead");
  thead.innerHTML="<tr>"+COLS.map(c=>'<th data-k="'+c.k+'" class="'+(c.num?"num ":"")
    +(c.k===sortKey?"sorted "+(sortAsc?"asc":""):"")+'">'+c.t+'</th>').join("")+"</tr>";
  thead.querySelectorAll("th").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k;if(k===sortKey)sortAsc=!sortAsc;else{sortKey=k;sortAsc=false;}drawTable(filtered());});
  const sorted=[...rows].sort((a,b)=>{
    let x=a[sortKey],y=b[sortKey];
    if(typeof x==="number"||typeof y==="number"){x=x??-Infinity;y=y??-Infinity;return sortAsc?x-y:y-x;}
    x=x||"";y=y||"";return sortAsc?(""+x).localeCompare(y):(""+y).localeCompare(x);});
  const tbody=document.querySelector("#tbl tbody");
  const MAX=600;
  tbody.innerHTML=sorted.slice(0,MAX).map(d=>{
    const nm=d.nm+(d.mate?'<span class="muted"> / '+d.mate+'</span>':'');
    return "<tr>"+
      "<td>"+d.y+"</td><td>"+d.c+"</td><td>"+d.r+"</td><td class='num'>"+d.n+"</td>"+
      "<td>"+nm+"</td>"+
      '<td><span class="chip" style="background:'+pColor(d.p)+'">'+d.p+"</span></td>"+
      "<td class='num'>"+fmt(d.v)+"</td>"+
      "<td class='num'>"+(d.vr==null?"—":d.vr)+"</td>"+
      '<td class="'+(d.w?"win":"")+'">'+(d.w?"★當選":"")+"</td>"+
      "<td>"+(d.inc?"現任":"")+"</td></tr>";
  }).join("");
  document.getElementById("rowCount").textContent=
    rows.length+" 筆"+(rows.length>MAX?"(表格顯示前 "+MAX+" 筆,圖表/KPI 為全部)":"");
}

buildFilters();
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
