# 政大選舉資料庫 爬取與資料集

來源:政治大學選舉研究中心「歷屆公職選舉資料庫」
<https://vote.nccu.edu.tw/cec/cechead.asp>(Big5 編碼的古典 ASP 站,無反爬)

## 檔案

| 檔案 | 說明 |
|------|------|
| `parse_index.py` | 階段 A:解析政大主索引頁 → `index.csv` |
| `scrape_html.py` | 階段 B:依索引逐場抓概況表 / 得票明細 → 兩張 CSV |
| `cec_extract.py` | 階段 D:從中選會 votedata.zip 萃取立委/議員 → `cec_candidates.csv`、`cec_partylist.csv` |
| `build_dashboard.py` | 統一 NCCU+CEC 資料,打包成級聯篩選互動儀表板 → `dashboard.html` |
| `build_geo.py` | 階段 E:萃取全域型選舉的縣市→區→里樹狀得票 → `data/`(供鑽取頁線上載入) |
| `drill.html` | 地理鑽取頁:全國▸縣市▸區▸里 逐層下鑽(需線上版,會按需 fetch `data/`) |
| `index.csv` | 105 場選舉(1992–2024)的連結索引 |
| `overview_turnout.csv` | **選舉概況**(地區層級投票率/票數),504 列 |
| `detail_candidates.csv` | **候選人得票明細**(候選人層級),724 列 |
| `dashboard.html` | **單一檔互動儀表板**,雙擊用瀏覽器開即可 |
| `vendor/chart.umd.min.js` | 圖表函式庫(打包進 dashboard.html 用) |
| `cache/` | 原始 HTML 快取(重跑不重打伺服器,可刪) |

## 互動儀表板

直接雙擊 `dashboard.html`(免安裝、免網路、免伺服器)。採**級聯篩選**避免資料量爆炸:

1. **選舉類別**(單選,驅動其餘)→ 2. **年度**(多選,供趨勢曲線)→ 3. **地區**(多選)→ 4. **政黨**(多選)+ 候選人搜尋 / 當選與否
- 即時更新:KPI、各政黨總得票數、各政黨當選席次、各政黨得票佔比趨勢(折線)、可排序明細表
- 涵蓋類別:總統、直轄市長、縣市長、省長、立法委員(區域/原住民/不分區政黨)、地方議員(區域/原住民)

資料異動後重建:`python3 build_dashboard.py`

## 階段 D:中選會官方資料(立委 / 議員)

政大資料庫的立委/議員候選人得票只在掃描 PDF 內,故改用**中選會選舉資料庫開放資料**
(`https://data.cec.gov.tw/選舉資料庫/votedata.zip`,政府資料開放授權)。

`cec_extract.py` 依官方「選舉資料庫格式」解析關聯式 `el*` 檔(elcand/elctks/elpaty/elbase/elprof),
輸出 `cec_candidates.csv`(14,669 筆候選人逐筆)與 `cec_partylist.csv`(不分區政黨得票)。
原始 110MB zip 不入版控(見 `.gitignore`);重跑前請自行下載至 `cec_data/votedata.zip`。

> 已知小缺口:1994–2006 早期直轄市原住民議員約 42 筆無對應得票(占 0.3%,區碼結構差異)。

## 重跑

```bash
python3 parse_index.py      # 重建 index.csv(線上抓)
python3 scrape_html.py      # 重建兩張資料 CSV(讀 cache,缺的才連網)
python3 scrape_html.py --limit 5   # 只測前 5 場
```

CSV 皆為 **UTF-8-SIG**(Excel 直接開不亂碼)、**長格式 tidy data**,可直接餵 Looker Studio / Power BI / Tableau。

## 資料字典

### overview_turnout.csv(每列 = 一場選舉 × 一個地區)
選舉年度 / 選舉別 / 選舉類別 / 屆任次 / 投票日期 / 地區別 /
人口數 / 選舉人數 / 候選人數 / 當選人數 / 投票數合計 / 有效票數 / 無效票數 /
選舉人數對人口數_pct / 投票率_pct / 當選對候選_pct

### detail_candidates.csv(每列 = 一位候選人/一組候選人)
選舉年度 / 選舉別 / 選舉類別 / 屆任次 / 投票日期 / 地區 /
號次 / 姓名 / 性別 / 出生年次 / 推薦政黨 / 得票數 / 得票率 / 當選否(Y/N) / 是否現任(Y/N) /
副手姓名 / 副手性別 / 副手出生年次（僅總統選舉有副手）

## 涵蓋範圍與限制

- **得票明細(候選人層級)只涵蓋單一當選人的行政首長選舉**:總統、各直轄市長、縣市長、省長。
- **議員 / 鄉鎮市長只有概況表(投票率層級),沒有候選人明細**;立委、議員等的候選人得票藏在 PDF。
- 政黨得票統計、候選人/當選人資歷統計 → 全在 PDF(階段 C,尚未處理)。

## 禮貌爬取

`scrape_html.py` 每次真實連網間隔 1.2 秒,並快取結果。請勿移除延遲或併發轟炸這台學術單位老主機。
