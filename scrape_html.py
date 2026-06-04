#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政大選舉資料庫 — HTML 表格爬蟲 (階段 B)
讀 index.csv,逐場抓「選舉概況表(vote421)」與「候選人得票明細(vote3)」,
解析成兩張適合做儀表板的長格式 CSV:

  - overview_turnout.csv  選舉概況(地區層級投票率/票數),62 場
  - detail_candidates.csv 候選人得票明細(候選人層級),48 場

特性:
  * 純標準庫(html.parser),免裝任何套件
  * 正確展開 HTML 表格的 rowspan / colspan
  * 表頭驅動對應欄位(自動適應總統「組」vs 縣市長「計/男/女」等差異)
  * 總統正副手:合併為同一筆,副手記在「副手姓名」等欄
  * 原始 HTML 快取於 ./cache/,重跑不重打伺服器
  * 每次請求間隔禮貌延遲

用法:
    python3 scrape_html.py            # 全抓
    python3 scrape_html.py --limit 5  # 只抓前 5 場(測試)
"""

import csv
import hashlib
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

INDEX_CSV = "index.csv"
CACHE_DIR = "cache"
OUT_OVERVIEW = "overview_turnout.csv"
OUT_DETAIL = "detail_candidates.csv"
DELAY_SEC = 1.2  # 禮貌延遲

# ----------------------------------------------------------------------------
# 抓取 + 快取
# ----------------------------------------------------------------------------

def cache_path(url: str) -> str:
    # 用完整 URL 的雜湊當檔名,避免 pass1 含 <>: 等字元被正規化後碰撞
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
    prefix = "ov" if "vote421" in url else "dt"
    return os.path.join(CACHE_DIR, f"{prefix}_{h}.html")


def fetch(url: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = cache_path(url)
    if os.path.exists(cp):
        with open(cp, "rb") as f:
            return f.read().decode("big5", errors="ignore")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research/data-analysis)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    with open(cp, "wb") as f:
        f.write(raw)
    time.sleep(DELAY_SEC)  # 只有真的打網路才延遲
    return raw.decode("big5", errors="ignore")


# ----------------------------------------------------------------------------
# HTML 第一個 <table> → 展開 rowspan/colspan 的網格
# 每個 cell = {"text": str, "is_header": bool, "origin": (r,c)}
# ----------------------------------------------------------------------------

class FirstTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.done = False
        self.rows = []          # list of list of raw-cell dicts
        self._cur = None        # current row cells
        self._cell = None       # current cell dict
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        a = dict(attrs)
        if tag == "table":
            if not self.in_table:
                self.in_table = True
            self._depth += 1
            return
        if not self.in_table:
            return
        if tag == "tr":
            self._cur = []
            self.rows.append(self._cur)
        elif tag in ("td", "th"):
            bg = (a.get("bgcolor") or "").lower()
            self._cell = {
                "text": "",
                "rowspan": int(a.get("rowspan", 1) or 1),
                "colspan": int(a.get("colspan", 1) or 1),
                "is_header": "004000" in bg,  # 深綠表頭
            }
            if self._cur is None:  # 容錯:td 在 tr 之外
                self._cur = []
                self.rows.append(self._cur)
            self._cur.append(self._cell)

    def handle_endtag(self, tag):
        if self.done or not self.in_table:
            return
        if tag in ("td", "th"):
            self._cell = None
        elif tag == "table":
            self._depth -= 1
            if self._depth <= 0:
                self.done = True
                self.in_table = False

    def handle_data(self, data):
        if self._cell is not None and not self.done:
            self._cell["text"] += data


def build_grid(html: str):
    """回傳 grid:list[list[cell]],cell 含 text/is_header/origin。已展開 span。"""
    p = FirstTableParser()
    p.feed(html)
    raw_rows = [r for r in p.rows if r]  # 去掉空 tr
    grid = []                            # 最終 2D
    occupied = {}                        # (r,c) -> cell (被 span 佔用)

    for r, cells in enumerate(raw_rows):
        if len(grid) <= r:
            grid.append([])
        c = 0
        for cell in cells:
            # 跳過已被上方 rowspan 佔據的欄
            while (r, c) in occupied:
                c += 1
            text = re.sub(r"\s+", " ", cell["text"]).strip()
            origin = (r, c)
            for dr in range(cell["rowspan"]):
                for dc in range(cell["colspan"]):
                    rr, cc = r + dr, c + dc
                    while len(grid) <= rr:
                        grid.append([])
                    val = {
                        "text": text,
                        "is_header": cell["is_header"],
                        "origin": origin,
                    }
                    occupied[(rr, cc)] = val
            c += cell["colspan"]

    # 從 occupied 重建規整 2D
    if not occupied:
        return []
    maxr = max(k[0] for k in occupied)
    maxc = max(k[1] for k in occupied)
    out = []
    for rr in range(maxr + 1):
        row = []
        for cc in range(maxc + 1):
            row.append(occupied.get((rr, cc), {"text": "", "is_header": False, "origin": (rr, cc)}))
        out.append(row)
    return out


def split_header_data(grid):
    """前面連續的『整列都是表頭』算表頭列,其餘為資料列。"""
    hdr_rows, data_start = [], 0
    for i, row in enumerate(grid):
        if any(cell["is_header"] for cell in row):
            hdr_rows.append(row)
        else:
            data_start = i
            break
    else:
        data_start = len(grid)
    return hdr_rows, grid[data_start:]


def column_names(hdr_rows):
    """把多層表頭壓成每欄一個名稱,例如 投票數_合計、候選人數_計。"""
    if not hdr_rows:
        return []
    ncol = max(len(r) for r in hdr_rows)
    names = []
    for c in range(ncol):
        parts = []
        for row in hdr_rows:
            if c < len(row):
                t = row[c]["text"]
                if t and (not parts or parts[-1] != t):
                    parts.append(t)
        names.append("_".join(parts))
    return names


# ----------------------------------------------------------------------------
# 數值清洗
# ----------------------------------------------------------------------------

def num(s):
    s = (s or "").strip()
    if s in ("", "--", "-", "X", "x"):
        return ""
    s = s.replace(",", "")
    return s if re.fullmatch(r"-?\d+(\.\d+)?", s) else s


def pct(s):
    s = (s or "").strip().replace("%", "")
    if s in ("", "--", "-"):
        return ""
    return s if re.fullmatch(r"-?\d+(\.\d+)?", s) else ""


# ----------------------------------------------------------------------------
# 選舉 meta 解析
# ----------------------------------------------------------------------------

ROC_RE = re.compile(r"中華民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日")


def parse_meta(year, etype, html):
    m = re.search(r"第\s*(\d+)\s*([任屆])", etype)
    term = m.group(1) if m else ""
    category = re.sub(r"第\s*\d+\s*[任屆]\s*", "", etype).strip()
    # 投票日期
    dm = ROC_RE.search(html)
    vote_date = ""
    if dm:
        roc, mo, da = map(int, dm.groups())
        vote_date = f"{roc + 1911}-{mo:02d}-{da:02d}"
    return {
        "選舉年度": year,
        "選舉別": etype,
        "選舉類別": category,
        "屆任次": term,
        "投票日期": vote_date,
    }


# ----------------------------------------------------------------------------
# 概況表解析
# ----------------------------------------------------------------------------

def map_overview_col(name):
    """表頭名稱 → 正規化欄位。回傳 None 表示忽略。"""
    n = name.replace(" ", "")
    if "對" in n:  # 比率欄
        if "選舉人數對人口數" in n:
            return "選舉人數對人口數_pct"
        if "投票數對選舉人數" in n:
            return "投票率_pct"
        if "當選人數對候選人數" in n or "當選人對候選人" in n:
            return "當選對候選_pct"
        return None
    if n.startswith("地區"):
        return "地區別"
    if n == "人口數":
        return "人口數"
    if n == "選舉人數":
        return "選舉人數"
    if n.startswith("候選") and (n.endswith("計") or n.endswith("組數") or n == "候選人數"):
        return "候選人數"
    if n.startswith("當選") and (n.endswith("計") or n.endswith("組數") or n == "當選人數"):
        return "當選人數"
    if "投票數_合計" in n or n == "投票數":
        return "投票數合計"
    if "有效票" in n:
        return "有效票數"
    if "無效票" in n:
        return "無效票數"
    return None


OVERVIEW_FIELDS = [
    "地區別", "人口數", "選舉人數", "候選人數", "當選人數",
    "投票數合計", "有效票數", "無效票數",
    "選舉人數對人口數_pct", "投票率_pct", "當選對候選_pct",
]


def parse_overview(meta, html):
    grid = build_grid(html)
    if not grid:
        return []
    hdr, data = split_header_data(grid)
    names = column_names(hdr)
    colmap = {c: map_overview_col(n) for c, n in enumerate(names)}

    out = []
    for row in data:
        rec = dict(meta)
        for f in OVERVIEW_FIELDS:
            rec[f] = ""
        got_region = False
        for c, cell in enumerate(row):
            field = colmap.get(c)
            if not field:
                continue
            val = cell["text"]
            if field == "地區別":
                rec["地區別"] = val
                got_region = bool(val)
            elif field.endswith("_pct"):
                rec[field] = pct(val)
            else:
                rec[field] = num(val)
        if got_region or any(rec[f] for f in OVERVIEW_FIELDS[1:]):
            out.append(rec)
    return out


# ----------------------------------------------------------------------------
# 得票明細解析(行政首長類;總統含正副手)
# ----------------------------------------------------------------------------

def map_detail_col(name):
    n = name.replace(" ", "")
    if n.startswith("地區"):
        return "地區"
    if "姓名" in n:
        return "姓名"
    if "號次" in n:
        return "號次"
    if "性別" in n:
        return "性別"
    if "出生" in n:
        return "出生年次"
    if "政黨" in n:
        return "推薦政黨"
    if "得票率" in n:
        return "得票率"
    if "得票" in n:
        return "得票數"
    if "當選" in n:
        return "當選否"
    if "現任" in n:
        return "是否現任"
    return None


DETAIL_FIELDS = [
    "地區", "號次", "姓名", "性別", "出生年次", "推薦政黨",
    "得票數", "得票率", "當選否", "是否現任",
    "副手姓名", "副手性別", "副手出生年次",
]


def parse_detail(meta, html):
    grid = build_grid(html)
    if not grid:
        return []
    hdr, data = split_header_data(grid)
    names = column_names(hdr)
    colmap = {c: map_detail_col(n) for c, n in enumerate(names)}
    # 找「得票數」欄的 index,用來判斷正/副手
    votes_col = next((c for c, f in colmap.items() if f == "得票數"), None)

    out = []
    cur = None
    for r_idx, row in enumerate(data):
        # 該列的得票數是否「自有」(origin 在本列)→ 主候選人;否則為副手
        is_primary = True
        if votes_col is not None and votes_col < len(row):
            cell = row[votes_col]
            # data 區段的列索引需換算回 grid 絕對列;用 origin 第一碼比較相對關係
            is_primary = (cell["text"] != "" and cell["origin"][0] == _abs_row(grid, hdr, r_idx))
        if is_primary:
            cur = dict(meta)
            for f in DETAIL_FIELDS:
                cur[f] = ""
            for c, cell in enumerate(row):
                field = colmap.get(c)
                if not field:
                    continue
                v = cell["text"]
                if field == "得票數":
                    cur[field] = num(v)
                elif field == "得票率":
                    cur[field] = pct(v)
                else:
                    cur[field] = v
            if cur.get("姓名") or cur.get("得票數"):
                out.append(cur)
        else:
            # 副手:取本列自有的姓名/性別/出生
            if cur is None:
                continue
            for c, cell in enumerate(row):
                field = colmap.get(c)
                if field == "姓名" and cell["origin"][0] == _abs_row(grid, hdr, r_idx):
                    cur["副手姓名"] = cell["text"]
                elif field == "性別" and cell["origin"][0] == _abs_row(grid, hdr, r_idx):
                    cur["副手性別"] = cell["text"]
                elif field == "出生年次" and cell["origin"][0] == _abs_row(grid, hdr, r_idx):
                    cur["副手出生年次"] = cell["text"]
    return out


def _abs_row(grid, hdr, data_row_idx):
    """資料列在 data 切片中的 index → 在整個 grid 的絕對列號。"""
    return len(hdr) + data_row_idx


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------

def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    rows = list(csv.DictReader(open(INDEX_CSV, encoding="utf-8-sig")))
    if limit:
        rows = rows[:limit]

    meta_fields = ["選舉年度", "選舉別", "選舉類別", "屆任次", "投票日期"]
    overview_all, detail_all = [], []

    for i, r in enumerate(rows, 1):
        year, etype = r["選舉年度"], r["選舉別"]
        ov_url, dt_url = r["選舉概況表_url"], r["候選人得票明細_url"]
        print(f"[{i}/{len(rows)}] {year} {etype}")

        if ov_url:
            html = fetch(ov_url)
            meta = parse_meta(year, etype, html)
            recs = parse_overview(meta, html)
            overview_all.extend(recs)
            print(f"      概況: {len(recs)} 區")
        if dt_url:
            html = fetch(dt_url)
            meta = parse_meta(year, etype, html)
            recs = parse_detail(meta, html)
            detail_all.extend(recs)
            print(f"      明細: {len(recs)} 候選人")

    write_csv(OUT_OVERVIEW, meta_fields + OVERVIEW_FIELDS, overview_all)
    write_csv(OUT_DETAIL, meta_fields + DETAIL_FIELDS, detail_all)
    print()
    print(f"[*] {OUT_OVERVIEW}: {len(overview_all)} 列")
    print(f"[*] {OUT_DETAIL}: {len(detail_all)} 列")


if __name__ == "__main__":
    main()
