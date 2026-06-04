#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包成單一、可離線的互動儀表板 dashboard.html(漸進式級聯篩選版)。

資料來源(統一為候選人逐筆 + 不分區政黨兩層):
  - detail_candidates.csv  NCCU 行政首長(總統/省長/直轄市長/縣市長)
  - cec_candidates.csv     CEC 立委/議員(區域 + 原住民)
  - cec_partylist.csv      CEC 立委不分區政黨票

UX:左側採「選舉類別 → 年度 → 地區 → 政黨」級聯篩選,
   先縮小範圍才列出地區/政黨,避免議員/里長細分到每個里時爆炸。

用法: python3 build_dashboard.py
"""

import csv
import json

VENDOR_JS = "vendor/chart.umd.min.js"
OUT = "dashboard.html"


def to_num(s):
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return None


def norm_exec(cat):
    if "總統" in cat:
        return "總統"
    if "省長" in cat:
        return "省長"
    if "市長" in cat:
        return "直轄市長"
    if "縣" in cat and "長" in cat:
        return "縣市長"
    return cat


def load_candidates():
    rows = []
    # NCCU 行政首長
    try:
        with open("detail_candidates.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "y": r["選舉年度"], "cat": norm_exec(r["選舉類別"]),
                    "region": r["地區"], "dist": "",
                    "nm": r["姓名"] + ("/" + r["副手姓名"] if r.get("副手姓名") else ""),
                    "p": r["推薦政黨"] or "未填",
                    "v": to_num(r["得票數"]) or 0, "vr": to_num(r["得票率"]),
                    "w": 1 if r["當選否"].strip().upper() == "Y" else 0,
                })
    except FileNotFoundError:
        pass
    # CEC 立委/議員(區域+原住民)
    CECMAP = {
        ("立委", "區域"): "立法委員(區域)",
        ("立委", "山地原住民"): "立法委員(原住民)",
        ("立委", "平地原住民"): "立法委員(原住民)",
        ("立委", "原住民"): "立法委員(原住民)",
        ("議員", "區域"): "地方議員(區域)",
        ("議員", "山地原住民"): "地方議員(原住民)",
        ("議員", "平地原住民"): "地方議員(原住民)",
        ("議員", "原住民"): "地方議員(原住民)",
    }
    try:
        with open("cec_candidates.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cat = CECMAP.get((r["選舉類別"], r["層級"]), r["選舉類別"])
                rows.append({
                    "y": r["選舉年度"], "cat": cat,
                    "region": r["縣市"], "dist": r["選區"],
                    "nm": r["姓名"], "p": r["政黨"] or "未填",
                    "v": to_num(r["得票數"]) or 0, "vr": to_num(r["得票率"]),
                    "w": 1 if r["當選"].strip().upper() == "Y" else 0,
                })
    except FileNotFoundError:
        pass
    return rows


def load_partylist():
    rows = []
    try:
        with open("cec_partylist.csv", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "y": r["選舉年度"], "cat": "立法委員(不分區政黨)",
                    "p": r["政黨"] or "未填",
                    "v": to_num(r["得票數"]) or 0, "vr": to_num(r["得票率"]),
                    "seats": to_num(r["當選席次"]) or 0,
                })
    except FileNotFoundError:
        pass
    return rows


# 類別顯示順序
CAT_ORDER = [
    "總統", "立法委員(區域)", "立法委員(原住民)", "立法委員(不分區政黨)",
    "直轄市長", "縣市長", "地方議員(區域)", "地方議員(原住民)", "省長",
]


def main():
    cand = load_candidates()
    party = load_partylist()
    cats = sorted({r["cat"] for r in cand} | {r["cat"] for r in party},
                  key=lambda c: (CAT_ORDER.index(c) if c in CAT_ORDER else 99, c))

    with open(VENDOR_JS, encoding="utf-8") as f:
        chartjs = f.read()

    html = TEMPLATE
    html = html.replace("/*__CHARTJS__*/", chartjs)
    html = html.replace("/*__CAND__*/", json.dumps(cand, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__PARTY__*/", json.dumps(party, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__CATS__*/", json.dumps(cats, ensure_ascii=False))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[*] 已產出 {OUT}:候選人 {len(cand)} 筆、不分區政黨 {len(party)} 筆、類別 {len(cats)} 種")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台灣歷屆選舉 · 政黨得票互動儀表板</title>
<style>
  :root{--bg:#f4f6f8;--panel:#fff;--ink:#1f2933;--muted:#647387;--line:#e3e8ee;--accent:#2b6cb0;--shadow:0 1px 3px rgba(0,0,0,.08)}
  *{box-sizing:border-box}
  body{margin:0;font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;background:var(--bg);color:var(--ink);font-size:14px}
  header{background:#1a2b45;color:#fff;padding:14px 22px}
  header h1{font-size:18px;margin:0;font-weight:700}
  header .sub{color:#a9b8d0;font-size:12.5px}
  .layout{display:flex;align-items:flex-start}
  aside{width:280px;flex:0 0 280px;padding:16px;position:sticky;top:0;max-height:100vh;overflow:auto}
  .step{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;box-shadow:var(--shadow)}
  .step>h3{margin:0;padding:10px 12px;font-size:13px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
  .step .num{display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;background:var(--accent);color:#fff;border-radius:50%;font-size:11px;margin-right:6px}
  .step .tools{font-size:11px;color:var(--accent);font-weight:400}
  .step .tools a{cursor:pointer;margin-left:8px}
  .body{padding:8px 12px 12px}
  .opts{max-height:230px;overflow:auto}
  .opt{display:flex;align-items:center;gap:7px;padding:2px 0;font-size:13px;cursor:pointer}
  .opt input{accent-color:var(--accent)}
  .opt .sw{width:9px;height:9px;border-radius:2px;flex:0 0 9px}
  .opt .cnt{margin-left:auto;color:var(--muted);font-size:11px}
  select.catsel{width:100%;padding:8px;border:1px solid var(--line);border-radius:7px;font-size:14px;background:#fff}
  .searchbox{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:7px;font-size:13px}
  .seg{display:flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
  .seg button{flex:1;border:0;background:#fff;padding:7px 0;cursor:pointer;font-size:12.5px;color:var(--muted)}
  .seg button.on{background:var(--accent);color:#fff}
  .hint{color:var(--muted);font-size:11.5px;padding:2px 2px 0}
  main{flex:1;padding:16px 20px 40px;min-width:0}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}
  .kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow)}
  .kpi .v{font-size:24px;font-weight:700}
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
  th.sorted::after{content:" \25BE";color:var(--accent)}
  th.sorted.asc::after{content:" \25B4"}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  .chip{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:11px}
  .win{color:#1b9431;font-weight:700}
  .tablewrap{max-height:520px;overflow:auto}
  .muted{color:var(--muted)}
  .tabletools{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
  .pill{background:#eef2f7;border-radius:20px;padding:3px 10px;font-size:12px;color:var(--muted)}
  .crumbs{margin-bottom:12px;font-size:13px;color:var(--muted)}
  .crumbs b{color:var(--ink)}
</style>
</head>
<body>
<header>
  <h1>台灣歷屆選舉 · 政黨得票互動儀表板</h1>
  <span class="sub">資料來源:中選會選舉資料庫(立委/議員)· 政大選研中心(總統/縣市長)</span>
</header>

<div class="layout">
  <aside>
    <div class="step">
      <h3><span><span class="num">1</span>選舉類別</span></h3>
      <div class="body"><select class="catsel" id="catSel"></select>
      <div class="hint">先選類別,再選年度與地區</div></div>
    </div>
    <div class="step">
      <h3><span><span class="num">2</span>年度</span><span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3>
      <div class="body"><div class="opts" id="yearOpts"></div></div>
    </div>
    <div class="step" id="regionStep">
      <h3><span><span class="num">3</span>地區</span><span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3>
      <div class="body"><div class="opts" id="regionOpts"></div></div>
    </div>
    <div class="step">
      <h3><span><span class="num">4</span>政黨</span><span class="tools"><a data-all>全選</a><a data-none>清除</a></span></h3>
      <div class="body"><div class="opts" id="partyOpts"></div></div>
    </div>
    <div class="step" id="candStep">
      <h3><span>候選人</span></h3>
      <div class="body">
        <input class="searchbox" id="nameSearch" placeholder="🔍 搜尋姓名…" style="margin-bottom:8px">
        <div class="seg" id="winSeg"><button data-w="all" class="on">全部</button><button data-w="1">僅當選</button><button data-w="0">僅落選</button></div>
      </div>
    </div>
  </aside>

  <main>
    <div class="crumbs" id="crumbs"></div>
    <div class="kpis">
      <div class="kpi"><div class="v" id="kRaces">–</div><div class="l">場次(年度×地區)</div></div>
      <div class="kpi"><div class="v" id="kCand">–</div><div class="l" id="kCandL">候選人數</div></div>
      <div class="kpi"><div class="v" id="kVotes">–</div><div class="l">總得票數</div></div>
      <div class="kpi"><div class="v" id="kWin">–</div><div class="l">當選席次</div></div>
    </div>
    <div class="cards">
      <div class="card"><h2>各政黨總得票數</h2><div class="chartwrap"><canvas id="chVotes"></canvas></div></div>
      <div class="card"><h2 id="seatTitle">各政黨當選席次</h2><div class="chartwrap"><canvas id="chSeats"></canvas></div></div>
      <div class="card full"><h2>各政黨得票佔比趨勢(該黨得票 ÷ 當期全部得票)</h2><div class="chartwrap tall"><canvas id="chTrend"></canvas></div></div>
      <div class="card full">
        <div class="tabletools"><h2 style="margin:0" id="tblTitle">明細</h2><span class="pill" id="rowCount"></span></div>
        <div class="tablewrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
      </div>
    </div>
  </main>
</div>

<script>/*__CHARTJS__*/</script>
<script>
const CAND = /*__CAND__*/;
const PARTY = /*__PARTY__*/;
const CATS = /*__CATS__*/;

const PARTY_COLORS = {
  "中國國民黨":"#1f4e9c","民主進步黨":"#1b9431","無黨籍及未經政黨推薦":"#9aa0a6","未填":"#c0c7d0",
  "親民黨":"#f7841f","新黨":"#f5c400","台灣民眾黨":"#28c8c8","台灣團結聯盟":"#b53f97",
  "時代力量":"#ffb000","建國黨":"#2bbf6a","綠黨":"#7cb342","台灣基進":"#a3251d","其他":"#cbd2da"
};
function hashColor(s){let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))&0xffffff;return "hsl("+(h%360)+",55%,55%)";}
function pColor(p){return PARTY_COLORS[p]||hashColor(p);}
const fmt=n=>(n==null?"":n.toLocaleString("en-US"));

function isPartyCat(cat){return cat.indexOf("不分區")>=0;}

const state={cat:CATS[0],years:new Set(),regions:new Set(),parties:new Set(),q:"",win:"all"};
let charts={};

function baseRows(){
  const src=isPartyCat(state.cat)?PARTY:CAND;
  return src.filter(d=>d.cat===state.cat);
}
function distinct(rows,key){return [...new Set(rows.map(d=>d[key]).filter(x=>x!==undefined&&x!==""))];}
function countBy(rows,key){const m={};rows.forEach(d=>{const k=d[key];if(k!==undefined&&k!=="")m[k]=(m[k]||0)+1;});return m;}

// ---- 級聯:類別 → 年度 → 地區 → 政黨 ----
function onCatChange(){
  const rows=baseRows();
  state.years=new Set(distinct(rows,"y"));
  rebuildYears();
  resetRegions(); resetParties();
  render();
}
function resetRegions(){
  const rows=baseRows().filter(d=>state.years.has(d.y));
  state.regions=new Set(distinct(rows,"region"));
  rebuildRegions();
}
function resetParties(){
  let rows=baseRows().filter(d=>state.years.has(d.y));
  if(!isPartyCat(state.cat)) rows=rows.filter(d=>state.regions.has(d.region)||!d.region);
  state.parties=new Set(distinct(rows,"p"));
  rebuildParties();
}

function chkList(elId,values,counts,selset,key,withColor){
  const el=document.getElementById(elId);
  if(!values.length){el.innerHTML='<div class="hint">(無)</div>';return;}
  el.innerHTML=values.map(v=>{
    const sw=withColor?'<span class="sw" style="background:'+pColor(v)+'"></span>':'';
    return '<label class="opt"><input type="checkbox" value="'+encodeURIComponent(v)+'" '+(selset.has(v)?"checked":"")+'>'
      +sw+'<span>'+v+'</span><span class="cnt">'+(counts[v]||0)+'</span></label>';
  }).join("");
  el.querySelectorAll('input').forEach(cb=>cb.onchange=e=>{
    const v=decodeURIComponent(e.target.value);
    if(e.target.checked)selset.add(v);else selset.delete(v);
    if(key==="y"){resetRegions();resetParties();}
    else if(key==="region"){resetParties();}
    render();
  });
}
function rebuildYears(){
  const rows=baseRows();
  chkList("yearOpts",distinct(rows,"y").sort(),countBy(rows,"y"),state.years,"y",false);
}
function rebuildRegions(){
  document.getElementById("regionStep").style.display=isPartyCat(state.cat)?"none":"";
  if(isPartyCat(state.cat))return;
  const rows=baseRows().filter(d=>state.years.has(d.y));
  const cnt=countBy(rows,"region");
  const vals=distinct(rows,"region").sort((a,b)=>(cnt[b]-cnt[a]));
  chkList("regionOpts",vals,cnt,state.regions,"region",false);
}
function rebuildParties(){
  let rows=baseRows().filter(d=>state.years.has(d.y));
  if(!isPartyCat(state.cat)) rows=rows.filter(d=>state.regions.has(d.region)||!d.region);
  const cnt=countBy(rows,"p");
  const vals=distinct(rows,"p").sort((a,b)=>(cnt[b]-cnt[a]));
  chkList("partyOpts",vals,cnt,state.parties,"p",true);
}

// 全選/清除
document.querySelectorAll('.step .tools').forEach(t=>{
  t.querySelectorAll('a').forEach(a=>a.onclick=e=>{
    const all="all" in e.target.dataset;
    const step=e.target.closest('.step');
    const opts=step.querySelector('.opts');
    const id=opts.id;
    let key=id==="yearOpts"?"y":id==="regionOpts"?"region":"p";
    const set=key==="y"?state.years:key==="region"?state.regions:state.parties;
    opts.querySelectorAll('input').forEach(cb=>{const v=decodeURIComponent(cb.value);cb.checked=all;if(all)set.add(v);else set.delete(v);});
    if(key==="y"){resetRegions();resetParties();}
    else if(key==="region"){resetParties();}
    render();
  });
});

// ---- 主篩選 ----
function filtered(){
  let rows=baseRows().filter(d=>state.years.has(d.y));
  if(isPartyCat(state.cat)){
    rows=rows.filter(d=>state.parties.has(d.p));
    return rows;
  }
  rows=rows.filter(d=>(d.region===""||state.regions.has(d.region))&&state.parties.has(d.p));
  if(state.win!=="all")rows=rows.filter(d=>String(d.w)===state.win);
  if(state.q)rows=rows.filter(d=>d.nm&&d.nm.includes(state.q));
  return rows;
}

function aggParty(rows,party){
  const m={};
  rows.forEach(d=>{m[d.p]=m[d.p]||{votes:0,seats:0};m[d.p].votes+=d.v;m[d.p].seats+=(party?(d.seats||0):d.w);});
  return Object.entries(m).map(([p,o])=>({p,...o})).sort((a,b)=>b.votes-a.votes);
}
function topN(arr,n){if(arr.length<=n)return arr;const t=arr.slice(0,n);const o={p:"其他",votes:0,seats:0};arr.slice(n).forEach(x=>{o.votes+=x.votes;o.seats+=x.seats;});return [...t,o];}

function drawBar(id,labels,vals,colors,suffix){
  if(charts[id])charts[id].destroy();
  charts[id]=new Chart(document.getElementById(id),{type:"bar",
    data:{labels,datasets:[{data:vals,backgroundColor:colors,borderRadius:4}]},
    options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+fmt(c.parsed.x)+(suffix||"")}}},
      scales:{x:{ticks:{callback:v=>v>=10000?(v/10000)+"萬":v}}}}});
}

function render(){
  const party=isPartyCat(state.cat);
  const rows=filtered();
  // 麵包屑
  const yrs=[...state.years].sort();
  document.getElementById("crumbs").innerHTML=
    "<b>"+state.cat+"</b> ／ 年度 "+(yrs.length?yrs[0]+(yrs.length>1?"–"+yrs[yrs.length-1]:""):"—")
    +(party?"":" ／ 地區 "+(state.regions.size)+" 個");
  // KPI
  document.getElementById("kRaces").textContent=party?yrs.length:new Set(rows.map(d=>d.y+"|"+d.region)).size;
  document.getElementById("kCandL").textContent=party?"政黨數":"候選人數";
  document.getElementById("kCand").textContent=party?new Set(rows.map(d=>d.p)).size:fmt(rows.length);
  document.getElementById("kVotes").textContent=fmt(rows.reduce((s,d)=>s+d.v,0));
  document.getElementById("kWin").textContent=fmt(rows.reduce((s,d)=>s+(party?(d.seats||0):d.w),0));

  const agg=aggParty(rows,party), aggV=topN(agg,12);
  drawBar("chVotes",aggV.map(o=>o.p),aggV.map(o=>o.votes),aggV.map(o=>pColor(o.p)),"");
  document.getElementById("seatTitle").textContent=party?"各政黨當選席次(不分區)":"各政黨當選席次";
  const aggS=topN(agg.filter(o=>o.seats>0).sort((a,b)=>b.seats-a.seats),12);
  drawBar("chSeats",aggS.map(o=>o.p),aggS.map(o=>o.seats),aggS.map(o=>pColor(o.p))," 席");
  drawTrend(rows,agg);
  drawTable(rows,party);
}

function drawTrend(rows,agg){
  const years=[...new Set(rows.map(d=>d.y))].sort();
  const tops=agg.slice(0,6).map(o=>o.p);
  const tot={};years.forEach(y=>tot[y]=0);rows.forEach(d=>tot[d.y]+=d.v);
  const ds=tops.map(p=>{
    const by={};years.forEach(y=>by[y]=0);
    rows.filter(d=>d.p===p).forEach(d=>by[d.y]+=d.v);
    return {label:p,borderColor:pColor(p),backgroundColor:pColor(p),tension:.25,spanGaps:true,
      data:years.map(y=>tot[y]?+(by[y]/tot[y]*100).toFixed(2):null)};
  });
  if(charts.chTrend)charts.chTrend.destroy();
  charts.chTrend=new Chart(document.getElementById("chTrend"),{type:"line",
    data:{labels:years,datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:"bottom"},tooltip:{callbacks:{label:c=>" "+c.dataset.label+": "+(c.parsed.y==null?"—":c.parsed.y+"%")}}},
      scales:{y:{title:{display:true,text:"得票佔比 %"},ticks:{callback:v=>v+"%"}}}}});
}

// ---- 明細表 ----
let sortKey="v",sortAsc=false;
function drawTable(rows,party){
  const COLS=party
    ?[{k:"y",t:"年度"},{k:"p",t:"政黨"},{k:"v",t:"得票數",num:1},{k:"vr",t:"得票率%",num:1},{k:"seats",t:"席次",num:1}]
    :[{k:"y",t:"年度"},{k:"region",t:"地區"},{k:"dist",t:"選區"},{k:"nm",t:"姓名"},{k:"p",t:"政黨"},{k:"v",t:"得票數",num:1},{k:"vr",t:"得票率%",num:1},{k:"w",t:"當選"}];
  document.getElementById("tblTitle").textContent=party?"不分區政黨明細":"候選人明細";
  const thead=document.querySelector("#tbl thead");
  thead.innerHTML="<tr>"+COLS.map(c=>'<th data-k="'+c.k+'" class="'+(c.num?"num ":"")+(c.k===sortKey?"sorted "+(sortAsc?"asc":""):"")+'">'+c.t+'</th>').join("")+"</tr>";
  thead.querySelectorAll("th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(k===sortKey)sortAsc=!sortAsc;else{sortKey=k;sortAsc=false;}drawTable(filtered(),party);});
  const sorted=[...rows].sort((a,b)=>{let x=a[sortKey],y=b[sortKey];
    if(typeof x==="number"||typeof y==="number"){x=x??-Infinity;y=y??-Infinity;return sortAsc?x-y:y-x;}
    x=x||"";y=y||"";return sortAsc?(""+x).localeCompare(y):(""+y).localeCompare(x);});
  const MAX=800,tb=document.querySelector("#tbl tbody");
  tb.innerHTML=sorted.slice(0,MAX).map(d=>party
    ?"<tr><td>"+d.y+"</td><td><span class='chip' style='background:"+pColor(d.p)+"'>"+d.p+"</span></td><td class='num'>"+fmt(d.v)+"</td><td class='num'>"+(d.vr==null?"—":d.vr)+"</td><td class='num'>"+(d.seats||0)+"</td></tr>"
    :"<tr><td>"+d.y+"</td><td>"+d.region+"</td><td>"+(d.dist||"")+"</td><td>"+d.nm+"</td><td><span class='chip' style='background:"+pColor(d.p)+"'>"+d.p+"</span></td><td class='num'>"+fmt(d.v)+"</td><td class='num'>"+(d.vr==null?"—":d.vr)+"</td><td class='"+(d.w?"win":"")+"'>"+(d.w?"★":"")+"</td></tr>"
  ).join("");
  document.getElementById("rowCount").textContent=rows.length+" 筆"+(rows.length>MAX?"(表格顯示前 "+MAX+" 筆,圖表為全部)":"");
}

// ---- 初始化 ----
document.getElementById("catSel").innerHTML=CATS.map(c=>'<option>'+c+'</option>').join("");
document.getElementById("catSel").onchange=e=>{state.cat=e.target.value;sortKey="v";sortAsc=false;onCatChange();};
document.querySelectorAll('#winSeg button').forEach(b=>b.onclick=e=>{
  document.querySelectorAll('#winSeg button').forEach(x=>x.classList.remove("on"));
  e.target.classList.add("on");state.win=e.target.dataset.w;render();});
document.getElementById("nameSearch").oninput=e=>{state.q=e.target.value.trim();render();};
onCatChange();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
