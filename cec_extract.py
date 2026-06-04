#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中選會選舉資料庫(votedata.zip)→ 立委 / 議員 結構化 CSV(階段 D)

依官方「選舉資料庫格式」欄位定義,從 zip 內每個「選舉單元」(含 elcand.csv 的目錄)萃取:
  - 區域 / 原住民(山地·平地)→ 候選人逐筆得票  → cec_candidates.csv
  - 不分區政黨            → 政黨得票率/席次     → cec_partylist.csv

關鍵:
  * zip 檔名為 Big5,內容為 UTF-8;新檔有引號、舊檔無引號 → 一律用 csv 模組解析
  * elctks 取「投開票所=0」且與候選人同一行政區層級的彙總列 = 該候選人在其選區的總得票
  * 政黨名、地區名、選區名分別以該單元的 elpaty / elbase 對照

用法: python3 cec_extract.py
"""

import csv
import io
import re
import zipfile

ZIP = "cec_data/votedata.zip"
OUT_CAND = "cec_candidates.csv"
OUT_PARTY = "cec_partylist.csv"

NON_TARGET_LEAF = ("縣市長", "市長", "總統", "鄉鎮", "代表", "國代", "省長", "公投", "村里長", "里長")


def dec(name):
    """zip 內 Big5 檔名 → 可讀字串"""
    try:
        return name.encode("cp437").decode("big5", "replace")
    except Exception:
        return name


def read_csv(z, zipname):
    """讀單一檔 → list[list[str]](去引號、去空白)"""
    txt = z.read(zipname).decode("utf-8", "replace")
    rows = []
    for r in csv.reader(io.StringIO(txt)):
        cells = []
        for c in r:
            c = c.strip().strip('"').strip()
            if c.startswith("'"):  # 部分檔案有 Excel 文字前綴單引號(如 '01)
                c = c[1:]
            cells.append(c)
        rows.append(cells)
    return rows


def classify(path):
    """由路徑判斷 (類別, 層級, 年度);非立委/議員回 None"""
    parts = [p for p in path.split("/") if p]
    leaf = parts[-1]
    parent = parts[-2] if len(parts) > 1 else ""

    if any(k in leaf for k in NON_TARGET_LEAF):
        return None
    src = leaf if any(k in leaf for k in ("立委", "立法委員", "議員")) else parent
    if "立委" in src or "立法委員" in src:
        typ = "立委"
    elif "議員" in src:
        typ = "議員"
    else:
        return None

    if "不分區" in leaf:
        sub = "不分區"
    elif "山" in leaf:
        sub = "山地原住民"
    elif "平" in leaf:
        sub = "平地原住民"
    elif "原住民" in leaf:
        sub = "原住民"
    else:
        sub = "區域"

    m = re.search(r"(19|20)\d{2}", path)
    year = m.group(0) if m else parent
    # 「N屆立委」推回年度(第3屆立委=1995)
    if not re.search(r"(19|20)\d{2}", year):
        dm = re.search(r"(\d+)\s*屆", path)
        TERM_YEAR = {"3": "1995", "4": "1998", "5": "2001"}
        if dm and dm.group(1) in TERM_YEAR:
            year = TERM_YEAR[dm.group(1)]
    return typ, sub, year


def find_units(z):
    """回傳 {目錄zip前綴: (顯示路徑)} 所有含 elcand.csv 的單元"""
    units = {}
    for n in z.namelist():
        d = dec(n)
        if d.endswith("elcand.csv"):
            zip_prefix = n[:-len("elcand.csv")]
            units[zip_prefix] = d[:-len("elcand.csv")]
    return units


def files_in(z, prefix):
    """該單元目錄下的檔名對照 {基本檔名: zip內名}"""
    out = {}
    plen = len(prefix)
    for n in z.namelist():
        if n.startswith(prefix) and not n.endswith("/"):
            base = n[plen:]
            if "/" not in base:
                out[base] = n
    return out


def to_int(s):
    s = (s or "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def num_area(cols):
    """前 5 欄行政區 key (省市,縣市,選區,鄉鎮,村里)"""
    return tuple(cols[:5])


def build_elbase(rows):
    """key=(省市,縣市,選區,鄉鎮,村里) → 名稱"""
    m = {}
    for r in rows:
        if len(r) >= 6:
            m[num_area(r)] = r[5]
    return m


def build_elpaty(rows):
    m = {}
    for r in rows:
        if len(r) >= 2 and to_int(r[0]) is not None:
            m[to_int(r[0])] = r[1]
    return m


def is_total(field):
    """投開票所欄是否為『彙總』(數值 0;可能是 0 / 00 / 0000)"""
    return to_int(field) == 0


def build_vote_index(rows):
    """
    取每個行政區層級的彙總列(投開票所=0):
      key=(省市,縣市,選區,鄉鎮,村里,號次) → (得票數, 得票率, 當選註記)
    候選人用自己的行政區精準對到所屬選區的那一列。
    """
    m = {}
    for r in rows:
        if len(r) >= 9 and is_total(r[5]):
            key = (r[0], r[1], r[2], r[3], r[4], to_int(r[6]))
            m[key] = (to_int(r[7]), r[8], r[9] if len(r) > 9 else "")
    return m


def name_for(elbase, area, level):
    """level: 'city' 取縣市名;'dist' 取選區名"""
    省, 縣, 選, 鄉, 村 = area
    if level == "city":
        return elbase.get((省, 縣, "00", "000", "0000")) or elbase.get((省, 縣, "00", "000", "0000")) or ""
    if level == "dist":
        return elbase.get((省, 縣, 選, "000", "0000")) or ""
    return ""


def extract():
    z = zipfile.ZipFile(ZIP)
    units = find_units(z)

    cand_rows, party_rows = [], []
    stats = {"立委": 0, "議員": 0}
    skipped = 0

    for prefix, disp in sorted(units.items(), key=lambda x: x[1]):
        info = classify(disp)
        if not info:
            skipped += 1
            continue
        typ, sub, year = info
        fs = files_in(z, prefix)
        if "elcand.csv" not in fs:
            continue

        elpaty = build_elpaty(read_csv(z, fs["elpaty.csv"])) if "elpaty.csv" in fs else {}
        elbase = build_elbase(read_csv(z, fs["elbase.csv"])) if "elbase.csv" in fs else {}

        if sub == "不分區":
            # 不分區:elretks = 政黨得票率/席次;得票數由 elprof 全國有效票推算
            if "elretks.csv" not in fs:
                continue
            valid = None
            if "elprof.csv" in fs:
                for r in read_csv(z, fs["elprof.csv"]):
                    # 全國彙總列:各行政區欄與投開票所皆為 0,有效票在第 7 欄
                    if len(r) >= 7 and all(to_int(x) == 0 for x in r[:6]) and to_int(r[6]) is not None:
                        valid = to_int(r[6]); break
            for r in read_csv(z, fs["elretks.csv"]):
                if len(r) < 5 or to_int(r[0]) is None:
                    continue
                pid = to_int(r[0])
                rate = r[1]
                seats = to_int(r[4])
                votes = ""
                try:
                    if valid is not None:
                        votes = round(valid * float(rate) / 100)
                except ValueError:
                    pass
                party_rows.append({
                    "選舉年度": year, "選舉類別": typ, "層級": "不分區",
                    "政黨": elpaty.get(pid, str(pid)),
                    "得票數": votes, "得票率": rate, "當選席次": seats if seats is not None else "",
                })
            stats[typ] += 1
            continue

        # 區域 / 原住民:候選人逐筆
        if "elctks.csv" not in fs:
            continue
        cand = [r for r in read_csv(z, fs["elcand.csv"]) if len(r) >= 8 and to_int(r[5]) is not None]
        if not cand:
            continue
        tks = build_vote_index(read_csv(z, fs["elctks.csv"]))
        for r in cand:
            area = num_area(r)
            no = to_int(r[5])
            if sub == "區域":
                keys = [(area[0], area[1], area[2], area[3], area[4], no)]
            else:
                # 原住民類:立委為全國選區、議員為各縣市原住民選區
                # 逐層回退:精準 → 清空選區 → 全國
                keys = [
                    (area[0], area[1], area[2], area[3], area[4], no),
                    (area[0], area[1], "00", "000", "0000", no),
                    ("00", "000", "00", "000", "0000", no),
                ]
            votes, rate, _mark = (None, "", "")
            for key in keys:
                if key in tks:
                    votes, rate, _mark = tks[key]; break
            pid = to_int(r[7])
            dist = name_for(elbase, area, "dist") or r[2]
            city = name_for(elbase, area, "city") or re.sub(r"第.*$", "", dist)  # 縣市對不到時由選區名回推
            cand_rows.append({
                "選舉年度": year, "選舉類別": typ, "層級": sub,
                "縣市": city,
                "選區": dist,
                "號次": no, "姓名": r[6], "性別": r[8] if len(r) > 8 else "",
                "政黨": elpaty.get(pid, str(pid)),
                "得票數": votes if votes is not None else "",
                "得票率": rate,
                "當選": "Y" if (len(r) > 14 and r[14] == "*") else "N",
            })
        stats[typ] += 1

    # 寫出
    cfields = ["選舉年度", "選舉類別", "層級", "縣市", "選區", "號次", "姓名", "性別", "政黨", "得票數", "得票率", "當選"]
    with open(OUT_CAND, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cfields); w.writeheader()
        for r in cand_rows: w.writerow(r)
    pfields = ["選舉年度", "選舉類別", "層級", "政黨", "得票數", "得票率", "當選席次"]
    with open(OUT_PARTY, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=pfields); w.writeheader()
        for r in party_rows: w.writerow(r)

    print(f"[*] 處理單元:立委 {stats['立委']}、議員 {stats['議員']}(跳過非目標 {skipped})")
    print(f"[*] {OUT_CAND}: {len(cand_rows)} 列(區域+原住民候選人)")
    print(f"[*] {OUT_PARTY}: {len(party_rows)} 列(不分區政黨)")


if __name__ == "__main__":
    extract()
