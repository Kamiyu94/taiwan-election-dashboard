# 政大選舉資料庫 爬取與資料集

來源:政治大學選舉研究中心「歷屆公職選舉資料庫」
<https://vote.nccu.edu.tw/cec/cechead.asp>(Big5 編碼的古典 ASP 站,無反爬)

## 檔案

| 檔案 | 說明 |
|------|------|
| `parse_index.py` | 階段 A:解析主索引頁 → `index.csv` |
| `scrape_html.py` | 階段 B:依索引逐場抓概況表 / 得票明細 → 兩張 CSV |
| `build_dashboard.py` | 階段 B+:把明細打包成互動儀表板 → `dashboard.html` |
| `index.csv` | 105 場選舉(1992–2024)的連結索引 |
| `overview_turnout.csv` | **選舉概況**(地區層級投票率/票數),504 列 |
| `detail_candidates.csv` | **候選人得票明細**(候選人層級),724 列 |
| `dashboard.html` | **單一檔互動儀表板**,雙擊用瀏覽器開即可 |
| `vendor/chart.umd.min.js` | 圖表函式庫(打包進 dashboard.html 用) |
| `cache/` | 原始 HTML 快取(重跑不重打伺服器,可刪) |

## 互動儀表板

直接雙擊 `dashboard.html`(免安裝、免網路、免伺服器)。可勾選:

- **選舉類別 / 年度 / 政黨 / 地區**(多選,可交叉)、**當選與否**、**候選人姓名搜尋**
- 即時更新:KPI(場次/候選人數/總得票/當選席次)、各政黨總得票數、各政黨當選席次、
  各政黨得票佔比趨勢(折線)、可排序的候選人明細表

資料異動後重建:`python3 build_dashboard.py`

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
