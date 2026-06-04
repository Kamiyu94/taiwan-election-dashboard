#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理鑽取資料產生器(階段 E)
從中選會 votedata.zip 萃取「全域型選舉」(總統 / 縣市長 / 直轄市長)的
  縣市 → 鄉鎮市區 → 村里  三層樹狀候選人得票,輸出分層 JSON 供儀表板線上按需載入。

輸出(data/ 目錄,供 GitHub Pages 線上 fetch):
  data/races.json                 可鑽取的選舉清單
  data/<race>/summary.json        該選舉:候選人 + 各縣市總得票(初始載入)
  data/<race>/<縣市碼>.json        該縣市:各區→各里候選人得票(點到才載)

用法: python3 build_geo.py
"""

import csv
import io
import json
import os
import re
import zipfile

ZIP = "cec_data/votedata.zip"
OUTDIR = "data"

# 要產生鑽取的全域型選舉(territory-wide,單一轄區同一場)
RACES = [
    # 總統(2016 在中選會開放資料缺,故未列)
    {"key": "pres2024", "label": "2024 總統", "units": ["2024總統立委/總統"]},
    {"key": "pres2020", "label": "2020 總統", "units": ["2020總統立委/總統"]},
    {"key": "pres2012", "label": "2012 總統", "units": ["20120114-總統及立委/總統"]},
    {"key": "pres2008", "label": "2008 總統", "units": ["20080322-總統"]},
    {"key": "pres2004", "label": "2004 總統", "units": ["2004   11任總統"]},
    {"key": "pres2000", "label": "2000 總統", "units": ["2000年10任總統"]},
    {"key": "pres1996", "label": "1996 總統", "units": ["9任總統"]},
    # 縣市長 / 直轄市長
    {"key": "mayor2022", "label": "2022 縣市長 / 直轄市長",
     "units": ["2022-111年地方公職人員選舉/C1/city", "2022-111年地方公職人員選舉/C1/prv"]},
    {"key": "mayor2018", "label": "2018 縣市長 / 直轄市長",
     "units": ["2018-107年地方公職人員選舉/縣市市長", "2018-107年地方公職人員選舉/直轄市市長"]},
    {"key": "mayor2014", "label": "2014 縣市長 / 直轄市長",
     "units": ["2014-103年地方公職人員選舉/縣市市長", "2014-103年地方公職人員選舉/直轄市市長"]},
    {"key": "mayor2010dpm", "label": "2010 直轄市長(五都)", "units": ["20101127-五都市長議員及里長/市長"]},
    {"key": "mayor2006kh", "label": "2006 直轄市長(北高)", "units": ["2006直轄市長"]},
    {"key": "mayor2005", "label": "2005 縣市長", "units": ["2005縣市長"]},
    {"key": "mayor2001", "label": "2001 縣市長", "units": ["2001縣市長"]},
    {"key": "mayor1997", "label": "1997 縣市長", "units": ["1997縣市長"]},
]


def dec(name):
    try:
        return name.encode("cp437").decode("big5", "replace")
    except Exception:
        return name


def to_int(s):
    s = (s or "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


class Zip:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.map = {}
        for n in self.z.namelist():
            if not n.endswith("/"):
                self.map[dec(n)] = n

    def read(self, suffix):
        for disp, real in self.map.items():
            if disp.endswith(suffix):
                txt = self.z.read(real).decode("utf-8", "replace")
                out = []
                for r in csv.reader(io.StringIO(txt)):
                    out.append([c.strip().strip('"').strip().lstrip("'") for c in r])
                return out
        return None


def load_unit(z, unit):
    """回傳 (candidates_by_key, elbase_name, ctks_rows)"""
    paty = {}
    for r in (z.read(unit + "/elpaty.csv") or []):
        if len(r) >= 2 and to_int(r[0]) is not None:
            paty[to_int(r[0])] = r[1]
    cands = {}  # (省,縣,號次) -> {name, party}
    for r in (z.read(unit + "/elcand.csv") or []):
        if len(r) < 8 or to_int(r[5]) is None:
            continue
        key = (r[0], r[1], to_int(r[5]))
        if key not in cands:  # 取正手(首列)
            cands[key] = {"name": r[6], "party": paty.get(to_int(r[7]), str(to_int(r[7])))}
    name = {}  # (省,縣,鄉,村) -> 名稱
    for r in (z.read(unit + "/elbase.csv") or []):
        if len(r) >= 6:
            name[(r[0], r[1], r[3], r[4])] = r[5]
    ctks = z.read(unit + "/elctks.csv") or []
    return cands, name, ctks


def build_race(z, race):
    cities = {}          # 縣市碼 -> {name, cands:{no:{}}, votes:{no:v}, districts:{...}}
    for unit in race["units"]:
        cands, name, ctks = load_unit(z, unit)
        for r in ctks:
            if len(r) < 9:
                continue
            prov, city, dist_z, town, li = r[0], r[1], r[2], r[3], r[4]
            poll, no, votes = r[5], to_int(r[6]), to_int(r[7])
            if no is None or votes is None:
                continue
            if poll.lstrip("0") != "":      # 只要投開票所彙總(=0)
                continue
            if prov == "00":                # 跳過全國列
                continue
            # 注意:全域型選舉縣市總在選區=00、區/里在選區=01,各層級不重疊,
            # 故不過濾選區;votes 用指派(非累加),縱有重複列也不會疊加。
            ccode = prov + city
            c = cities.setdefault(ccode, {
                "name": name.get((prov, city, "000", "0000"), ccode),
                "cands": {}, "votes": {}, "districts": {},
            })
            cand = cands.get((prov, city, no)) or cands.get(("00", "000", no)) or {"name": "?", "party": ""}
            c["cands"][no] = cand
            if town == "000" and li == "0000":          # 縣市總計
                c["votes"][no] = votes
            elif li == "0000":                           # 區
                d = c["districts"].setdefault(town, {
                    "name": name.get((prov, city, town, "0000"), town), "votes": {}, "li": {}})
                d["votes"][no] = votes
            else:                                         # 里
                d = c["districts"].setdefault(town, {
                    "name": name.get((prov, city, town, "0000"), town), "votes": {}, "li": {}})
                lz = d["li"].setdefault(li, {"name": name.get((prov, city, town, li), li), "votes": {}})
                lz["votes"][no] = votes
    return cities


def cand_list(c):
    return [{"no": no, **c["cands"][no]} for no in sorted(c["cands"])]


def main():
    z = Zip(ZIP)
    os.makedirs(OUTDIR, exist_ok=True)
    races_index = []

    for race in RACES:
        cities = build_race(z, race)
        if not cities:
            print(f"[!] {race['label']} 無資料,略過")
            continue
        rdir = os.path.join(OUTDIR, race["key"])
        os.makedirs(rdir, exist_ok=True)

        # summary:候選人(以最大縣市為代表)+ 各縣市總得票
        summary_cities = []
        for ccode, c in sorted(cities.items()):
            summary_cities.append({"code": ccode, "name": c["name"],
                                   "cands": cand_list(c), "votes": c["votes"]})
            # 各縣市細檔:區 → 里
            districts = []
            for tcode, d in sorted(c["districts"].items()):
                districts.append({
                    "code": tcode, "name": d["name"], "votes": d["votes"],
                    "li": [{"code": lc, "name": lz["name"], "votes": lz["votes"]}
                           for lc, lz in sorted(d["li"].items())],
                })
            with open(os.path.join(rdir, ccode + ".json"), "w", encoding="utf-8") as f:
                json.dump({"name": c["name"], "cands": cand_list(c), "districts": districts},
                          f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(rdir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump({"label": race["label"], "cities": summary_cities},
                      f, ensure_ascii=False, separators=(",", ":"))
        races_index.append({"key": race["key"], "label": race["label"], "cities": len(cities)})
        print(f"[*] {race['label']}: {len(cities)} 縣市")

    with open(os.path.join(OUTDIR, "races.json"), "w", encoding="utf-8") as f:
        json.dump(races_index, f, ensure_ascii=False)
    # 體積統計
    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUTDIR) for f in fs)
    print(f"[*] data/ 總大小 {total/1024:.0f} KB")


if __name__ == "__main__":
    main()
