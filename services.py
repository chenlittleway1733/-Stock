"""
外部資料與模型服務層：
yfinance、Fugle、FinMind、Yahoo、Gemini 等 API 存取都集中在這裡。
由原始 app(1).py 拆分而來，已全面升級為最新的 google-genai 官方 SDK。
"""
import datetime
import io
import json
import math
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# 新增 Google 官方 GenAI SDK 引入
from google import genai
from google.genai import types

# 從 utils 引入需要的工具
from utils import s_float, log_data_health

# ==========================================
# 3. 外部 API 與模型模組
# ==========================================
def fetch_fugle_kline(stock_id, api_key, timeframe="D"):
    if not api_key: return pd.DataFrame()
    today = datetime.date.today()
    if timeframe in ["60", "30", "15"]: from_date = (today - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
    else: from_date = (today - datetime.timedelta(days=365*5)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{stock_id}?timeframe={timeframe}&from={from_date}&to={to_date}"
    headers = {"X-API-KEY": api_key.strip()}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            log_data_health("Fugle", True, res.status_code)
            data = res.json().get('data', [])
            if data:
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['date'])
                df.set_index('Date', inplace=True)
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                return df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
            else:
                log_data_health("Fugle", False, res.status_code)
    except: pass

    return pd.DataFrame()

# ==========================================
# 3.1 ETF 持股曝險追蹤（系統抓取，不使用 AI）
# ==========================================
def _normalize_etf_code(code):
    """ETF 代號標準化：支援 00987A / 00987a / 0050。"""
    if code is None:
        return ""
    return str(code).strip().upper().replace(".TW", "")


def _normalize_etf_holders(rows, default_source="系統抓取"):
    """將不同來源抓到的 ETF 持股資料統一欄位，並去重。"""
    normalized = []
    seen = set()
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        code = _normalize_etf_code(r.get("etf_code") or r.get("code") or r.get("id"))
        name = str(r.get("etf_name") or r.get("name") or "").strip()
        if not code:
            continue

        weight = r.get("weight")
        try:
            if isinstance(weight, str):
                weight = weight.replace("%", "").replace(",", "").strip()
            weight = float(weight) if weight not in (None, "", "null") else None
            # AI 偶爾會回傳 0.0685，畫面統一顯示為 6.85
            if weight is not None and 0 < abs(weight) <= 1:
                weight = weight * 100
        except Exception:
            weight = None

        shares = r.get("shares") or r.get("holding_shares") or r.get("持有股數")
        data_date = str(r.get("data_date") or r.get("date") or r.get("資料日期") or "").strip()
        source = str(r.get("source") or default_source).strip()
        data_type = str(r.get("data_type") or default_source).strip()
        note = str(r.get("note") or r.get("備註") or "").strip()

        key = code
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "etf_code": code,
            "etf_name": name,
            "weight": weight,
            "shares": shares,
            "data_date": data_date,
            "source": source,
            "data_type": data_type,
            "note": note,
        })

    normalized.sort(key=lambda x: (x.get("weight") is None, -(x.get("weight") or 0)))
    return normalized


def _extract_etf_holders_from_text(raw_text, source_name):
    """
    從 Yahoo / FindBillion 等頁面的 HTML 或嵌入 JSON 文字中，盡量抽取 ETF 代號、名稱、持股比例。
    注意：這是備援式解析，網站改版時仍可能失效，因此 UI 會明確標示資料來源與限制。
    """
    if not raw_text:
        return []

    text = re.sub(r"\\u002F", "/", raw_text)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"&quot;|&#34;", '"', text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    rows = []

    # 先抓常見格式：ETF中文名稱 00987A ... 6.85%
    # 名稱長度設寬一點，避免抓到整段敘述；後面再清洗。
    pattern = re.compile(r"([\u4e00-\u9fffA-Za-z0-9\-＋+（）()·\.]{2,32})\s*(00\d{2,3}[A-Z]?)\s{0,20}(.{0,120}?)(\d{1,2}(?:\.\d{1,4})?)\s*%", re.I)
    for m in pattern.finditer(text):
        name = m.group(1).strip(" ：:-｜|,，。")
        code = _normalize_etf_code(m.group(2))
        weight = m.group(4)
        if not code or not name:
            continue
        if any(bad in name for bad in ["http", "Yahoo", "FindBillion", "資料", "持有"]):
            # 若名稱被抓太長，取最後一段可能的 ETF 名稱
            name = re.split(r"[：:｜|，,。\s]", name)[-1].strip()
        rows.append({
            "etf_code": code,
            "etf_name": name,
            "weight": weight,
            "source": source_name,
            "data_type": "系統抓取",
        })

    # 另外抓 JSON 常見 key-value 格式，例如 symbol/name/weight 分散在附近。
    code_pat = re.compile(r'"(?:symbol|code|etfCode|stockNo|id)"\s*:\s*"?(00\d{2,3}[A-Z]?)"?', re.I)
    for m in code_pat.finditer(text):
        start = max(0, m.start() - 250)
        end = min(len(text), m.end() + 350)
        block = text[start:end]
        code = _normalize_etf_code(m.group(1))
        name_match = re.search(r'"(?:name|etfName|stockName|shortName)"\s*:\s*"([^"{}]{2,40})"', block, re.I)
        weight_match = re.search(r'"(?:weight|holdingRatio|ratio|percent|shareholding)"\s*:\s*"?(-?\d+(?:\.\d+)?)"?', block, re.I)
        rows.append({
            "etf_code": code,
            "etf_name": name_match.group(1).strip() if name_match else "",
            "weight": weight_match.group(1) if weight_match else None,
            "source": source_name,
            "data_type": "系統抓取",
        })

    return _normalize_etf_holders(rows, default_source="系統抓取")


@st.cache_data(ttl=86400)
def get_stock_etf_holders(stock_id):
    """
    查詢「哪些 ETF 持有此股票」。
    重要：此函式只使用公開網頁資料源，不呼叫 AI；AI 補查只會在 get_financials_from_ai() 被按鈕觸發時執行。
    回傳格式：
    [{etf_code, etf_name, weight, shares, data_date, source, data_type, note}]
    """
    stock_id = str(stock_id).strip()
    if not stock_id:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    sources = [
        ("Yahoo股市", f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/etf"),
        ("FindBillion", f"https://www.findbillion.com/twstock/{stock_id}/etf"),
    ]

    best_rows = []
    for source_name, url in sources:
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200 or not res.text:
                log_data_health(source_name, False, res.status_code)
                continue
            rows = _extract_etf_holders_from_text(res.text, source_name)
            if rows:
                log_data_health(source_name, True, res.status_code)
                for r in rows:
                    r["source_url"] = url
                # 取資料較多者；若 Yahoo 有資料優先直接用 Yahoo。
                if not best_rows or len(rows) > len(best_rows) or source_name == "Yahoo股市":
                    best_rows = rows
                if source_name == "Yahoo股市" and len(rows) >= 3:
                    break
            else:
                log_data_health(source_name, False, "NO_ETF_ROWS")
        except Exception as e:
            log_data_health(source_name, False, f"ERR:{str(e)[:80]}")

    return _normalize_etf_holders(best_rows, default_source="系統抓取")[:20]



# ==========================================
# 3.2 ETF 成分股快取反查（v4：MoneyDJ/Pocket/TWSE；一般查詢不使用 AI / 不用 Google）
# ==========================================
ETF_CACHE_DIR = ".etf_cache"
ETF_MASTER_CACHE_FILE = os.path.join(ETF_CACHE_DIR, "etf_master_list.json")
ETF_HOLDINGS_CACHE_FILE = os.path.join(ETF_CACHE_DIR, "etf_holdings_cache.json")
ETF_CACHE_VERSION = "v8.0-regex-fallback-holdings-cache"
ETF_SEED_CUTOFF_DATE = "2026-05-14"

# 這是「保底種子清單」：避免 TWSE / 外部清單抓不到時漏掉主動式 ETF。
# 新 ETF 仍會盡量由 discover_etf_master_list() 從公開頁面補進來。
ETF_SEED_LIST = [
    ("0050", "元大台灣50"), ("0051", "元大中型100"), ("0052", "富邦科技"),
    ("0053", "元大電子"), ("0056", "元大高股息"), ("0057", "富邦摩台"),
    ("006208", "富邦台50"), ("00690", "兆豐藍籌30"), ("00692", "富邦公司治理"),
    ("00701", "國泰股利精選30"), ("00713", "元大台灣高息低波"), ("00728", "第一金工業30"),
    ("00730", "富邦臺灣優質高息"), ("00733", "富邦臺灣中小"), ("00735", "國泰臺韓科技"),
    ("00736", "國泰新興市場"), ("00850", "元大臺灣ESG永續"), ("00878", "國泰永續高股息"),
    ("00881", "國泰台灣5G+"), ("00891", "中信關鍵半導體"), ("00892", "富邦台灣半導體"),
    ("00900", "富邦特選高股息30"), ("00904", "新光臺灣半導體30"), ("00905", "FT臺灣Smart"),
    ("00907", "永豐優息存股"), ("00912", "中信臺灣智慧50"), ("00913", "兆豐台灣晶圓製造"),
    ("00915", "凱基優選高股息30"), ("00919", "群益台灣精選高息"), ("00922", "國泰台灣領袖50"),
    ("00923", "群益台ESG低碳50"), ("00927", "群益半導體收益"), ("00929", "復華台灣科技優息"),
    ("00932", "兆豐永續高息等權"), ("00934", "中信成長高股息"), ("00939", "統一台灣高息動能"),
    ("00940", "元大台灣價值高息"), ("00944", "野村趨勢動能高息"), ("00946", "群益科技高息成長"),
    ("00952", "凱基台灣AI50"), ("00980A", "主動野村臺灣優選"), ("00981A", "主動統一台股增長"),
    ("00982A", "主動群益台灣強棒"), ("00983A", "主動中信ARK創新"), ("00984A", "主動安聯台灣高息"),
    ("00985A", "主動野村台灣50"), ("00986A", "主動群益科技創新"), ("00987A", "主動台新優勢成長"),
    ("00988A", "主動統一台股優"), ("00989A", "主動復華未來50"), ("00990A", "主動野村全球航運"),
    ("00400A", "主動國泰動能高息"), ("00403A", "主動統一台灣科技"),
]


def _today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def _ensure_etf_cache_dir():
    os.makedirs(ETF_CACHE_DIR, exist_ok=True)


def _read_json_file(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json_file(path, data):
    _ensure_etf_cache_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _flatten_columns(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(x) for x in c if str(x) != "nan"]).strip() for c in df.columns]
    else:
        df.columns = [str(c).strip() for c in df.columns]
    return df


def _clean_percent_to_float(v):
    if v is None:
        return None
    try:
        s = str(v).strip().replace("％", "%").replace("%", "").replace(",", "")
        if s in ["", "--", "-", "N/A", "nan", "None"]:
            return None
        x = float(s)
        # 有些來源用 0.0968 表示 9.68%，統一轉為百分比數字。
        if 0 < abs(x) <= 1:
            x *= 100
        return x
    except Exception:
        return None

def _normalize_tw_name(name):
    """把股票/ETF 名稱做最小清洗，方便由名稱反查代號。"""
    s = str(name or "").strip()
    s = re.sub(r"\([^)]*\)|（[^）]*）", "", s)
    s = re.sub(r"\s+", "", s)
    s = s.replace("臺", "台")
    return s


@st.cache_data(ttl=86400, show_spinner=False)
def _load_local_stock_name_code_map():
    """
    建立『股票名稱 → 股票代號』對照。
    MoneyDJ / Pocket 的 ETF 成分股表有時只有股票名稱、沒有 2330 這種代號；
    若不做名稱反查，快取就會是 0 筆或漏掉 00981A → 台積電。
    """
    mapping = {
        "台積電": "2330", "聯發科": "2454", "鴻海": "2317", "台達電": "2308",
        "廣達": "2382", "緯穎": "6669", "奇鋐": "3017", "雙鴻": "3324",
        "金像電": "2368", "台光電": "2383", "台燿": "6274", "欣興": "3037",
        "南電": "8046", "日月光投控": "3711", "聯電": "2303", "中華電": "2412",
        "富邦金": "2881", "國泰金": "2882", "兆豐金": "2886", "中信金": "2891",
        "元大金": "2885", "玉山金": "2884", "第一金": "2892", "華南金": "2880",
        "統一": "1216", "長榮": "2603", "陽明": "2609", "萬海": "2615",
        "大立光": "3008", "世芯-KY": "3661", "創意": "3443", "智原": "3035",
    }

    # 從你的 stocklist.txt 補充更多自選/產業鏈股票名稱。
    for path in ["stocklist.txt", os.path.join(os.getcwd(), "stocklist.txt")]:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "," not in line:
                        continue
                    parts = [x.strip() for x in line.split(",")]
                    if len(parts) >= 2 and re.fullmatch(r"\d{4}", parts[0]):
                        mapping[_normalize_tw_name(parts[1])] = parts[0]
        except Exception:
            pass

    return {_normalize_tw_name(k): str(v) for k, v in mapping.items() if k and v}


def _infer_stock_name_from_row(vals, stock_code=""):
    """從表格列中猜測成分股名稱。"""
    candidates = []
    for v in vals:
        s = str(v or "").strip()
        if not s or s.lower() in ["nan", "none"]:
            continue
        if any(bad in s for bad in ["投資比例", "持股比例", "持有股數", "股票代號", "證券代號", "合計", "小計", "ETF"]):
            continue
        if stock_code and stock_code in s:
            # 台積電(2330.TW) 這種格式，先取代號前的名稱。
            m = re.search(r"([\u4e00-\u9fffA-Za-z0-9\-＋+·]{2,30})\s*[\(（]?" + re.escape(stock_code), s)
            if m:
                return m.group(1).strip()
            continue
        if re.search(r"[\u4e00-\u9fff]", s):
            # 避免拿到整段很長的說明。
            s = re.split(r"[\s　,，|｜]", s)[0].strip()
            if 1 < len(s) <= 30:
                candidates.append(s)
    return candidates[0] if candidates else ""


def _extract_stock_code_from_row(row_text, vals, stock_name=""):
    """優先從文字抓 4 碼代號；抓不到時，用名稱對照表反查。"""
    m_code = re.search(r"(?<!\d)(\d{4})(?:\.TW|\s|$|\)|）|　|,|，|/)", row_text)
    if m_code:
        return m_code.group(1)

    name_map = _load_local_stock_name_code_map()
    possible_names = []
    if stock_name:
        possible_names.append(stock_name)
    for v in vals:
        sv = str(v or "").strip()
        if re.search(r"[\u4e00-\u9fff]", sv):
            possible_names.append(sv)

    for nm in possible_names:
        key = _normalize_tw_name(nm)
        if key in name_map:
            return name_map[key]
        # 有時儲存格包含「台積電 普通股」或「台積電(2330)」這類字串。
        for k, code in name_map.items():
            if k and k in key:
                return code
    return ""


def _extract_data_date_from_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text))
    patterns = [
        r"(?:資料日期|資料時間|更新日期|更新時間|持股日期|成分股日期|基準日|截至|日期)[:：\s]*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s*(?:資料|更新|持股|成分股|基準日)",
        r"(\d{3}[/-]\d{1,2}[/-]\d{1,2})",  # 民國年格式，先原樣保留
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).replace("/", "-")
    return ""


def _request_html(url, timeout=15):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
    }
    res = requests.get(url, headers=headers, timeout=timeout)
    res.raise_for_status()
    # MoneyDJ 有時編碼不是 UTF-8，交給 requests 判斷。
    if not res.encoding or res.encoding.lower() == "iso-8859-1":
        res.encoding = res.apparent_encoding or "utf-8"
    return res.text


def discover_etf_master_list(force=False):
    """
    建立 ETF 主清單：
    1) 先讀快取；
    2) 盡量從公開資料源補 ETF 代號；
    3) 失敗時至少使用 ETF_SEED_LIST，避免 00981A 這類主動式 ETF 漏掉。
    """
    cached = _read_json_file(ETF_MASTER_CACHE_FILE, {})
    if (not force) and cached.get("updated_date") == _today_str() and cached.get("items"):
        return cached.get("items", [])

    items = {code.upper(): {"etf_code": code.upper(), "etf_name": name, "source": "seed"} for code, name in ETF_SEED_LIST}

    # 嘗試從 TWSE OpenAPI / 公開列表補充。不同時期 endpoint 可能調整；失敗不阻斷主流程。
    candidate_urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX",
        "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
    ]
    for url in candidate_urls:
        try:
            data = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}).json()
            if not isinstance(data, list):
                continue
            for row in data:
                if not isinstance(row, dict):
                    continue
                txt = " ".join([str(v) for v in row.values()])
                # 台股 ETF 常見代號：00xxx / 00xxxA / 004xxA / 006xxL 等
                m = re.search(r"\b(00\d{2,4}[A-Z]?)\b", txt, re.I)
                if not m:
                    continue
                code = m.group(1).upper()
                if not code.startswith("00"):
                    continue
                # 嘗試從欄位名稱找中文名稱
                name = ""
                for k, v in row.items():
                    ks = str(k)
                    if any(x in ks for x in ["名稱", "股票名稱", "有價證券名稱", "基金"]):
                        name = str(v).strip()
                        break
                if not name:
                    name = items.get(code, {}).get("etf_name", "")
                items[code] = {"etf_code": code, "etf_name": name, "source": "TWSE/OpenAPI"}
        except Exception:
            continue

    result = sorted(items.values(), key=lambda x: x.get("etf_code", ""))
    _write_json_file(ETF_MASTER_CACHE_FILE, {
        "version": ETF_CACHE_VERSION,
        "updated_date": _today_str(),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "seed_cutoff_date": ETF_SEED_CUTOFF_DATE,
        "count": len(result),
        "source_counts": {src: sum(1 for x in result if x.get("source") == src) for src in sorted(set(x.get("source", "未知") for x in result))},
        "note": f"內建種子清單包含 {ETF_SEED_CUTOFF_DATE} 前已知上市 ETF；可按鈕重新從 TWSE/OpenAPI 補抓新上市或漏收 ETF。",
        "items": result,
    })
    return result


def _parse_holdings_text_regex_fallback(html, etf_code, etf_name, source, source_url, data_date=""):
    """
    v8：MoneyDJ / CMoney / Pocket 有些頁面雖然文字裡有成分股，
    但 pandas.read_html 在 Streamlit Cloud 可能因 lxml/bs4 或表格格式失敗，
    因此再用純文字 regex 補抓。
    常見格式：台積電(2330.TW) 9.68 11,657,000.00
    或：2330 台積電 9.23%
    """
    if not html:
        return []
    text = str(html)
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;|&#34;", '"', text)
    text = re.sub(r"\s+", " ", text)

    rows = []
    # MoneyDJ：台積電(2330.TW) 9.68 11,657,000.00
    pat_name_code = re.compile(
        r"([\u4e00-\u9fffA-Za-z0-9\-＋+＊*·]{1,32})\s*[\(（]\s*(\d{4})\.TW\s*[\)）]\s*[,，\s]*(-?\d{1,3}(?:\.\d{1,4})?)\s*%?\s*[,，\s]*([0-9,]+(?:\.\d+)?)?",
        re.I
    )
    for m in pat_name_code.finditer(text):
        stock_name = m.group(1).strip()
        stock_code = m.group(2).strip()
        weight = _clean_percent_to_float(m.group(3))
        shares = (m.group(4) or "").strip() or None
        if not stock_name or not stock_code:
            continue
        rows.append({
            "etf_code": etf_code.upper(),
            "etf_name": etf_name,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight": weight,
            "shares": shares,
            "data_date": data_date,
            "source": source,
            "source_url": source_url,
            "data_type": "系統抓取",
            "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parse_method": "regex_name_code",
        })

    # CMoney / Pocket 常見：2330 台積電 9.23%
    pat_code_name = re.compile(
        r"(?<!\d)(\d{4})(?!\d)\s+([\u4e00-\u9fffA-Za-z0-9\-＋+＊*·]{1,32})\s+(-?\d{1,3}(?:\.\d{1,4})?)\s*%",
        re.I
    )
    for m in pat_code_name.finditer(text):
        stock_code = m.group(1).strip()
        stock_name = m.group(2).strip()
        weight = _clean_percent_to_float(m.group(3))
        if not stock_name or not stock_code:
            continue
        rows.append({
            "etf_code": etf_code.upper(),
            "etf_name": etf_name,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight": weight,
            "shares": None,
            "data_date": data_date,
            "source": source,
            "source_url": source_url,
            "data_type": "系統抓取",
            "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parse_method": "regex_code_name",
        })

    return rows


def _dedup_holding_rows(rows):
    dedup = {}
    for r in rows or []:
        stock_key = str(r.get("stock_code") or "").strip()
        if not stock_key:
            stock_key = _normalize_tw_name(r.get("stock_name", ""))
        key = (str(r.get("etf_code", "")).upper(), stock_key)
        if not key[0] or not stock_key:
            continue
        old = dedup.get(key)
        if old is None or (old.get("weight") is None and r.get("weight") is not None):
            dedup[key] = r
    return list(dedup.values())


def _parse_holdings_tables_from_html(html, etf_code, etf_name, source, source_url):
    """
    解析 MoneyDJ / Pocket / 其他 HTML 表格。
    v8 重點：
    - pandas.read_html 失敗時不直接放棄，改用 regex 從 HTML 純文字補抓。
    - 不再假設表格一定有 4 碼股票代號；有名稱也保留。
    """
    rows = []
    data_date = _extract_data_date_from_text(html)
    try:
        tables = pd.read_html(io.StringIO(html))
    except Exception:
        tables = []

    name_code_map = _load_local_stock_name_code_map()

    for df in tables:
        if df is None or df.empty:
            continue
        df = _flatten_columns(df)
        df = df.fillna("")
        full_text = " ".join(df.astype(str).head(120).values.ravel().tolist())
        col_text = " ".join([str(c) for c in df.columns])
        table_text = full_text + " " + col_text

        # MoneyDJ 有時欄名很簡短；只要表格像成分股/持股表，就嘗試解析。
        looks_like_holding_table = any(k in table_text for k in [
            "投資比例", "持股", "權重", "比例", "成分股", "股票代號", "證券代號", "持有股數", "名稱"
        ])
        has_known_stock_name = any(k in table_text for k in list(name_code_map.keys())[:80])
        if not looks_like_holding_table and not has_known_stock_name:
            continue

        for _, r in df.iterrows():
            vals = [str(v).strip() for v in list(r.values) if str(v).strip() not in ["", "nan", "None"]]
            if not vals:
                continue
            row_text = " ".join(vals)
            if any(x in row_text for x in ["投資區域", "產業", "資產配置", "合計", "小計", "現金", "期貨", "基金淨資產"]):
                continue

            # 先猜名稱，再由名稱/文字找代號。
            stock_name = _infer_stock_name_from_row(vals)
            stock_code = _extract_stock_code_from_row(row_text, vals, stock_name)

            # v7：不要強制要求 ETF 成分股列一定有股票代號。
            # 因為 MoneyDJ / Pocket 有時只提供「台積電」這種成分股名稱；
            # 個股頁目前已經知道 curr_id 與 c_name，所以反查時可直接用名稱比對。
            if not stock_code and not stock_name:
                continue
            if stock_code and stock_code == str(etf_code)[:4]:
                # 避免把 ETF 自己誤判為成分股。
                continue
            if not stock_name:
                stock_name = _infer_stock_name_from_row(vals, stock_code)

            weight = None
            # 優先從欄名含比例/權重/持股的欄位取。
            for c in df.columns:
                if any(k in str(c) for k in ["投資比例", "持股比例", "權重", "比例", "%"]):
                    weight = _clean_percent_to_float(r.get(c))
                    if weight is not None:
                        break
            # 再從整列抓百分比。
            if weight is None:
                m_w = re.search(r"(-?\d{1,3}(?:\.\d{1,4})?)\s*%", row_text)
                if m_w:
                    weight = _clean_percent_to_float(m_w.group(1))
            # 最後退一步：若該列有多個數字，常見最後一個小數是比例。
            if weight is None:
                nums = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{1,4})?)(?!\d)", row_text.replace(",", ""))
                for num in reversed(nums):
                    try:
                        x = float(num)
                        if 0 <= x <= 100 and num != stock_code:
                            weight = x
                            break
                    except Exception:
                        pass

            shares = None
            for c in df.columns:
                if any(k in str(c) for k in ["持有股數", "股數", "持股"]):
                    shares = str(r.get(c)).strip()
                    break

            rows.append({
                "etf_code": etf_code.upper(),
                "etf_name": etf_name,
                "stock_code": stock_code,
                "stock_name": stock_name,
                "weight": weight,
                "shares": shares,
                "data_date": data_date,
                "source": source,
                "source_url": source_url,
                "data_type": "系統抓取",
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    # v8：表格解析後，再用 regex 補抓；若 read_html 失敗，也可靠 regex 建立快取。
    rows.extend(_parse_holdings_text_regex_fallback(html, etf_code, etf_name, source, source_url, data_date=data_date))
    return _dedup_holding_rows(rows)

def fetch_moneydj_etf_holdings(etf_code, etf_name=""):
    url = f"https://www.moneydj.com/etf/x/basic/basic0007.xdjhtm?etfid={str(etf_code).lower()}.tw"
    html = _request_html(url)
    return _parse_holdings_tables_from_html(html, etf_code, etf_name, "MoneyDJ", url)


def fetch_pocket_etf_holdings(etf_code, etf_name=""):
    url = f"https://www.pocket.tw/etf/tw/{str(etf_code).upper()}/fundholding/"
    html = _request_html(url)
    return _parse_holdings_tables_from_html(html, etf_code, etf_name, "Pocket", url)


def fetch_cmoney_etf_holdings(etf_code, etf_name=""):
    url = f"https://www.cmoney.tw/etf/tw/{str(etf_code).upper()}/fundholding"
    html = _request_html(url)
    return _parse_holdings_tables_from_html(html, etf_code, etf_name, "CMoney", url)


def update_etf_holdings_cache(force=False, max_etfs=None):
    """
    更新 ETF → 成分股快取。一般查詢不使用 AI / 不用 Google。
    max_etfs 可在測試時限制掃描檔數；正式環境建議 None。
    """
    cached = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    if (not force) and cached.get("updated_date") == _today_str() and cached.get("holdings"):
        return cached

    master = discover_etf_master_list(force=force)
    if max_etfs:
        master = master[:int(max_etfs)]

    holdings = []
    errors = []
    for i, item in enumerate(master, start=1):
        code = item.get("etf_code", "").upper()
        name = item.get("etf_name", "")
        if not code:
            continue
        rows = []
        # MoneyDJ 優先；抓不到才試 Pocket。
        try:
            rows = fetch_moneydj_etf_holdings(code, name)
        except Exception as e:
            errors.append({"etf_code": code, "source": "MoneyDJ", "error": str(e)[:160]})
        if not rows:
            try:
                rows = fetch_pocket_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "Pocket", "error": str(e)[:160]})
        if not rows:
            try:
                rows = fetch_cmoney_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "CMoney", "error": str(e)[:160]})
        holdings.extend(rows)
        # 禮貌延遲，避免對外部網站造成壓力。
        time.sleep(0.25)

    cache = {
        "version": ETF_CACHE_VERSION,
        "updated_date": _today_str(),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "master_count": len(master),
        "holdings_count": len(holdings),
        "holdings": holdings,
        "errors_sample": errors[:30],
    }
    _write_json_file(ETF_HOLDINGS_CACHE_FILE, cache)
    return cache


def load_etf_holdings_cache(auto_update=True):
    cache = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    if auto_update and (cache.get("updated_date") != _today_str() or not cache.get("holdings")):
        cache = update_etf_holdings_cache(force=False)
    return cache


def update_etf_master_list_cache(force=True):
    """
    更新 ETF 主清單快取：
    - 不使用 AI、不用 Google 搜尋；
    - 以內建種子清單為底，再嘗試從 TWSE/OpenAPI 補進新上市或漏收 ETF；
    - 只更新 ETF 清單，不會抓每檔 ETF 的成分股。
    """
    discover_etf_master_list(force=force)
    return _read_json_file(ETF_MASTER_CACHE_FILE, {})


def get_etf_master_cache_status():
    master = _read_json_file(ETF_MASTER_CACHE_FILE, {})
    items = master.get("items", []) if isinstance(master.get("items"), list) else []
    active_count = 0
    for x in items:
        code = str(x.get("etf_code", "")).upper()
        name = str(x.get("etf_name", ""))
        if code.endswith("A") or "主動" in name:
            active_count += 1
    return {
        "cache_version": master.get("version", "尚未建立"),
        "updated_date": master.get("updated_date", "尚未更新"),
        "updated_at": master.get("updated_at", "尚未更新"),
        "is_today": master.get("updated_date") == _today_str(),
        "count": master.get("count", len(items)),
        "active_count": active_count,
        "seed_cutoff_date": master.get("seed_cutoff_date", ETF_SEED_CUTOFF_DATE),
        "source_counts": master.get("source_counts", {}),
        "note": master.get("note", f"內建種子清單包含 {ETF_SEED_CUTOFF_DATE} 前已知上市 ETF。"),
    }


def get_etf_cache_status():
    cache = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    master = _read_json_file(ETF_MASTER_CACHE_FILE, {})
    return {
        "cache_version": cache.get("version", "尚未建立"),
        "updated_date": cache.get("updated_date", "尚未更新"),
        "updated_at": cache.get("updated_at", "尚未更新"),
        "is_today": cache.get("updated_date") == _today_str(),
        "master_count": cache.get("master_count", master.get("count", 0)),
        "holdings_count": cache.get("holdings_count", len(cache.get("holdings", [])) if isinstance(cache.get("holdings"), list) else 0),
        "errors_count": len(cache.get("errors_sample", [])) if isinstance(cache.get("errors_sample"), list) else 0,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_etf_holders(stock_id, stock_name=None, force_refresh=False):
    """
    從 ETF 成分股快取反查「哪些 ETF 持有此股票」。
    注意：此函式一般查詢不呼叫 AI、不用 Google 搜尋。
    若快取沒有資料，才用 Yahoo/FindBillion 個股反查作為最後補漏。
    """
    stock_id = str(stock_id).strip()
    if not stock_id:
        return []

    if force_refresh:
        cache = update_etf_holdings_cache(force=True)
    else:
        cache = load_etf_holdings_cache(auto_update=True)

    holdings = cache.get("holdings", []) if isinstance(cache, dict) else []
    results = []
    target_name_key = _normalize_tw_name(stock_name or "")
    if not target_name_key:
        try:
            target_name_key = _normalize_tw_name(get_chinese_name(stock_id) or "")
        except Exception:
            target_name_key = ""

    for r in holdings:
        row_code = str(r.get("stock_code", "")).strip()
        row_name_key = _normalize_tw_name(r.get("stock_name", ""))
        if row_code == stock_id or (target_name_key and row_name_key and target_name_key == row_name_key):
            results.append({
                "etf_code": _normalize_etf_code(r.get("etf_code")),
                "etf_name": r.get("etf_name", ""),
                "weight": r.get("weight"),
                "shares": r.get("shares"),
                "data_date": r.get("data_date") or "來源未揭露",
                "source": r.get("source") or "ETF成分股快取",
                "source_url": r.get("source_url", ""),
                "data_type": "ETF成分股快取反查",
                "note": "由 ETF 持股明細反查，不是 Yahoo 個股頁結果",
            })

    # 去重：同一 ETF 若多來源重複，優先保留 MoneyDJ / 有比例者。
    pref = {"MoneyDJ": 0, "Pocket": 1, "TWSE": 2, "Yahoo股市": 3, "FindBillion": 4}
    dedup = {}
    for r in results:
        code = r.get("etf_code")
        old = dedup.get(code)
        if old is None:
            dedup[code] = r
        else:
            old_rank = pref.get(str(old.get("source")), 99)
            new_rank = pref.get(str(r.get("source")), 99)
            if (old.get("weight") is None and r.get("weight") is not None) or new_rank < old_rank:
                dedup[code] = r
    results = list(dedup.values())
    results.sort(key=lambda x: (x.get("weight") is None, -(x.get("weight") or 0)))

    if results:
        return results[:80]

    # 最後補漏：保留舊 Yahoo/FindBillion 個股頁解析，但明確標示來源。
    # 這不是主資料源，只避免快取建置失敗時完全沒資料。
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
        sources = [
            ("Yahoo股市", f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/etf"),
            ("FindBillion", f"https://www.findbillion.com/twstock/{stock_id}/etf"),
        ]
        best_rows = []
        for source_name, url in sources:
            try:
                res = requests.get(url, headers=headers, timeout=12)
                if res.status_code != 200:
                    continue
                rows = _extract_etf_holders_from_text(res.text, source_name)
                for rr in rows:
                    rr["data_date"] = rr.get("data_date") or "來源未揭露"
                    rr["data_type"] = "個股頁補漏"
                    rr["note"] = "ETF 快取未命中，改用個股頁補漏"
                if rows and (not best_rows or len(rows) > len(best_rows)):
                    best_rows = rows
            except Exception:
                continue
        return best_rows[:20]
    except Exception:
        return []

def get_financials_from_ai(stock_name, stock_id, api_key, model_name="gemini-3.1-pro-preview"):
    """
    AI 財報校對與補齊。
    v7 修正重點：
    1) 僅允許 Gemini 3 Pro Preview 付費版 + Google Search。
    2) 不自動降級到 2.5 Pro / 2.5 Flash / 離線保底，避免不準資料進入估值模型。
    3) 尖峰時段採用「同模型 Pro Only Retry」：立即重試、等待 3 秒、等待 8 秒。
    4) 全部失敗時只回傳 error 與 attempts，不產生 AI 財報數據。
    """
    if not api_key:
        return {"error": "未提供 API Key"}

    try:
        client = genai.Client(api_key=api_key.strip())
    except Exception as e:
        return {"error": f"GenAI Client 初始化失敗：{str(e)}"}

    current_year = datetime.date.today().year
    target_year = current_year if datetime.date.today().month < 9 else current_year + 1

    system_prompt = f"""你是一個精準的財經數據提取機器人。請上網搜尋該台股公司「最新」、「最即時」的財報與市場數據，絕對不要使用過期的舊資料，提取以下指標：
    1. 「歷史本益比 (P/E)」
    2. 「近四季或最新年度 EPS (Trailing EPS)」
    3. 「法人預估 {target_year} 年度 EPS (Forward EPS)」
    4. 「股價淨值比 (P/B)」
    5. 「毛利率」
    6. 「營益率」
    7. 「ROE(股東權益報酬率)」
    8. 「法人預估未來 1~3 年獲利複合成長率 (CAGR)，若無則用最新營收 YoY 替代」
    9. 「國內外法人最新預估目標價 (Target Price)」
    10. 「負債權益比 (Debt-to-Equity Ratio)」
    11. 「最新單月營收月增率(MoM)」
    12. 「預估現金殖利率 (Dividend Yield)」(例如：擬配發現金股利2元，最新股價900元，殖利率應為 0.0022)
    13. 「最新資料所屬年月或具體日期 (Data Period)」(請務必標示出你查到這些最新數據的具體發布日期或所屬時間，例如：2024年4月或2024/05/15)
    14. 「目標價統計分析師人數 (Target Price Analyst Count)」
    15. 「目標價核心理由摘要 (Target Price Rationale)」
    16. 「最新自由現金流 (Free Cash Flow)」
    17. 「最新流動比率 (Current Ratio)」
    18. 「總發行股數或股本大小 (Shares Outstanding / Capital)」
    必須嚴格回傳包含上述 18 個財務欄位的 JSON 格式。百分比請轉換為小數（例如 25.5% 寫成 0.255，衰退5%寫成 -0.05），數值請直接輸出數字。若查無資料，該欄位請填 null。
    請務必搜尋近期各大券商對該公司的最新目標價。
    注意：本函式只負責財報與估值校對，不要查詢 ETF 持股；ETF 持股由獨立按鈕 get_etf_holders_from_ai() 執行。
    JSON 格式範例：
    {{"pe": 15.2, "trailing_eps": 5.4, "forward_eps": 6.2, "pb": 2.1, "gross_margin": 0.255, "operating_margin": 0.123, "roe": 0.15, "yoy": 0.35, "target_price": 1050.0, "target_price_high": 1200.0, "target_price_avg": 1050.0, "target_price_low": 900.0, "target_price_analyst_count": 18, "target_price_rationale": "AI 伺服器需求強、毛利率改善但評價偏高", "debt_to_equity": 0.45, "mom": 0.015, "dividend_yield": 0.032, "data_period": "2024/05/15", "free_cash_flow": 1500000000, "current_ratio": 1.85, "shares_outstanding": 2500000000}}
    絕對不要輸出 markdown 標記或其他文字。"""

    prompt_text = f"請啟用搜尋引擎，【務必尋找最新日期】查詢台股 {stock_name} ({stock_id}) 最新財報新聞、營收 MoM，以及 {target_year} 法人預估未來三年複合成長率(CAGR)、預測 EPS 與最新目標價。請務必確認並標示出資料的發布日期！不要查詢 ETF 持股，ETF 持股由獨立功能處理。"

    def _make_config(search_enabled=True):
        kwargs = {
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
        }
        if search_enabled:
            kwargs["tools"] = [{"google_search": {}}]
        return types.GenerateContentConfig(**kwargs)

    def _is_non_retryable_error(err_text):
        """授權/權限/模型不存在這類錯誤，短時間重試通常無效。"""
        t = str(err_text).lower()
        fatal_keywords = [
            "api key not valid", "invalid api key", "api_key_invalid",
            "permission_denied", "permission denied", "unauthenticated",
            "401", "403", "not found", "model not found",
            "billing", "quota exceeded"
        ]
        return any(k in t for k in fatal_keywords)

    # Pro Only：只用付費版高階模型 + Google Search；不降級。
    candidate_model = "gemini-3.1-pro-preview"
    retry_delays = [0, 3, 8]
    attempts = []
    response = None
    text = None
    used_model = candidate_model
    used_search = True
    fallback_reason = ""
    last_error = None

    for idx, delay_sec in enumerate(retry_delays, start=1):
        if delay_sec > 0:
            time.sleep(delay_sec)

        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=prompt_text,
                config=_make_config(search_enabled=True)
            )
            text = response.text
            log_data_health("Gemini", True, 200)
            attempts.append({
                "attempt": idx,
                "model": candidate_model,
                "search_enabled": True,
                "delay_before_retry_sec": delay_sec,
                "ok": True,
                "reason": "Pro Only 同模型聯網重試成功" if idx > 1 else "Pro Only 付費版高階模型聯網成功"
            })
            break
        except Exception as e:
            err_msg = str(e)
            last_error = err_msg
            log_data_health("Gemini", False, f"ERR:{candidate_model}:search:try{idx}")
            attempts.append({
                "attempt": idx,
                "model": candidate_model,
                "search_enabled": True,
                "delay_before_retry_sec": delay_sec,
                "ok": False,
                "error": err_msg[:500],
                "reason": "Pro Only 付費版高階模型聯網失敗；不降級，只重試同模型"
            })
            if _is_non_retryable_error(err_msg):
                break

    if response is None or text is None:
        return {
            "error": (
                "Gemini 3 Pro Preview（付費版）聯網財報校對失敗。"
                f"系統已用同一付費模型重試 {len(attempts)} 次，仍未成功；"
                "已禁止降級到 2.5 Pro / 2.5 Flash / 離線保底，以避免不準數據進入極限高空價。"
                "請稍後再試，或檢查 API 權限、配額與模型可用狀態。"
            ),
            "last_error": str(last_error)[:500] if last_error else None,
            "attempts": attempts
        }

    if not text:
        return {
            "error": "Gemini 3 Pro Preview（付費版）回傳內容為空；系統不降級，請稍後重試。",
            "attempts": attempts
        }

    marker_match = re.search(r"\[TARGET_PRICE:\s*([^,\]]+)\s*,\s*([^,\]]+)\s*,\s*([^\]]+)\]", text)
    marker_data = {}
    if marker_match:
        marker_data = {
            "target_price_high": s_float(marker_match.group(1).replace("無", "")),
            "target_price_avg": s_float(marker_match.group(2).replace("無", "")),
            "target_price_low": s_float(marker_match.group(3).replace("無", "")),
        }

    s_idx = text.find('{')
    e_idx = text.rfind('}')
    if s_idx != -1 and e_idx != -1:
        clean_text = text[s_idx:e_idx+1]
        try:
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict):
                parsed.update({k: v for k, v in marker_data.items() if v is not None and parsed.get(k) is None})
                parsed["model_used"] = used_model
                parsed["ai_search_enabled"] = bool(used_search)
                parsed["fallback_reason"] = fallback_reason
                parsed["attempts"] = attempts
                parsed["retry_policy"] = "Pro Only：gemini-3.1-pro-preview + Google Search；最多 3 次；不降級。"
                parsed["query_payload"] = json.dumps({
                    "stock": f"{stock_name} ({stock_id})",
                    "target_year": target_year,
                    "model_used": used_model,
                    "google_search_enabled": bool(used_search),
                    "fallback_reason": fallback_reason or "無",
                    "retry_policy": "Pro Only same-model retry: delays 0s, 3s, 8s; no downgrade.",
                    "prompt": prompt_text,
                }, ensure_ascii=False, indent=2)
            return parsed
        except json.JSONDecodeError:
            return {
                "error": "AI 回傳的格式不正確，無法解析 JSON 資料。系統不降級，請稍後重試。",
                "raw_text_preview": text[:500],
                "attempts": attempts
            }
    else:
        return {
            "error": "AI 回傳的格式不正確，無法萃取 JSON 資料。系統不降級，請稍後重試。",
            "raw_text_preview": text[:500],
            "attempts": attempts
        }

@st.cache_data(ttl=86400)
def get_peers_from_ai(stock_name, stock_id, api_key):
    if not api_key: return []
    try:
        client = genai.Client(api_key=api_key.strip())
        system_prompt = "請列出與目標公司核心業務最直接競爭的 3~5 家台股上市櫃公司代號。必須是純數字 JSON 陣列格式：[\"2383\", \"3044\"]。絕對不要輸出其他文字。"
        
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=f"請尋找 {stock_name} ({stock_id}) 的同業競爭對手",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[{"google_search": {}}]
            )
        )
        log_data_health("Gemini", True, 200)
        clean_text = re.sub(r'```json\n?|```', '', response.text).strip()
        peers = json.loads(clean_text)
        if isinstance(peers, list): return [str(p) for p in peers][:4] 
    except Exception as e: 
        log_data_health("Gemini", False, str(e))
    return []

def get_ai_industry_analysis(stock_name, stock_id, api_key, context_data, model_name="gemini-3.1-pro-preview"):
    if not api_key: return "ERROR: 未輸入金鑰"
    try:
        client = genai.Client(api_key=api_key.strip())
        system_prompt = "你是一位精通台股的資深產業分析師與操盤手。請針對目標公司的最新動態提供深度分析，包含產業前景、競爭優勢、系統風險及買賣點策略。請用 Markdown 格式與 Emoji。不要輸出 HTML。"
        
        used_model = "gemini-3.1-pro-preview"
        try:
            response = client.models.generate_content(
                model=used_model,
                contents=f"請深度分析台股 {stock_name} ({stock_id})。關鍵數據：\n{context_data}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[{"google_search": {}}]
                )
            )
            log_data_health("Gemini", True, 200)
            ans = re.sub(r'```markdown\n?|```', '', response.text).strip()
            return ans
        except Exception as e:
            log_data_health("Gemini", False, f"ERR:{used_model}:search")
            return f"⚠️ Gemini 3 Pro Preview（付費版）聯網分析失敗；系統已禁止降級到 2.5 系列，以避免不準資料。細節: {str(e)}"
    except Exception as e: 
        return f"連線異常: {str(e)}"

def get_ai_analysis_final(topic, api_key, model_name="gemini-3.1-pro-preview"):
    if not api_key: return "ERROR: 未輸入金鑰", []
    try:
        client = genai.Client(api_key=api_key.strip())
        system_prompt = "你是一位精通台股產業鏈的專業分析師。請針對議題推薦 3 檔「潛力權值股」與 3 檔「中小型飆股」。必須嚴格回傳 JSON 格式：{\"reasoning\": \"...\", \"stocks\": [{\"id\": \"4位數代號\", \"name\": \"中文名稱\", \"type\": \"潛力\", \"why\": \"原因\"}]}。"
        
        used_model = "gemini-3.1-pro-preview"
        try:
            response = client.models.generate_content(
                model=used_model,
                contents=f"請深度分析台股議題：{topic}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    tools=[{"google_search": {}}]
                )
            )
            log_data_health("Gemini", True, 200)
        except Exception as e:
            log_data_health("Gemini", False, f"ERR:{used_model}:search")
            return f"Gemini 3 Pro Preview（付費版）聯網議題推演失敗；系統已禁止降級到 2.5 系列，以避免不準資料。細節：{str(e)}", []

        clean_json = re.sub(r'```json\n?|```', '', response.text).strip()
        s_idx = clean_json.find('{')
        e_idx = clean_json.rfind('}')
        if s_idx != -1 and e_idx != -1: 
            clean_json = clean_json[s_idx:e_idx+1]
        
        # 官方 SDK Grounding 資料解析方式
        links = []
        try:
            if response.candidates and response.candidates[0].grounding_metadata:
                for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        links.append(chunk.web.uri)
        except: pass
        
        return json.loads(clean_json), list(set(links))
    except Exception as e: 
        return f"連線異常: {str(e)}", []

@st.cache_data(ttl=900) 
def get_global_market_trend():
    try:
        tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        h = tw_time.hour
        
        if 14 <= h < 22:
            target_day = "明日"
            time_status = "<span style='color:gray; font-size:0.9rem;'>(美股現貨尚未開盤，此為昨夜收盤參考)</span>"
        elif h >= 22 or h < 5:
            target_day = "明日" if h >= 22 else "今日"
            time_status = "<span style='color:#00bfff; font-size:0.9rem;'>(美股現貨與台股夜盤 交易中)</span>"
        else:
            target_day = "今日"
            time_status = "<span style='color:#00cc66; font-size:0.9rem;'>(美股與夜盤已收盤，為最新結算數據)</span>"

        tickers = yf.Tickers('^SOX TSM NQ=F EWT')
        def get_price_and_pct(ticker_obj):
            try:
                hist = ticker_obj.history(period='5d')
                if len(hist) >= 2:
                    c = float(hist['Close'].iloc[-1])
                    p = float(hist['Close'].iloc[-2])
                    if not math.isnan(c) and not math.isnan(p) and p != 0: return c, (c - p) / p * 100
            except: pass
            return 0.0, 0.0

        sox_price, sox_pct = get_price_and_pct(tickers.tickers['^SOX'])
        tsm_price, tsm_pct = get_price_and_pct(tickers.tickers['TSM'])
        nq_price, nq_pct = get_price_and_pct(tickers.tickers['NQ=F'])
        ewt_price, ewt_pct = get_price_and_pct(tickers.tickers['EWT'])
        score = sox_pct * 0.3 + tsm_pct * 0.3 + nq_pct * 0.1 + ewt_pct * 0.3
        
        if score > 1.0: trend, color = f"🔥 極度樂觀 ({target_day}台股開盤強勢)", "#ff4d4d"
        elif score > 0.1: trend, color = f"📈 偏多看待 (有利{target_day}台股表現)", "#ff4d4d"
        elif score > -0.8: trend, color = f"↔️ 震盪整理 ({target_day}台股可能平盤震盪)", "#FFD700"
        else: trend, color = f"❄️ 悲觀警戒 ({target_day}台股面臨回檔壓力)", "#00cc66"
            
        return {"sox_p": sox_price, "sox": sox_pct, "tsm_p": tsm_price, "tsm": tsm_pct, "nq_p": nq_price, "nq": nq_pct, "ewt_p": ewt_price, "ewt": ewt_pct, "trend": trend, "color": color, "target_day": target_day, "time_status": time_status}
    except: return None

@st.cache_data(ttl=43200)
def get_monthly_revenue(stock_id, fm_key=""):
    try:
        y_url = f"https://tw.stock.yahoo.com/quote/{stock_id}/revenue"
        y_res = requests.get(y_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        log_data_health("Yahoo", y_res.status_code == 200, y_res.status_code)
        if y_res.status_code == 200:
            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', y_res.text)
            if json_match:
                raw_json = json.loads(json_match.group(1))
                def find_rev_list(node):
                    if isinstance(node, dict):
                        if 'yearMonth' in node and 'revenue' in node and 'monthOverMonth' in node:
                            return [node]
                        res = []
                        for k, v in node.items():
                            ext = find_rev_list(v)
                            if ext: res.extend(ext)
                        return res
                    elif isinstance(node, list):
                        res = []
                        for item in node:
                            ext = find_rev_list(item)
                            if ext: res.extend(ext)
                        return res
                    return []
                    
                rev_list = find_rev_list(raw_json)
                valid_revs = [r for r in rev_list if isinstance(r.get('yearMonth'), str) and re.match(r'\d{4}/\d{2}', r.get('yearMonth'))]
                
                if valid_revs:
                    valid_revs.sort(key=lambda x: x['yearMonth'], reverse=True)
                    latest = valid_revs[0]
                    mon = latest.get('yearMonth')
                    
                    def get_raw(field):
                        val = latest.get(field)
                        if isinstance(val, dict): return val.get('raw', 0)
                        return float(val) if val is not None else 0
                        
                    rev_raw = get_raw('revenue')
                    yoy_raw = get_raw('yearOverYear')
                    mom_raw = get_raw('monthOverMonth')
                    
                    if mon and rev_raw:
                        return pd.DataFrame([{
                            'Month': mon, 
                            'Revenue': round(rev_raw / 100000000, 2), 
                            'YoY': round(yoy_raw * 100, 2), 
                            'MoM': round(mom_raw * 100, 2)
                        }])
    except: pass
    
    try:
        today = datetime.date.today()
        start_str = f"{today.year - 2}-{today.month:02d}-01"
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id={stock_id}&start_date={start_str}"
        if fm_key: url += f"&token={fm_key}" 
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        ok = (res.status_code == 200)
        status_val = res.status_code
        data = res.json()
        ok = ok and data.get('status') == 200
        log_data_health("FinMind", ok, status_val)
        if data.get('status') == 200 and data.get('data'):
            df = pd.DataFrame(data['data'])
            df['date'] = pd.to_datetime(df['date'])
            current_month_start = pd.to_datetime(f"{today.year}-{today.month:02d}-01")
            df = df[df['date'] < current_month_start].sort_values('date').reset_index(drop=True)
            df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce')
            if 'revenue_year_on_year_growth' in df.columns: df['YoY'] = pd.to_numeric(df['revenue_year_on_year_growth'], errors='coerce')
            else: df['YoY'] = df['revenue'].pct_change(periods=12) * 100
            df['MoM'] = df['revenue'].pct_change(periods=1) * 100
            df['Month'] = df['date'].dt.strftime('%Y/%m')
            df['Revenue'] = df['revenue'] / 100000000 
            final_df = df.dropna(subset=['YoY']).tail(12).copy()
            if not final_df.empty:
                final_df['Revenue'] = final_df['Revenue'].round(2)
                final_df['YoY'] = final_df['YoY'].round(2)
                final_df['MoM'] = final_df['MoM'].round(2)
                return final_df[['Month', 'Revenue', 'YoY', 'MoM']].reset_index(drop=True)
    except: pass
    return None

@st.cache_data(ttl=43200)
def get_pe_pb_data(stock_id, fm_key=""):
    try:
        today = datetime.date.today()
        start_str = f"{today.year - 5}-{today.month:02d}-01"
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPER&data_id={stock_id}&start_date={start_str}"
        if fm_key: url += f"&token={fm_key}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 200 and data.get('data'): 
                df = pd.DataFrame(data['data'])
                df['date'] = pd.to_datetime(df['date'])
                df['PER'] = pd.to_numeric(df['PER'], errors='coerce')
                df['PBR'] = pd.to_numeric(df.get('PBR'), errors='coerce') 
                return df[df['PER'] > 0].dropna(subset=['date', 'PER']).reset_index(drop=True)
    except: pass
    return None

@st.cache_data(ttl=43200)
def get_finmind_financial_health(stock_id, fm_key=""):
    try:
        today = datetime.date.today()
        start_str = f"{today.year - 2}-01-01" 
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockFinancialStatements&data_id={stock_id}&start_date={start_str}"
        if fm_key: url += f"&token={fm_key}"
        res = requests.get(url, timeout=15)
        data = res.json()
        if data.get('status') == 200 and data.get('data'):
            df = pd.DataFrame(data['data'])
            if df.empty: return {}
            
            df['date'] = pd.to_datetime(df['date'])
            dates = sorted(df['date'].unique())
            latest_date = dates[-1]
            prev_date = dates[-5] if len(dates) >= 5 else (dates[0] if len(dates)>1 else latest_date)
            
            df_latest = df[df['date'] == latest_date]
            df_prev = df[df['date'] == prev_date]
            
            vals_l = dict(zip(df_latest['type'].astype(str).str.strip(), df_latest['value']))
            vals_p = dict(zip(df_prev['type'].astype(str).str.strip(), df_prev['value']))
            
            def get_val(v_dict, *keys):
                for k in keys:
                    for v_key in v_dict.keys():
                        if k in v_key:
                            try: return float(str(v_dict[v_key]).replace(',', '').replace('%', ''))
                            except: pass
                return 0.0
                
            rev_l = get_val(vals_l, '營業收入', '淨收益', '收益')
            gp_l = get_val(vals_l, '營業毛利', '毛利')
            op_l = get_val(vals_l, '營業利益')
            ni_l = get_val(vals_l, '本期淨利', '淨利')
            ta_l = get_val(vals_l, '資產總計', '資產總額', '資產')
            tl_l = get_val(vals_l, '負債總')
            eq_l = get_val(vals_l, '權益總')
            ca_l = get_val(vals_l, '流動資產')
            cl_l = get_val(vals_l, '流動負債')
            ltd_l = get_val(vals_l, '非流動負債', '長期借款')
            cfo_l = get_val(vals_l, '營業活動之淨現金流入', '營業活動之現金流量', '營業活動之淨現金')
            if cfo_l == 0: cfo_l = op_l 
            shares_l = get_val(vals_l, '普通股股本', '股本')
            
            rev_p = get_val(vals_p, '營業收入', '淨收益', '收益')
            gp_p = get_val(vals_p, '營業毛利', '毛利')
            ni_p = get_val(vals_p, '本期淨利', '淨利')
            ta_p = get_val(vals_p, '資產總計', '資產總額', '資產')
            ca_p = get_val(vals_p, '流動資產')
            cl_p = get_val(vals_p, '流動負債')
            ltd_p = get_val(vals_p, '非流動負債', '長期借款')
            shares_p = get_val(vals_p, '普通股股本', '股本')
            
            if ta_l <= 0 or ta_p <= 0: return {}

            res_dict = {}
            if rev_l > 0:
                res_dict['grossMargins'] = gp_l / rev_l
                res_dict['operatingMargins'] = op_l / rev_l
            if eq_l > 0: res_dict['debtToEquity'] = tl_l / eq_l
                
            f_score = 0
            if ta_l > 0 and ta_p > 0:
                roa_l, roa_p = ni_l / ta_l, ni_p / ta_p
                if roa_l > 0: f_score += 1                 
                if cfo_l > 0: f_score += 1                 
                if roa_l > roa_p: f_score += 1             
                if cfo_l > ni_l: f_score += 1              
                if (ltd_l / ta_l) < (ltd_p / ta_p): f_score += 1  
                cr_l = (ca_l / cl_l) if cl_l > 0 else 0
                cr_p = (ca_p / cl_p) if cl_p > 0 else 0
                if cr_l > cr_p: f_score += 1               
                if shares_l <= shares_p and shares_l > 0: f_score += 1 
                gm_l = (gp_l / rev_l) if rev_l > 0 else 0
                gm_p = (gp_p / rev_p) if rev_p > 0 else 0
                if gm_l > gm_p: f_score += 1               
                at_l = rev_l / ta_l
                at_p = rev_p / ta_p
                if at_l > at_p: f_score += 1               
                
            res_dict['f_score'] = f_score
            res_dict['cfo_l'] = cfo_l
            return res_dict
    except: pass
    return {}

@st.cache_data(ttl=1800)
def get_stock_news(stock_id):
    news_data = []
    
    try:
        query = f"{stock_id} 台股 (財報 OR 法說會 OR 營收 OR 盈餘 OR EPS)"
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            import email.utils
            root = ET.fromstring(res.text)
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                source = item.find('source').text if item.find('source') is not None else "Google News"
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                timestamp = 0
                if pubDate:
                    try:
                        parsed_date = email.utils.parsedate_tz(pubDate)
                        if parsed_date:
                            timestamp = int(email.utils.mktime_tz(parsed_date))
                    except: pass
                    
                news_data.append({
                    "title": title,
                    "publisher": source,
                    "link": link,
                    "timestamp": timestamp
                })
    except: pass

    if not news_data:
        for ext in [".TW", ".TWO"]:
            try:
                ticker = yf.Ticker(f"{stock_id}{ext}")
                news = ticker.news
                if news:
                    for n in news:
                        title = n.get("title", "")
                        if any(kw in title for kw in ["財報", "法說", "營收", "EPS", "盈餘", "季報", "年報", "獲利"]):
                            news_data.append({
                                "title": title,
                                "publisher": n.get("publisher", ""),
                                "link": n.get("link", ""),
                                "timestamp": n.get("providerPublishTime", 0)
                            })
                    break 
            except: pass
            
    if news_data:
        news_data.sort(key=lambda x: x["timestamp"], reverse=True)
        return news_data[:5]
    return []

def get_fallback_info(stock_id):
    info = {}
    for ext in [".TW", ".TWO"]:
        try:
            tk = yf.Ticker(f"{stock_id}{ext}")
            fi = tk.fast_info
            if 'last_price' in fi:
                info['realtime_price'] = fi['last_price']
                info['realtime_prev_close'] = fi.get('previous_close')
                info['realtime_open'] = fi.get('open')
                info['realtime_high'] = fi.get('day_high')
                info['realtime_low'] = fi.get('day_low')
                info['realtime_volume'] = fi.get('last_volume')
                break
        except: pass
        
    try:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        text = res.text
        
        json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text)
        if json_match:
            data = json.loads(json_match.group(1))
            keys_to_find = ['peRatio', 'trailingPE', 'pbRatio', 'priceToBook', 'eps', 'trailingEps', 'dividendYield', 'targetHighPrice', 'targetMeanPrice', 'targetLowPrice', 'grossMargins', 'operatingMargins', 'returnOnEquity']
            found_data = {}
            
            def find_keys(node):
                if isinstance(node, dict):
                    for k, v in node.items():
                        if k in keys_to_find:
                            if isinstance(v, dict) and 'raw' in v:
                                found_data[k] = v['raw']
                            elif isinstance(v, (int, float)):
                                found_data[k] = v
                        find_keys(v)
                elif isinstance(node, list):
                    for item in node:
                        find_keys(item)
                        
            find_keys(data)
            
            info['trailingPE'] = found_data.get('peRatio') or found_data.get('trailingPE')
            info['priceToBook'] = found_data.get('pbRatio') or found_data.get('priceToBook')
            info['trailingEps'] = found_data.get('eps') or found_data.get('trailingEps')
            info['dividendYield'] = found_data.get('dividendYield')
            info['targetHighPrice'] = found_data.get('targetHighPrice')
            info['targetMeanPrice'] = found_data.get('targetMeanPrice')
            info['targetLowPrice'] = found_data.get('targetLowPrice')
            info['grossMargins'] = found_data.get('grossMargins')
            info['operatingMargins'] = found_data.get('operatingMargins')
            info['returnOnEquity'] = found_data.get('returnOnEquity')
            
        sec_match = re.search(r'href="/class-quote\?category=([^"&]+)', text)
        if sec_match: info['sector'] = urllib.parse.unquote(sec_match.group(1))
    except: pass
    return info

@st.cache_data(ttl=30)
def get_realtime_data(stock_id):
    rt_data = {}
    try:
        session = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        session.get("https://mis.twse.com.tw/stock/index.jsp", headers=headers, timeout=5)
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw|otc_{stock_id}.tw"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            msg_array = data.get('msgArray', [])
            if msg_array:
                info = msg_array[0]
                def p_f(v): return float(v) if v != '-' and v is not None else None
                rt_price = p_f(info.get('z'))
                if rt_price is None: rt_price = p_f(info.get('y'))
                if rt_price is not None:
                    rt_data['realtime_price'] = rt_price
                    rt_data['realtime_prev_close'] = p_f(info.get('y'))
                    rt_data['realtime_open'] = p_f(info.get('o')) or rt_price
                    rt_data['realtime_high'] = p_f(info.get('h')) or rt_price
                    rt_data['realtime_low'] = p_f(info.get('l')) or rt_price
                    rt_data['realtime_volume'] = p_f(info.get('v'))
                    return rt_data
    except: pass

    for ext in [".TW", ".TWO"]:
        try:
            tk = yf.Ticker(f"{stock_id}{ext}")
            fi = tk.fast_info
            if 'last_price' in fi:
                rt_data['realtime_price'] = fi['last_price']
                rt_data['realtime_prev_close'] = fi.get('previous_close')
                rt_data['realtime_open'] = fi.get('open')
                rt_data['realtime_high'] = fi.get('day_high')
                rt_data['realtime_low'] = fi.get('day_low')
                rt_data['realtime_volume'] = fi.get('last_volume')
                return rt_data
        except: continue
        
    return rt_data

def inject_realtime_data(hist, stock_id, timeframe="D"):
    if hist is None or hist.empty: return hist, None
    
    tw_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    if tw_time.hour < 9: target_date = (tw_time - datetime.timedelta(days=1)).date()
    else: target_date = tw_time.date()
    
    if hist.index.tz is not None:
        hist = hist[hist.index.date <= target_date]
    else:
        hist = hist[hist.index.date <= target_date]
        
    if hist.empty: return hist, None

    rt_data = get_realtime_data(stock_id)
    rt_price = rt_data.get('realtime_price')
    rt_prev = rt_data.get('realtime_prev_close')
    
    if rt_price is not None and rt_price > 0:
        rt_open = rt_data.get('realtime_open') or rt_price
        rt_high = rt_data.get('realtime_high') or rt_price
        rt_low = rt_data.get('realtime_low') or rt_price
        rt_vol = rt_data.get('realtime_volume') or 0
        
        last_date = hist.index[-1].date()
        if timeframe == "D":
            if last_date < target_date:
                new_idx = pd.to_datetime(target_date)
                if hist.index.tz is not None: new_idx = new_idx.tz_localize(hist.index.tz)
                new_row = pd.DataFrame({
                    'Open': [rt_open], 'High': [rt_high], 'Low': [rt_low], 
                    'Close': [rt_price], 'Volume': [rt_vol]
                }, index=pd.Index([new_idx], name='Date'))
                hist = pd.concat([hist, new_row])
            elif last_date == target_date:
                hist.loc[hist.index[-1], 'Close'] = rt_price
                hist.loc[hist.index[-1], 'Open'] = rt_open
                hist.loc[hist.index[-1], 'High'] = max(hist.loc[hist.index[-1], 'High'], rt_high)
                hist.loc[hist.index[-1], 'Low'] = min(hist.loc[hist.index[-1], 'Low'], rt_low)
                if rt_vol > 0: hist.loc[hist.index[-1], 'Volume'] = rt_vol
        elif timeframe in ["W", "M"]:
            hist.loc[hist.index[-1], 'Close'] = rt_price
            if rt_high > hist.loc[hist.index[-1], 'High']: hist.loc[hist.index[-1], 'High'] = rt_high
            if rt_low < hist.loc[hist.index[-1], 'Low']: hist.loc[hist.index[-1], 'Low'] = rt_low
            
    hist.index.name = 'Date'
    return hist, rt_prev

@st.cache_data(ttl=3600)
def _get_base_stock_data(stock_id, fugle_key="", fm_key=""):
    hist = None
    info_data = {}
    price_source = None
    info_source = None
    fallback_notes = []

    if fugle_key:
        hist = fetch_fugle_kline(stock_id, fugle_key, "D")
        if hist is not None and not hist.empty:
            price_source = "Fugle API"
    
    for ext in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{stock_id}{ext}")
            if hist is None or hist.empty:
                temp_hist = ticker.history(period="5y")
                if not temp_hist.empty:
                    hist = temp_hist
                    price_source = "Yahoo Finance (yfinance)"
            try:
                info_data = ticker.info
                if info_data:
                    info_source = "Yahoo Finance (yfinance)"
            except:
                pass
            if info_data or (hist is not None and not hist.empty): break
        except: continue
            
    if hist is None or hist.empty:
        for ext in [".TW", ".TWO"]:
            try:
                url = f"https://query1.finance.yahoo.com/v7/finance/download/{stock_id}{ext}?range=5y&interval=1d&events=history"
                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                log_data_health("Yahoo", res.status_code == 200, res.status_code)
                if res.status_code == 200:
                    df = pd.read_csv(io.StringIO(res.text))
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    hist = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    if not hist.empty:
                        price_source = "Yahoo Finance CSV fallback"
                        fallback_notes.append("主資料源失敗，已改用 Yahoo CSV 備援股價。")
                        break
            except: pass

    if hist is None or hist.empty:
        try:
            start_str = f"{(datetime.date.today() - datetime.timedelta(days=1825)).isoformat()}"
            url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={stock_id}&start_date={start_str}"
            if fm_key: url += f"&token={fm_key}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            log_data_health("FinMind", res.status_code == 200, res.status_code)
            data = res.json()
            if data.get('status') == 200 and data.get('data'):
                df = pd.DataFrame(data['data'])
                df['Date'] = pd.to_datetime(df['date'])
                df.rename(columns={'open':'Open','max':'High','min':'Low','close':'Close','Trading_Volume':'Volume'}, inplace=True)
                df.set_index('Date', inplace=True)
                hist = df[['Open','High','Low','Close','Volume']]
                if hist is not None and not hist.empty:
                    price_source = "FinMind fallback"
                    fallback_notes.append("Yahoo 來源失敗，已改用 FinMind 備援股價。")
        except: pass

    if hist is not None and not hist.empty:
        hist.index.name = 'Date'
        fallback = get_fallback_info(stock_id)
        filled_from_fallback = 0
        for k, v in fallback.items():
            if v is not None:
                if k not in info_data or not info_data[k] or str(info_data[k]).lower() == 'nan':
                    info_data[k] = v
                    filled_from_fallback += 1
        if filled_from_fallback > 0:
            if info_source is None:
                info_source = "Yahoo 頁面解析備援"
            fallback_notes.append(f"已由頁面解析補齊 {filled_from_fallback} 個財務欄位。")

    info_data['__price_source'] = price_source or "未知來源"
    info_data['__info_source'] = info_source or "未知來源"
    info_data['__fallback_notes'] = fallback_notes                    
    return hist, info_data

def get_stock_data(stock_id, fugle_key="", fm_key=""):
    hist, info_data = _get_base_stock_data(stock_id, fugle_key, fm_key)
    if hist is not None and not hist.empty:
        hist = hist.copy()
        info_data = info_data.copy()
        hist, rt_prev = inject_realtime_data(hist, stock_id, "D")
        if rt_prev is not None: info_data['previousClose'] = rt_prev
    return hist, info_data

@st.cache_data(ttl=900)
def _get_base_chart_data(stock_id, timeframe, fugle_key=""):
    tf_map = {"日線": "D", "週線": "W", "月線": "M", "60分線": "60"}
    if fugle_key:
        tf = tf_map.get(timeframe, "D")
        df = fetch_fugle_kline(stock_id, fugle_key, tf)
        if not df.empty:
            df.index.name = 'Date'
            return df

    interval_map = {"日線": {"period": "1y", "interval": "1d"}, "週線": {"period": "2y", "interval": "1wk"}, "月線": {"period": "5y", "interval": "1mo"}, "60分線": {"period": "1mo", "interval": "60m"}}
    params = interval_map.get(timeframe, {"period": "1y", "interval": "1d"})
    for ext in [".TW", ".TWO"]:
        try:
            ticker = yf.Ticker(f"{stock_id}{ext}")
            df = ticker.history(period=params["period"], interval=params["interval"])
            if not df.empty:
                if df.index.tz is not None: df.index = df.index.tz_localize(None)
                df.index.name = 'Date'
                return df
        except: continue
        
    if timeframe == "日線":
        hist, _ = _get_base_stock_data(stock_id, fugle_key, "")
        if hist is not None and not hist.empty: return hist

    return pd.DataFrame()

def get_chart_data(stock_id, timeframe, fugle_key=""):
    df = _get_base_chart_data(stock_id, timeframe, fugle_key)
    if not df.empty:
        df = df.copy()
        if timeframe == "日線": df, _ = inject_realtime_data(df, stock_id, "D")
        elif timeframe == "週線": df, _ = inject_realtime_data(df, stock_id, "W")
        elif timeframe == "月線": df, _ = inject_realtime_data(df, stock_id, "M")
    return df

@st.cache_data(ttl=43200)
def get_inst_data(stock_id, fm_key=""):
    try:
        today = datetime.date.today()
        start_str = (today - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={start_str}"
        if fm_key: url += f"&token={fm_key}" 
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 200 and data.get('data'):
                df = pd.DataFrame(data['data'])
                if df.empty: return pd.DataFrame()
                df['date'] = pd.to_datetime(df['date'])
                
                if 'buy_sell' not in df.columns:
                    if 'buy' not in df.columns: df['buy'] = 0
                    if 'sell' not in df.columns: df['sell'] = 0
                    df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
                    df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
                    df['buy_sell'] = df['buy'] - df['sell']
                else:
                    df['buy_sell'] = pd.to_numeric(df['buy_sell'], errors='coerce').fillna(0)
                
                pivot_df = df.pivot_table(index='date', columns='name', values='buy_sell', aggfunc='sum').fillna(0)
                res_df = pd.DataFrame(index=pivot_df.index)
                f_cols = [c for c in pivot_df.columns if '外資' in str(c) or 'Foreign' in str(c)]
                t_cols = [c for c in pivot_df.columns if '投信' in str(c) or 'Trust' in str(c)]
                d_cols = [c for c in pivot_df.columns if '自營商' in str(c) or 'Dealer' in str(c)]
                res_df['Foreign'] = pivot_df[f_cols].sum(axis=1) if f_cols else 0
                res_df['Trust'] = pivot_df[t_cols].sum(axis=1) if t_cols else 0
                res_df['Dealer'] = pivot_df[d_cols].sum(axis=1) if d_cols else 0
                return res_df / 1000 
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=60)
def validate_api_keys(f_key, m_key):
    f_res, m_res = None, None
    if f_key:
        clean_f = re.sub(r'\s+', '', f_key)
        try:
            r1 = requests.get("https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/2330?timeframe=D", headers={"X-API-KEY": clean_f}, timeout=15)
            f_res = (r1.status_code == 200)
        except: f_res = False
    if m_key:
        clean_m = re.sub(r'\s+', '', m_key)
        try:
            r2 = requests.get(f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=2330&start_date=2024-01-01&end_date=2024-01-02&token={clean_m}", timeout=15)
            m_res = (r2.status_code == 200 and r2.json().get('status') == 200)
        except: m_res = False
    return f_res, m_res

@st.cache_data(ttl=86400) 
def get_chinese_name(stock_id):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        match = re.search(r'<title>(.*?)(?:\(| \()', res.text)
        if match: return match.group(1).strip()
    except: pass
    return None

@st.cache_data(ttl=86400)
def translate_to_zh(text):
    if not text or text == '暫無簡介。': return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "zh-TW", "dt": "t", "q": text}
        res = requests.get(url, params=params, timeout=5)
        return "".join([item[0] for item in res.json()[0]])
    except: return text + "\n\n(⚠️ 翻譯服務暫時忙碌中)"

# ==========================================
# 3.3 ETF 持股快取 v9 覆寫：避免外部站連線失敗時慢掃；新增 Yahoo ETF 持股頁反查
# ==========================================
ETF_CACHE_VERSION = "v9.0-fast-fail-yahoo-etf-holding-fallback"

# 預設只快速掃描台股/主動式與常見科技 ETF，避免 53 檔 x 3 來源造成 Streamlit 卡住。
ETF_PRIORITY_CODES = [
    "00981A", "00987A", "00988A", "00403A", "00400A",
    "00980A", "00982A", "00984A", "00985A", "00986A", "00989A",
    "0050", "0052", "006208", "00952", "00922", "00923", "00904", "00881",
]


def _request_html_quick(url, timeout=(1.2, 3.0)):
    """短逾時抓取，避免 Streamlit Cloud 對 MoneyDJ/Pocket/CMoney 連線失敗時卡很久。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "close",
    }
    res = requests.get(url, headers=headers, timeout=timeout)
    res.raise_for_status()
    if not res.encoding or str(res.encoding).lower() == "iso-8859-1":
        res.encoding = res.apparent_encoding or "utf-8"
    return res.text


def _parse_yahoo_etf_holding_html(html, etf_code, etf_name=""):
    """解析 Yahoo ETF 的 holding 頁：/quote/00981A.TW/holding。"""
    url = f"https://tw.stock.yahoo.com/quote/{str(etf_code).upper()}.TW/holding"
    data_date = _extract_data_date_from_text(html)
    rows = []

    # 先沿用 v8 的表格/文字解析。
    try:
        rows.extend(_parse_holdings_tables_from_html(html, etf_code, etf_name, "Yahoo ETF持股頁", url))
    except Exception:
        pass

    try:
        rows.extend(_parse_holdings_text_regex_fallback(html, etf_code, etf_name, "Yahoo ETF持股頁", url, data_date=data_date))
    except Exception:
        pass

    # Yahoo 常把資料塞在 JSON/Next data，補抓常見 key 組合。
    text = str(html or "")
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r"&quot;|&#34;", '"', text)
    text = re.sub(r"&amp;", "&", text)
    text_plain = re.sub(r"<[^>]+>", " ", text)
    text_plain = re.sub(r"\s+", " ", text_plain)

    # JSON 區塊：symbol/name/weight 可能順序不同，所以用附近 block 判讀。
    for m in re.finditer(r'(?<!\d)(\d{4})(?:\.TW)?(?!\d)', text_plain):
        stock_code = m.group(1)
        block = text_plain[max(0, m.start()-220): min(len(text_plain), m.end()+260)]
        # 抓附近中文名
        nm = ""
        before = block[:block.find(stock_code)] if stock_code in block else block
        after = block[block.find(stock_code)+len(stock_code):] if stock_code in block else block
        name_candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9\-＋+＊*·]{2,24}", before[-80:] + " " + after[:80])
        for cand in name_candidates:
            if cand not in ["持股比例", "持有股數", "資料日期", "Yahoo", "Finance"] and not re.fullmatch(r"\d+", cand):
                nm = cand
                break
        # 抓附近百分比
        wm = re.search(r"(-?\d{1,3}(?:\.\d{1,4})?)\s*%", block)
        weight = _clean_percent_to_float(wm.group(1)) if wm else None
        if stock_code and (nm or weight is not None):
            rows.append({
                "etf_code": str(etf_code).upper(),
                "etf_name": etf_name,
                "stock_code": stock_code,
                "stock_name": nm,
                "weight": weight,
                "shares": None,
                "data_date": data_date,
                "source": "Yahoo ETF持股頁",
                "source_url": url,
                "data_type": "系統抓取",
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "parse_method": "yahoo_nearby_regex",
            })

    return _dedup_holding_rows(rows)


def fetch_yahoo_etf_holdings(etf_code, etf_name=""):
    url = f"https://tw.stock.yahoo.com/quote/{str(etf_code).upper()}.TW/holding"
    html = _request_html_quick(url)
    return _parse_yahoo_etf_holding_html(html, etf_code, etf_name)


def _probe_source_health():
    """先探測來源是否可連線；不可連線就整批跳過，避免每檔 ETF 都 timeout。"""
    tests = {
        "MoneyDJ": "https://www.moneydj.com/etf/x/basic/basic0007.xdjhtm?etfid=0050.tw",
        "Pocket": "https://www.pocket.tw/etf/tw/0050/fundholding/",
        "CMoney": "https://www.cmoney.tw/etf/tw/0050/fundholding",
        "Yahoo ETF持股頁": "https://tw.stock.yahoo.com/quote/0050.TW/holding",
    }
    health = {}
    for name, url in tests.items():
        try:
            html = _request_html_quick(url, timeout=(1.0, 2.2))
            health[name] = bool(html and len(html) > 500)
        except Exception as e:
            health[name] = False
    return health


def _get_priority_master_items(master):
    """把主動式與常用台股科技 ETF 放前面，且預設只掃這批，避免更新太慢。"""
    by_code = {str(x.get("etf_code", "")).upper(): x for x in master if x.get("etf_code")}
    items = []
    for code in ETF_PRIORITY_CODES:
        if code in by_code:
            items.append(by_code[code])
        else:
            seed_name = next((n for c, n in ETF_SEED_LIST if c.upper() == code), "")
            items.append({"etf_code": code, "etf_name": seed_name, "source": "priority_seed"})
    # 去重
    seen, out = set(), []
    for x in items:
        c = str(x.get("etf_code", "")).upper()
        if c and c not in seen:
            seen.add(c)
            out.append(x)
    return out


def update_etf_holdings_cache(force=False, max_etfs=None, scan_all=False):
    """
    v9：快速更新 ETF → 成分股快取。
    - 先探測來源，MoneyDJ/Pocket/CMoney 無法連線就整批跳過，不再 53 檔逐一 timeout。
    - 預設只掃重點/主動式 ETF，避免 Streamlit Cloud 按鈕卡 1 分鐘以上。
    - 新增 Yahoo ETF 持股頁作為可連線的 ETF→成分股來源，用來補 00981A 這類 Yahoo 個股頁漏列問題。
    """
    cached = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    if (not force) and cached.get("updated_date") == _today_str() and cached.get("holdings"):
        return cached

    master_all = discover_etf_master_list(force=force)
    if scan_all:
        master = master_all
    else:
        master = _get_priority_master_items(master_all)
    if max_etfs:
        master = master[:int(max_etfs)]

    source_health = _probe_source_health()
    holdings = []
    errors = []

    for item in master:
        code = str(item.get("etf_code", "")).upper()
        name = item.get("etf_name", "")
        if not code:
            continue
        rows = []

        if source_health.get("MoneyDJ"):
            try:
                rows = fetch_moneydj_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "MoneyDJ", "error": str(e)[:180]})
        else:
            errors.append({"etf_code": code, "source": "MoneyDJ", "error": "來源探測失敗，已跳過整批 MoneyDJ，避免逐檔 timeout"})

        if not rows and source_health.get("Yahoo ETF持股頁"):
            try:
                rows = fetch_yahoo_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "Yahoo ETF持股頁", "error": str(e)[:180]})

        if not rows and source_health.get("Pocket"):
            try:
                rows = fetch_pocket_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "Pocket", "error": str(e)[:180]})
        elif not source_health.get("Pocket"):
            errors.append({"etf_code": code, "source": "Pocket", "error": "來源探測失敗，已跳過整批 Pocket"})

        if not rows and source_health.get("CMoney"):
            try:
                rows = fetch_cmoney_etf_holdings(code, name)
            except Exception as e:
                errors.append({"etf_code": code, "source": "CMoney", "error": str(e)[:180]})
        elif not source_health.get("CMoney"):
            errors.append({"etf_code": code, "source": "CMoney", "error": "來源探測失敗，已跳過整批 CMoney"})

        holdings.extend(rows)
        time.sleep(0.05)

    cache = {
        "version": ETF_CACHE_VERSION,
        "updated_date": _today_str(),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "master_count": len(master),
        "master_total_count": len(master_all),
        "scan_mode": "all" if scan_all else "priority_fast",
        "source_health": source_health,
        "holdings_count": len(holdings),
        "holdings": _dedup_holding_rows(holdings),
        "errors_sample": errors[:80],
        "note": "v9 預設快速掃描重點/主動式 ETF；MoneyDJ/Pocket/CMoney 若探測失敗會整批跳過，避免按鈕卡住。",
    }
    cache["holdings_count"] = len(cache["holdings"])
    _write_json_file(ETF_HOLDINGS_CACHE_FILE, cache)
    return cache


def load_etf_holdings_cache(auto_update=True):
    cache = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    # v9：自動更新只在快取不存在時做快速更新；若今天已建立但 0 筆，不在每次頁面載入重跑，避免變慢。
    if auto_update and (not cache or cache.get("updated_date") != _today_str()):
        cache = update_etf_holdings_cache(force=False)
    return cache


def get_etf_cache_status():
    cache = _read_json_file(ETF_HOLDINGS_CACHE_FILE, {})
    master = _read_json_file(ETF_MASTER_CACHE_FILE, {})
    return {
        "cache_version": cache.get("version", "尚未建立"),
        "updated_date": cache.get("updated_date", "尚未更新"),
        "updated_at": cache.get("updated_at", "尚未更新"),
        "is_today": cache.get("updated_date") == _today_str(),
        "master_count": cache.get("master_count", master.get("count", 0)),
        "master_total_count": cache.get("master_total_count", master.get("count", 0)),
        "scan_mode": cache.get("scan_mode", "尚未建立"),
        "source_health": cache.get("source_health", {}),
        "holdings_count": cache.get("holdings_count", len(cache.get("holdings", [])) if isinstance(cache.get("holdings"), list) else 0),
        "errors_count": len(cache.get("errors_sample", [])) if isinstance(cache.get("errors_sample"), list) else 0,
    }


def _scan_priority_etfs_for_stock(stock_id, stock_name=""):
    """快取沒有命中時，快速直接檢查重點 ETF 的 Yahoo ETF 持股頁，避免 00981A 漏掉。"""
    stock_id = str(stock_id).strip()
    target_name_key = _normalize_tw_name(stock_name or "")
    if not target_name_key:
        try:
            target_name_key = _normalize_tw_name(get_chinese_name(stock_id) or "")
        except Exception:
            target_name_key = ""

    master = discover_etf_master_list(force=False)
    candidates = _get_priority_master_items(master)
    out = []
    for item in candidates:
        code = str(item.get("etf_code", "")).upper()
        name = item.get("etf_name", "")
        try:
            rows = fetch_yahoo_etf_holdings(code, name)
        except Exception:
            continue
        for r in rows:
            row_code = str(r.get("stock_code", "")).strip()
            row_name_key = _normalize_tw_name(r.get("stock_name", ""))
            if row_code == stock_id or (target_name_key and row_name_key and target_name_key == row_name_key):
                out.append({
                    "etf_code": _normalize_etf_code(r.get("etf_code")),
                    "etf_name": r.get("etf_name", name),
                    "weight": r.get("weight"),
                    "shares": r.get("shares"),
                    "data_date": r.get("data_date") or "來源未揭露",
                    "source": r.get("source") or "Yahoo ETF持股頁",
                    "source_url": r.get("source_url", ""),
                    "data_type": "ETF持股頁快速反查",
                    "note": "快取未命中時，直接檢查重點 ETF 的持股頁；不是 Yahoo 個股頁結果",
                })
    return _normalize_etf_holders(out, default_source="ETF持股頁快速反查")


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_etf_holders(stock_id, stock_name=None, force_refresh=False):
    """
    v9：優先從 ETF 成分股快取反查；快取 0 筆時改用重點 ETF 持股頁快速反查；最後才退回 Yahoo 個股頁補漏。
    """
    stock_id = str(stock_id).strip()
    if not stock_id:
        return []

    cache = update_etf_holdings_cache(force=True) if force_refresh else load_etf_holdings_cache(auto_update=True)
    holdings = cache.get("holdings", []) if isinstance(cache, dict) else []
    results = []
    target_name_key = _normalize_tw_name(stock_name or "")
    if not target_name_key:
        try:
            target_name_key = _normalize_tw_name(get_chinese_name(stock_id) or "")
        except Exception:
            target_name_key = ""

    for r in holdings:
        row_code = str(r.get("stock_code", "")).strip()
        row_name_key = _normalize_tw_name(r.get("stock_name", ""))
        if row_code == stock_id or (target_name_key and row_name_key and target_name_key == row_name_key):
            results.append({
                "etf_code": _normalize_etf_code(r.get("etf_code")),
                "etf_name": r.get("etf_name", ""),
                "weight": r.get("weight"),
                "shares": r.get("shares"),
                "data_date": r.get("data_date") or "來源未揭露",
                "source": r.get("source") or "ETF成分股快取",
                "source_url": r.get("source_url", ""),
                "data_type": "ETF成分股快取反查",
                "note": "由 ETF 持股明細反查，不是 Yahoo 個股頁結果",
            })

    if not results:
        results = _scan_priority_etfs_for_stock(stock_id, stock_name)

    # 去重排序
    pref = {"MoneyDJ": 0, "Yahoo ETF持股頁": 1, "Pocket": 2, "CMoney": 3, "TWSE": 4, "Yahoo股市": 8, "FindBillion": 9}
    dedup = {}
    for r in results:
        code = r.get("etf_code")
        if not code:
            continue
        old = dedup.get(code)
        if old is None:
            dedup[code] = r
        else:
            old_rank = pref.get(str(old.get("source")), 99)
            new_rank = pref.get(str(r.get("source")), 99)
            if (old.get("weight") is None and r.get("weight") is not None) or new_rank < old_rank:
                dedup[code] = r
    results = list(dedup.values())
    results.sort(key=lambda x: (x.get("weight") is None, -(x.get("weight") or 0)))
    if results:
        return results[:80]

    # 最後補漏：舊 Yahoo 個股頁。這會漏 00981A，所以只當最後備援。
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
        sources = [
            ("Yahoo股市", f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/etf"),
            ("FindBillion", f"https://www.findbillion.com/twstock/{stock_id}/etf"),
        ]
        best_rows = []
        for source_name, url in sources:
            try:
                res = requests.get(url, headers=headers, timeout=(1.2, 3.0))
                if res.status_code != 200:
                    continue
                rows = _extract_etf_holders_from_text(res.text, source_name)
                for rr in rows:
                    rr["data_date"] = rr.get("data_date") or "來源未揭露"
                    rr["data_type"] = "個股頁補漏"
                    rr["note"] = "ETF 快取與重點 ETF 持股頁未命中，改用個股頁補漏；此來源可能漏主動式 ETF"
                if rows and (not best_rows or len(rows) > len(best_rows)):
                    best_rows = rows
            except Exception:
                continue
        return best_rows[:20]
    except Exception:
        return []


# ==========================================
# 3.4 ETF 持股查詢 v10：一般頁面只顯示 Yahoo 主要/前十大；完整 ETF 另用 AI 按鈕查
# ==========================================
ETF_SYSTEM_NOTE_V10 = "Yahoo 個股 ETF 頁多為主要/前十大或公開頁面可解析清單，不代表完整 ETF 持股名單。"

@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_etf_holders(stock_id, stock_name=None, force_refresh=False):
    """
    v10：一般個股頁只做快速查詢，不再更新/掃描 ETF 成分股快取。
    - 不使用 AI。
    - 不掃 MoneyDJ / Pocket / CMoney，避免 Streamlit Cloud 卡住。
    - 主要使用 Yahoo 個股 ETF 頁，必要時 FindBillion 補漏。
    - 回傳的 data_type 固定標示為「主要/前十大快速查詢」。
    """
    stock_id = str(stock_id).strip()
    if not stock_id:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    sources = [
        ("Yahoo股市", f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/etf"),
        ("FindBillion", f"https://www.findbillion.com/twstock/{stock_id}/etf"),
    ]
    best_rows = []
    for source_name, url in sources:
        try:
            res = requests.get(url, headers=headers, timeout=(1.5, 4.0))
            if res.status_code != 200:
                continue
            rows = _extract_etf_holders_from_text(res.text, source_name)
            for rr in rows:
                rr["data_date"] = rr.get("data_date") or "來源未揭露"
                rr["data_type"] = "主要/前十大快速查詢"
                rr["note"] = ETF_SYSTEM_NOTE_V10
            if rows and (not best_rows or len(rows) > len(best_rows)):
                best_rows = rows
        except Exception:
            continue
    return _normalize_etf_holders(best_rows, default_source="主要/前十大快速查詢")[:20]


def get_etf_holders_from_ai(stock_id, stock_name, api_key, model_name="gemini-3.1-pro-preview"):
    """
    獨立 AI ETF 持股查詢：只在使用者按下「AI 查完整 ETF 持有狀況」時執行。
    不併入 get_financials_from_ai()，避免財報校對工作量過大。
    """
    if not api_key:
        return {"error": "未提供 API Key"}
    try:
        client = genai.Client(api_key=api_key.strip())
    except Exception as e:
        return {"error": f"GenAI Client 初始化失敗：{str(e)}"}

    system_prompt = """你是一位台股 ETF 持股查詢助理。請查詢指定台股被哪些 ETF 持有。
重點規則：
1. 不要只依賴 Yahoo 個股 ETF 頁，因為該頁可能只列主要或前十大 ETF。
2. 優先查投信官網/PCF/投資組合明細，其次 MoneyDJ、Pocket、CMoney、WantGoo、Yahoo ETF 持股頁。
3. 請特別檢查主動式 ETF：00981A、00987A、00988A、00400A、00403A、00980A、00982A、00984A、00985A、00986A、00989A、00990A。
4. 請回傳 JSON，不要輸出 markdown 或解釋文字。
5. weight 請用百分比數字，例如 9.68% 寫成 9.68；若查無比例請填 null。
6. data_date 請填資料日期；若來源未揭露請填 null。
格式：
{"etf_holders_ai":[{"etf_code":"00981A","etf_name":"主動統一台股增長","weight":9.68,"data_date":"2026/05/13","source":"MoneyDJ","note":"資料來源說明"}],"summary":"簡短說明資料完整性與限制"}
"""
    prompt_text = f"請查詢台股 {stock_name} ({stock_id}) 被哪些 ETF 持有，尤其確認主動式 ETF 是否持有。請回傳 ETF 代號、名稱、持股比例、資料日期、資料來源。"
    attempts = []
    try:
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[{"google_search": {}}],
                response_mime_type="application/json",
            ),
        )
        text = response.text or ""
        attempts.append({"model": "gemini-3.1-pro-preview", "ok": True})
    except Exception as e:
        return {"error": f"AI ETF 持股查詢失敗：{str(e)}", "attempts": attempts}

    s_idx = text.find('{')
    e_idx = text.rfind('}')
    if s_idx == -1 or e_idx == -1:
        return {"error": "AI 回傳格式無法解析 JSON", "raw_text_preview": text[:500], "attempts": attempts}
    try:
        parsed = json.loads(text[s_idx:e_idx+1])
    except Exception as e:
        return {"error": f"AI ETF JSON 解析失敗：{str(e)}", "raw_text_preview": text[:500], "attempts": attempts}

    rows = _normalize_etf_holders(parsed.get("etf_holders_ai") or [], default_source="AI補查ETF")
    for row in rows:
        row["data_type"] = "AI完整ETF補查"
        row["note"] = row.get("note") or "AI 聯網補查，請以投信公告、PCF 或 ETF 官方持股明細為準。"
        if not row.get("data_date"):
            row["data_date"] = "來源未揭露"
    return {
        "etf_holders_ai": rows,
        "summary": parsed.get("summary", "AI 已完成 ETF 持股補查。"),
        "model_used": "Gemini 3 Pro Preview (付費版)",
        "ai_search_enabled": True,
        "query_payload": json.dumps({"stock": f"{stock_name} ({stock_id})", "prompt": prompt_text, "task": "獨立 AI ETF 持股查詢"}, ensure_ascii=False, indent=2),
        "attempts": attempts,
    }
