#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政大選舉研究中心「歷屆公職選舉資料庫」索引解析器
來源: https://vote.nccu.edu.tw/cec/cechead.asp

解析主索引頁,把每一場選舉的:
  - 選舉年度、選舉別
  - 兩個 HTML 動態頁連結 (選舉概況表 vote421 / 候選人得票明細 vote3)
  - 各類統計 PDF 連結
攤平成一張 CSV,供後續逐頁爬取使用。

用法:
    python3 parse_index.py            # 線上抓取並輸出 index.csv
    python3 parse_index.py local.html # 解析本機已存檔的 HTML
"""

import csv
import re
import sys
import urllib.request
from typing import List, Dict, Optional

BASE = "https://vote.nccu.edu.tw/cec/"
INDEX_URL = BASE + "cechead.asp"
OUT_CSV = "index.csv"

# 表頭 7 欄資料(對照主頁表頭順序)
# 概況表(vote421) / 得票明細(vote3) 為 HTML;其餘為 PDF,依出現順序對應:
PDF_COLUMNS = [
    "候選人資歷統計_pdf",
    "當選人資歷統計_pdf",
    "政黨得票統計_pdf",
    "政黨候選人數與當選席次_pdf",
]


def fetch(url: str) -> str:
    """抓取網頁並以 Big5 解碼(此站為 Big5 編碼的古典 ASP)。"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research/data-analysis)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("big5", errors="ignore")


def load_html(arg: Optional[str]) -> str:
    if arg:
        with open(arg, "rb") as f:
            return f.read().decode("big5", errors="ignore")
    return fetch(INDEX_URL)


def parse_index(html: str) -> List[Dict]:
    """把主索引頁切成一列一列選舉,逐列抽出年度/選舉別/各連結。"""
    # 找到資料起點(第一個年度列),避開表頭
    start = re.search(r"<td align=right>\d{4}</td>", html)
    if not start:
        return []
    body = html[start.start():]

    # 以 <tr> 切列(每場選舉一列)
    rows = re.split(r"<tr>", body, flags=re.IGNORECASE)
    records = []
    for row in rows:
        ym = re.search(r"<td align=right>(\d{4})</td>", row)
        if not ym:
            continue
        year = ym.group(1)

        tm = re.search(r"<td align=left>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        etype = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""

        # 依出現順序抓出所有 href(保留順序很重要)
        hrefs = re.findall(r"href=['\"]([^'\"]+)['\"]", row, flags=re.IGNORECASE)

        rec = {
            "選舉年度": year,
            "選舉別": etype,
            "選舉概況表_url": "",
            "候選人得票明細_url": "",
        }
        for col in PDF_COLUMNS:
            rec[col] = ""

        pdf_idx = 0
        for h in hrefs:
            full = h if h.lower().startswith("http") else BASE + h
            low = h.lower()
            if low.startswith("vote421.asp"):
                rec["選舉概況表_url"] = full
            elif low.startswith("vote3.asp"):
                rec["候選人得票明細_url"] = full
            elif low.endswith(".pdf"):
                if pdf_idx < len(PDF_COLUMNS):
                    rec[PDF_COLUMNS[pdf_idx]] = full
                else:
                    rec[f"其他_pdf_{pdf_idx}"] = full
                pdf_idx += 1

        records.append(rec)
    return records


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"[*] 取得索引頁 {'(本機檔案 ' + arg + ')' if arg else INDEX_URL} ...")
    html = load_html(arg)
    records = parse_index(html)
    print(f"[*] 解析到 {len(records)} 場選舉")

    if not records:
        print("[!] 沒有解析到任何資料,請檢查來源 HTML。")
        sys.exit(1)

    # 統一欄位(含可能出現的「其他_pdf_*」)
    fields = ["選舉年度", "選舉別", "選舉概況表_url", "候選人得票明細_url"] + PDF_COLUMNS
    extra = sorted({k for r in records for k in r if k not in fields})
    fields += extra

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in fields})

    print(f"[*] 已寫出 {OUT_CSV} (UTF-8-SIG, 可直接用 Excel 開)")
    # 簡單統計
    years = sorted({r["選舉年度"] for r in records})
    print(f"[*] 年度範圍: {years[0]} ~ {years[-1]} (共 {len(years)} 個年度)")


if __name__ == "__main__":
    main()
