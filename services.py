"""
外部資料與模型服務層：
yfinance、Fugle、FinMind、Yahoo、Gemini 等 API 存取都集中在這裡。
由原始 app(1).py 拆分而來。
"""
import datetime
import io
import json
import math
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

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

def get_financials_from_ai(stock_name, stock_id, api_key, model_name="gemini-3.1-flash-preview"):
    if not api_key: return {"error": "未提供 API Key"}
    api_key = api_key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    current_year = datetime.date.today().year
    target_year = current_year if datetime.date.today().month < 9 else current_year + 1
    
    # 🚀 修復 1：加回 JSON 格式範例，強制 AI 使用英文 key 輸出，確保 UI 能成功解析
    system_prompt = f"""你是一個精準的財經數據提取機器人。請上網搜尋該台股公司最新財報與市場數據，提取以下指標：
    1. 「歷史本益比 (P/E)」
    2. 「近四季或最新年度 EPS (Trailing EPS)」
    3. 「法人預估 {target_year} 年度 EPS (Forward EPS)」
    4. 「股價淨值比 (P/B)」
    5. 「毛利率」
    6. 「營益率」
    7. 「ROE(股東權益報酬率)」
    8. 「最新單月或累計營收年增率(YoY)」
    9. 「國內外法人最新預估目標價 (Target Price)」
    10. 「負債權益比 (Debt-to-Equity Ratio)」
    11. 「最新單月營收月增率(MoM)」
    12. 「預估現金殖利率 (Dividend Yield)」(例如：擬配發現金股利2元，最新股價900元，殖利率應為 0.0022)
    13. 「最新資料所屬年月或季度 (Data Period)」

    必須嚴格回傳包含上述 13 個欄位的 JSON 格式。百分比請轉換為小數（例如 25.5% 寫成 0.255，衰退5%寫成 -0.05），數值請直接輸出數字。若查無資料，該欄位請填 null。
    格式範例：
    {{"pe": 15.2, "trailing_eps": 5.4, "forward_eps": 6.2, "pb": 2.1, "gross_margin": 0.255, "operating_margin": 0.123, "roe": 0.15, "yoy": 0.082, "target_price": 1050.0, "debt_to_equity": 0.45, "mom": 0.015, "dividend_yield": 0.032, "data_period": "2024/03"}}
    絕對不要輸出 markdown 標記或其他文字。"""
    
    # 🚀 修復 2：聯網工具統一更正為官方標準的 googleSearch (駝峰命名)
    payload = {
        "contents": [{"parts": [{"text": f"請啟用搜尋引擎，查詢台股 {stock_name} ({stock_id}) 最新財報新聞、營收 MoM，以及 {target_year} 法人預測 EPS 與最新目標價"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    payload_no_search = {
        "contents": payload["contents"],
        "systemInstruction": payload["systemInstruction"],
        "generationConfig": payload["generationConfig"]
    }
    try:
        headers = {"Content-Type": "application/json"}
        used_model = model_name
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        if res.status_code == 404 and model_name != "gemini-2.5-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            res = requests.post(fallback_url, headers=headers, json=payload, timeout=60)
            used_model = "gemini-2.5-flash"
            
        # Google Search grounding 在尖峰時段可能較慢，若逾時則自動改用無搜尋工具重試一次
        if res.status_code in (408, 504, 500, 503):
            res = requests.post(url, headers=headers, json=payload_no_search, timeout=60)

        log_data_health("Gemini", res.status_code == 200, res.status_code)
        if res.status_code != 200:
            return {"error": f"API 連線被拒絕 (代碼 {res.status_code})。細節：{res.text[:150]}"}

        text = (
            res.json()
            .get('candidates', [{}])[0]
            .get('content', {})
            .get('parts', [{}])[0]
            .get('text', '')
            .strip()
        )
        if not text:
            return {"error": "AI 回傳內容為空，請稍後重試。"}
            
        s_idx = text.find('{')
        e_idx = text.rfind('}')
        if s_idx != -1 and e_idx != -1:
            clean_text = text[s_idx:e_idx+1]
            parsed = json.loads(clean_text)
            if isinstance(parsed, dict):
                parsed["model_used"] = used_model
                parsed["query_payload"] = json.dumps(payload, ensure_ascii=False, indent=2)
            return parsed            
        else:
            return {"error": "AI 回傳的格式不正確，無法萃取 JSON 資料。"}
            
    except requests.exceptions.Timeout:
        try:
            # 最後保底：改用 2.5 Flash 並關閉搜尋工具，降低逾時風險
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            res = requests.post(fallback_url, headers={"Content-Type": "application/json"}, json=payload_no_search, timeout=45)
            log_data_health("Gemini", res.status_code == 200, res.status_code)
            if res.status_code == 200:
                text = (
                    res.json()
                    .get('candidates', [{}])[0]
                    .get('content', {})
                    .get('parts', [{}])[0]
                    .get('text', '')
                    .strip()
                )
                s_idx = text.find('{')
                e_idx = text.rfind('}')
                if s_idx != -1 and e_idx != -1:
                    parsed = json.loads(text[s_idx:e_idx+1])
                    if isinstance(parsed, dict):
                        parsed["model_used"] = "gemini-2.5-flash"
                        parsed["query_payload"] = json.dumps(payload_no_search, ensure_ascii=False, indent=2)
                    return parsed                    
        except Exception:
            pass
        return {"error": "連線逾時 (超過 60 秒)，已嘗試自動降級模型仍失敗，請稍後再試。"}

    except Exception as e: 
        return {"error": f"發生未預期的例外狀況：{str(e)}"}

@st.cache_data(ttl=86400)
def get_peers_from_ai(stock_name, stock_id, api_key):
    if not api_key: return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": f"請尋找 {stock_name} ({stock_id}) 的同業競爭對手"}]}], 
        "systemInstruction": {"parts": [{"text": "請列出與目標公司核心業務最直接競爭的 3~5 家台股上市櫃公司代號。必須是純數字 JSON 陣列格式：[\"2383\", \"3044\"]。絕對不要輸出其他文字。"}]},
        "tools": [{"googleSearch": {}}]
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
        log_data_health("Gemini", res.status_code == 200, res.status_code)
        if res.status_code == 200:
            clean_text = re.sub(r'```json\n?|```', '', res.json()['candidates'][0]['content']['parts'][0]['text']).strip()
            peers = json.loads(clean_text)
            if isinstance(peers, list): return [str(p) for p in peers][:4] 
    except: pass
    return []

def get_ai_industry_analysis(stock_name, stock_id, api_key, context_data, model_name="gemini-2.5-flash"):
    if not api_key: return "ERROR: 未輸入金鑰"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key.strip()}"
    system_prompt = """你是一位精通台股的資深產業分析師與操盤手。請針對目標公司的最新動態提供深度分析，包含產業前景、競爭優勢、系統風險及買賣點策略。請用 Markdown 格式與 Emoji。不要輸出 HTML。"""
    payload = {
        "contents": [{"parts": [{"text": f"請深度分析台股 {stock_name} ({stock_id})。關鍵數據：\n{context_data}"}]}], 
        "systemInstruction": {"parts": [{"text": system_prompt}]}, 
        "tools": [{"googleSearch": {}}]
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=90)
        fallback_msg = ""
        if res.status_code == 404 and model_name != "gemini-2.5-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
            res = requests.post(fallback_url, headers={"Content-Type": "application/json"}, json=payload, timeout=90)
            fallback_msg = f"> 💡 **系統提示**：您指定的 `{model_name}` 尚未開放或輸入錯誤，系統已自動降級使用 `Gemini 2.5 Flash` 為您完成分析。\n\n---\n\n"
        log_data_health("Gemini", res.status_code == 200, res.status_code)
        if res.status_code == 200: 
            ans = re.sub(r'```markdown\n?|```', '', res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')).strip()
            return fallback_msg + ans
        elif res.status_code == 429: return "⏳ API 呼叫太頻繁，請稍候再試或切換回 Flash 模型。"
        else: return f"⚠️ API 連線失敗 (狀態碼: {res.status_code})"
    except Exception as e: return f"連線異常: {str(e)}"

def get_ai_analysis_final(topic, api_key, model_name="gemini-2.5-flash"):
    if not api_key: return "ERROR: 未輸入金鑰", []
    api_key = api_key.strip()
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    system_prompt = """你是一位精通台股產業鏈的專業分析師。請針對議題推薦 3 檔「潛力權值股」與 3 檔「中小型飆股」。必須嚴格回傳 JSON 格式：{"reasoning": "...", "stocks": [{"id": "4位數代號", "name": "中文名稱", "type": "潛力", "why": "原因"}]}。"""
    payload = {
        "contents": [{"parts": [{"text": f"請深度分析台股議題：{topic}"}]}], 
        "systemInstruction": {"parts": [{"text": system_prompt}]}, 
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 404 and model_name != "gemini-2.5-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(fallback_url, headers=headers, json=payload, timeout=60)
        log_data_health("Gemini", response.status_code == 200, response.status_code)
        if response.status_code == 200:
            res_json = response.json()
            content = res_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            clean_json = re.sub(r'```json\n?|```', '', content).strip()
            s_idx = clean_json.find('{')
            e_idx = clean_json.rfind('}')
            if s_idx != -1 and e_idx != -1: clean_json = clean_json[s_idx:e_idx+1]
            grounding = res_json.get('candidates', [{}])[0].get('groundingMetadata', {})
            links = [a.get('web', {}).get('uri') for a in grounding.get('groundingAttributions', []) if a.get('web', {}).get('uri')]
            return json.loads(clean_json), list(set(links))
        else: return f"API 錯誤 ({response.status_code})", []
    except Exception as e: return f"連線異常: {str(e)}", []

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
            return res_dict
    except: pass
    return {}

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
# 4. 側邊欄：功能選單與策略漏斗
# ==========================================
with st.sidebar:
    st.markdown("### 🔍 個股查詢")
    st.text_input("輸入台股代號", value=st.session_state.selected_stock, key="stock_input_widget", on_change=on_stock_input_change)
    st.markdown("<div style='color:#ff8c00; font-size:0.8rem; margin-top:-10px; margin-bottom:10px;'>💡 提示：輸入完畢請務必按 <b>Enter 鍵</b> 確認送出</div>", unsafe_allow_html=True)
    
    options = ["-- 快速切換標的 --"]
    categories = {}
    current_cat = "未分類"
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if "," in line:
                        p = line.split(",")
                        if len(p) >= 2:
                            options.append(f"　🔸 {p[0].strip()} {p[1].strip()}")
                            categories[current_cat].append((p[0].strip(), p[1].strip()))
                    else:
                        current_cat = line
                        options.append(f"🏷️ {line}")
                        categories[current_cat] = []
        except: pass
            
    st.selectbox("⚡ 快速選股名單", options, key="quick_select", on_change=on_quick_select_change)

    st.markdown("---")
    st.markdown("### 🎯 策略漏斗掃描器")
    if st.button("🔍 掃描同族群潛力股", use_container_width=True): st.session_state.run_screener = True
        
    if st.session_state.get('run_screener'):
        target_cat = None; target_stocks = []
        for cat, stocks in categories.items():
            for code, name in stocks:
                if code == st.session_state.selected_stock: target_cat = cat; target_stocks = stocks; break
        if target_cat and target_stocks:
            with st.spinner(f"掃描 {target_cat} 財報中..."):
                results = []
                pbar = st.progress(0)
                for i, (c, n) in enumerate(target_stocks):
                    _, inf = get_stock_data(c, st.session_state.fugle_key, st.session_state.finmind_key)
                    if inf:
                        pe = s_float(inf.get('trailingPE'))
                        roe = s_float(inf.get('returnOnEquity'))
                        eg = s_float(inf.get('earningsGrowth'))
                        if eg is None:
                            df_rv = get_monthly_revenue(c, st.session_state.finmind_key)
                            if df_rv is not None and not df_rv.empty: eg = s_float(df_rv['YoY'].iloc[-1]) / 100.0
                        
                        sys_peg = s_float(inf.get('pegRatio'))
                        peg_is_neg = (eg is not None and eg <= 0)
                        if (sys_peg is None or pd.isna(sys_peg)) and pe and eg and eg > 0: sys_peg = pe / (eg * 100)
                        
                        p_sort = sys_peg if sys_peg is not None and not pd.isna(sys_peg) and not peg_is_neg else 999
                        p_str = "分母為負" if peg_is_neg else (f"{sys_peg:.2f}" if sys_peg is not None and not pd.isna(sys_peg) else "N/A")
                        results.append({'code':c,'name':n,'roe':roe,'peg_sort':p_sort,'roe_str':to_pct(roe),'peg_str':p_str})
                    time.sleep(0.5); pbar.progress((i+1)/len(target_stocks))
                pbar.empty(); results.sort(key=lambda x: (x['peg_sort'], -x['roe'] if x['roe'] else 0))
                st.markdown("<div style='background:#1e1e1e; padding:10px; border-radius:5px; border-left:4px solid #00bfff;'><b>🌟 掃描結果</b></div>", unsafe_allow_html=True)
                for res in results:
                    icon = "🔥" if res['peg_sort'] < 1.5 and res['roe'] and res['roe'] > 0.15 else "🔸"
                    st.button(f"{icon} {res['name']} ({res['code']})\nPEG: {res['peg_str']} | ROE: {res['roe_str']}", key=f"s_{res['code']}", on_click=reset_all_states_on_stock_change, args=(res['code'],), use_container_width=True)

    st.markdown("---")
    st.markdown("### 🐳 籌碼集中度追蹤")
    if st.button("🔍 掃描籌碼增持名單", use_container_width=True):
        st.session_state.show_whale = True
        st.session_state.topic_results = None
        st.session_state.show_pk = False
        st.session_state.ai_industry_result = None
        st.session_state.run_screener = False
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔐 一鍵匯入金鑰")
    uploaded_key_file = st.file_uploader("📂 上傳 key.txt 自動填入", type=["txt"], help="請上傳包含 GEMINI_KEY, FUGLE_KEY, FINMIND_KEY 的純文字檔")
    if uploaded_key_file is not None:
        content = uploaded_key_file.getvalue().decode("utf-8")
        clean_content = re.sub(r'\s+', '', content)
        keys_loaded = 0
        m_gemini = re.search(r'GEMINI_KEY=(.*?)(?:FUGLE_KEY|FINMIND_KEY|$)', clean_content, re.IGNORECASE)
        m_fugle = re.search(r'FUGLE_KEY=(.*?)(?:GEMINI_KEY|FINMIND_KEY|$)', clean_content, re.IGNORECASE)
        m_finmind = re.search(r'FINMIND_KEY=(.*?)(?:GEMINI_KEY|FUGLE_KEY|$)', clean_content, re.IGNORECASE)
        
        if m_gemini and m_gemini.group(1):
            st.session_state.api_key = m_gemini.group(1)
            keys_loaded += 1
        if m_fugle and m_fugle.group(1):
            st.session_state.fugle_key = m_fugle.group(1)
            keys_loaded += 1
        if m_finmind and m_finmind.group(1):
            st.session_state.finmind_key = m_finmind.group(1)
            keys_loaded += 1
            
        if keys_loaded > 0:
            st.success(f"✅ 成功載入 {keys_loaded} 組金鑰！密碼框已自動填滿，請點擊下方「🔄 重新整理快取」套用。")
        else:
            st.error("❌ 找不到有效的金鑰，請確認檔案格式是否正確。")

    st.markdown("---")
    st.markdown("### 🧠 AI 聯網議題選股")
    topic_q = st.text_input("輸入議題 (如: 代理人AI、矽光子)")
    
    ai_model_option = st.radio("選擇 AI 大腦", [
        "Gemini 2.5 Flash", 
        "Gemini 2.5 Pro",
        "Gemini 3 Flash Preview",
        "Gemini 3.1 Flash-Lite Preview",
        "Gemini 3.1 Pro Preview (付費版)"
    ], key="ai_model_radio")
    
    st.session_state.api_key = st.text_input("🔑 Gemini API Key", type="password", value=st.session_state.api_key)
    
    if st.button("AI 實時推演分析", type="primary", use_container_width=True):
        if topic_q and st.session_state.api_key:
            st.session_state.selected_model = get_selected_model_id()
            st.session_state.topic_results = "LOADING"
            st.session_state.ai_industry_result = None
            st.session_state.run_screener = False
            st.rerun()
            
    st.markdown("---")
    st.markdown("### ⚔️ 產業同業 PK")
    if st.button("🤖 尋找同業競爭對手並 PK", use_container_width=True):
        if not st.session_state.api_key: st.warning("請先輸入您的 API Key。")
        else: st.session_state.show_pk = True; st.rerun()

    st.markdown("---")
    st.markdown("### 📈 進階資料源設定")
    st.session_state.fugle_key = st.text_input("🔑 Fugle (富果) API Key (選填)", type="password", value=st.session_state.fugle_key)
    st.session_state.finmind_key = st.text_input("🔑 FinMind API Key (選填)", type="password", value=st.session_state.finmind_key)

    def log_data_health(source, ok, status_code=None):
        src = str(source).strip()
        if not src:
            return
        if 'data_health_stats' not in st.session_state:
            st.session_state.data_health_stats = {
                "Yahoo": {"last_success": None, "error_count": 0, "last_status": "N/A"},
                "Fugle": {"last_success": None, "error_count": 0, "last_status": "N/A"},
                "FinMind": {"last_success": None, "error_count": 0, "last_status": "N/A"},
                "Gemini": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            }
        stats = st.session_state.data_health_stats
        if src not in stats:
            stats[src] = {"last_success": None, "error_count": 0, "last_status": "N/A"}

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = stats[src]
        s["last_status"] = str(status_code) if status_code is not None else ("OK" if ok else "ERR")
        if ok:
            s["last_success"] = now_str
        else:
            s["error_count"] = int(s.get("error_count", 0)) + 1
        stats[src] = s
        st.session_state.data_health_stats = stats

    f_ok, m_ok = validate_api_keys(st.session_state.fugle_key, st.session_state.finmind_key)
    
    if st.session_state.fugle_key:
        if f_ok: st.success("✅ 富果 API 連線成功")
        else: st.error("❌ 富果金鑰無效或已過期")
        
    if st.session_state.finmind_key:
        if m_ok: st.success("✅ FinMind API 連線成功")
        else: st.error("❌ FinMind 金鑰無效")

    st.markdown("---")
    st.markdown("### 🩺 Data Health Panel")
    health = st.session_state.get("data_health_stats", {})
    def fmt_health_status(raw_status):
        rs = str(raw_status).upper() if raw_status is not None else "N/A"
        if rs == "N/A":
            return "— 尚未呼叫"
        if rs in ["200", "OK", "TRUE"]:
            return f"✅ 成功 ({raw_status})"
        if rs in ["ERR", "FALSE"]:
            return "❌ 連線錯誤 (ERR)"
        return f"⚠️ 失敗 ({raw_status})"

    if health:
        for src in ["Yahoo", "Fugle", "FinMind", "Gemini"]:
            s = health.get(src, {"last_success": None, "error_count": 0, "last_status": "N/A"})
            last_ok = s.get("last_success") or "尚無"
            err_cnt = s.get("error_count", 0)
            last_st = s.get("last_status", "N/A")
            st.markdown(
                f"- **{src}**｜最近狀態: `{fmt_health_status(last_st)}`｜錯誤次數: `{err_cnt}`\n"
                f"  - 最後成功時間: `{last_ok}`"
            )
    else:
        st.info("尚無來源健康資料。")
        
    st.markdown("---")
    if st.button("🔄 重新整理快取", use_container_width=True):
        st.cache_data.clear(); st.rerun()

# ==========================================
# 5. 主畫面開始
# ==========================================
st.markdown("## 📈 台股聯網 AI 投資戰情室")

if st.session_state.fugle_key and not f_ok:
    st.error("🚨 **系統警報**：您輸入的「富果 (Fugle) API Key」驗證失敗！請至左側欄檢查金鑰是否輸入正確。")
if st.session_state.finmind_key and not m_ok:
    st.error("🚨 **系統警報**：您輸入的「FinMind API Key」驗證失敗！請至左側欄檢查金鑰是否輸入正確。")

if st.session_state.topic_results == "LOADING":
    with st.spinner(f"🤖 AI 正在連線推演「{topic_q}」..."):
        data, links = get_ai_analysis_final(topic_q, st.session_state.api_key, st.session_state.get('selected_model', 'gemini-2.5-flash'))
        if isinstance(data, dict):
            st.session_state.topic_results = {"data": data, "links": links, "topic": topic_q}
            st.session_state.show_whale = False
            st.rerun()
        else:
            st.error(f"AI 解析失敗或逾時無回應。\n\n詳細原因：{data}")
            st.session_state.topic_results = None

if isinstance(st.session_state.topic_results, dict):
    t = st.session_state.topic_results
    st.success("✅ AI 議題推演完成！系統已為您捕捉以下關聯受惠股，點擊按鈕即可一鍵切換至該檔股票的戰情室面板！")
    
    ai_topic_html = f"""
    <div style='background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FFD700;'>
        <h3 style='color: white; margin-top: 0;'>💡 議題動態推演：【{t['topic']}】</h3>
        <div style='color: #e0e0e0; font-size: 1.05rem; line-height: 1.6;'>{t['data'].get('reasoning', '無分析內容')}</div>
    </div>
    """
    st.markdown(clean_html(ai_topic_html), unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🛡️ 潛力權值股 (點擊切換)")
        for s in [x for x in t['data'].get('stocks', []) if "權值" in x.get('type', '') or "潛力" in x.get('type', '')]:
            st.button(f"📌 {s.get('name', '未知')} ({s.get('id', '')})", on_click=reset_all_states_on_stock_change, args=(s.get('id', ''),), key=f"tp_{s.get('id', '')}", use_container_width=True)
            st.caption(f"理由：{s.get('why', '')}")
    with c2:
        st.markdown("#### 🚀 爆發中小型股 (點擊切換)")
        for s in [x for x in t['data'].get('stocks', []) if "中小" in x.get('type', '') or "爆發" in x.get('type', '')]:
            st.button(f"🔥 {s.get('name', '未知')} ({s.get('id', '')})", on_click=reset_all_states_on_stock_change, args=(s.get('id', ''),), key=f"ts_{s.get('id', '')}", use_container_width=True)
            st.caption(f"理由：{s.get('why', '')}")
            
    if t['links']:
        with st.expander("🔗 查看 AI 參考來源"):
            for link in t['links']: st.markdown(f"- [{link}]({link})")
    st.markdown("---")

if st.session_state.show_whale:
    st.markdown("### 🐳 近兩周大戶持股比例顯著增加標的")
    whales = [("2317", "鴻海"), ("2382", "廣達"), ("1519", "華城"), ("6669", "緯穎"), ("3324", "雙鴻")]
    cols = st.columns(5)
    for idx, (code, name) in enumerate(whales):
        with cols[idx]: st.button(f"{name}\n({code})", on_click=reset_all_states_on_stock_change, args=(code,), key=f"w_{code}", use_container_width=True)
    st.markdown("---")

curr_id = st.session_state.selected_stock
if curr_id:
    with st.spinner('同步數據中...'):
        hist, info = get_stock_data(curr_id, st.session_state.fugle_key, st.session_state.finmind_key)
        if info is None: info = {}
        c_name = get_chinese_name(curr_id) or info.get('shortName', curr_id)

    if hist is not None and not hist.empty:
        col_title, col_star = st.columns([0.85, 0.15])
        with col_title: st.markdown(f"### 🏢 {c_name} ({curr_id})")
        with col_star:
            in_watch = curr_id in get_watchlist()
            btn_label = "⭐ 移除自選" if in_watch else "☆ 加入自選"
            if st.button(btn_label, use_container_width=True):
                toggle_watchlist(curr_id, c_name)
                st.rerun()

        sector_disp = SECTOR_MAP.get(info.get('sector', '未知'), info.get('sector', '未知'))
        st.markdown(f"**🏷️ 產業分類：** {sector_disp} / {info.get('industry', '未知')}")
        with st.expander("📖 查看公司詳細營業項目簡介 (自動英翻中)"):
            st.write(translate_to_zh(info.get('longBusinessSummary', '暫無簡介。')))

        # ==========================================
        # ⚡ 即時報價
        # ==========================================
        st.markdown("#### ⚡ 即時報價與交易資訊")
        today_data = hist.iloc[-1]
        prev_data = hist.iloc[-2] if len(hist) > 1 else today_data
        
        curr_p = s_float(today_data.get('Close'), 0)
        open_p = s_float(today_data.get('Open'), 0)
        high_p = s_float(today_data.get('High'), 0)
        low_p = s_float(today_data.get('Low'), 0)
        vol_shares = s_float(today_data.get('Volume'), 0)
        
        vol_lots = int(vol_shares // 1000) if vol_shares else 0
        prev_vol_lots = int(s_float(prev_data.get('Volume'), 0) // 1000) if len(hist) > 1 else 0
        
        prev_close = s_float(info.get('previousClose'), s_float(prev_data.get('Close'), 0))
        change = curr_p - prev_close if prev_close else 0
        change_pct = (change / prev_close) * 100 if prev_close else 0
        amp = ((high_p - low_p) / prev_close) * 100 if prev_close and prev_close > 0 else 0
        avg_price = (high_p + low_p + curr_p) / 3 if curr_p else 0
        turnover_100m = (vol_shares * avg_price) / 100000000
        
        def get_color(val, base):
            if val > base: return "#ff4d4d"
            elif val < base: return "#00cc66"
            return "#ffffff"
            
        c_curr = get_color(curr_p, prev_close)
        c_open = get_color(open_p, prev_close)
        c_high = get_color(high_p, prev_close)
        c_low = get_color(low_p, prev_close)
        c_change = get_color(change, 0)
        arrow = "▲" if change > 0 else ("▼" if change < 0 else "")
        
        quote_html = f"""
        <style>
        .q-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 30px; background: #1e1e1e; padding: 15px 20px; border-radius: 8px; font-family: sans-serif; margin-bottom: 20px; border: 1px solid #333; }}
        .q-item {{ display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 4px; }}
        .q-label {{ color: #aaa; font-size: 1rem; }}
        .q-val {{ font-weight: bold; font-size: 1.1rem; }}
        </style>
        <div class="q-container">
            <div class="q-item"><span class="q-label">成交</span><span class="q-val" style="color: {c_curr};">{curr_p:,.2f}</span></div>
            <div class="q-item"><span class="q-label">昨收</span><span class="q-val" style="color: #fff;">{prev_close:,.2f}</span></div>
            <div class="q-item"><span class="q-label">開盤</span><span class="q-val" style="color: {c_open};">{open_p:,.2f}</span></div>
            <div class="q-item"><span class="q-label">漲跌幅</span><span class="q-val" style="color: {c_change};">{arrow} {abs(change_pct):.2f}%</span></div>
            <div class="q-item"><span class="q-label">最高</span><span class="q-val" style="color: {c_high};">{high_p:,.2f}</span></div>
            <div class="q-item"><span class="q-label">漲跌</span><span class="q-val" style="color: {c_change};">{arrow} {abs(change):.2f}</span></div>
            <div class="q-item"><span class="q-label">最低</span><span class="q-val" style="color: {c_low};">{low_p:,.2f}</span></div>
            <div class="q-item"><span class="q-label">總量 (張)</span><span class="q-val" style="color: #ffd700;">{vol_lots:,}</span></div>
            <div class="q-item"><span class="q-label">均價</span><span class="q-val" style="color: #fff;">{avg_price:,.2f}</span></div>
            <div class="q-item"><span class="q-label">昨量 (張)</span><span class="q-val" style="color: #fff;">{prev_vol_lots:,}</span></div>
            <div class="q-item"><span class="q-label">成交金額(億)</span><span class="q-val" style="color: #fff;">{turnover_100m:,.2f}</span></div>
            <div class="q-item"><span class="q-label">振幅</span><span class="q-val" style="color: #fff;">{amp:.2f}%</span></div>
        </div>
        """
        st.markdown(clean_html(quote_html), unsafe_allow_html=True)

        # ==========================================
        # 🌍 國際連動與動態時間趨勢推估
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        trend_data = get_global_market_trend()
        if trend_data:
            target_day_text = trend_data.get('target_day', '明日')
            time_status_text = trend_data.get('time_status', '')
            st.markdown(f"#### 🌍 國際連動與{target_day_text}趨勢推估 {time_status_text}", unsafe_allow_html=True)
            
            def c_color(v): return "#ff4d4d" if v > 0 else "#00cc66" if v < 0 else "#fff"
            trend_html = f"""
            <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {trend_data['color']}; margin-bottom: 20px; border-top:1px solid #333; border-right:1px solid #333; border-bottom:1px solid #333;'>
                <div style='font-size:1.15rem; font-weight:bold; color:{trend_data['color']}; margin-bottom:10px;'>{trend_data['trend']}</div>
                <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;'>
                    <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>費城半導體 (^SOX)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["sox_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["sox"])};'>({trend_data["sox"]:+.2f}%)</span></div>
                    <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台積電 ADR (TSM)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["tsm_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["tsm"])};'>({trend_data["tsm"]:+.2f}%)</span></div>
                    <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>納斯達克期貨 (NQ=F)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["nq_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["nq"])};'>({trend_data["nq"]:+.2f}%)</span></div>
                    <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台股 ETF (EWT)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["ewt_p"]:,.2f}</b> <span style='font-size:1rem; color:{c_color(trend_data["ewt"])};'>({trend_data["ewt"]:+.2f}%)</span></div>
                </div>
            </div>
            """
            st.markdown(clean_html(trend_html), unsafe_allow_html=True)

        # ==========================================
        # 💼 財務基本面與獲利基準微調
        # ==========================================
        col_fin_title, col_fin_btn = st.columns([0.6, 0.4])
        with col_fin_title:
            st.markdown("#### 💼 財務基本面與獲利基準微調")
        with col_fin_btn:
            if st.button("🪄 啟動 AI 全方位校對與補齊財報", disabled=not st.session_state.api_key, use_container_width=True, help="點此讓 AI 上網搜尋最新財報與估值指標，並與現有資料進行比對"):
                with st.spinner("AI 正在聯網為您強行抓取最新財報數據，請稍候... (約需 30-45 秒)"):
                    selected_model = get_selected_model_id()
                    fetched_data = get_financials_from_ai(c_name, curr_id, st.session_state.api_key, selected_model)
                    
                    if isinstance(fetched_data, dict) and "error" not in fetched_data:
                        fetched_data['model_used'] = st.session_state.get('ai_model_radio', 'Gemini 2.5 Flash')
                        st.session_state.ai_fetched_financials[curr_id] = fetched_data
                        st.rerun()
                    elif isinstance(fetched_data, dict) and "error" in fetched_data:
                        st.error(f"🚨 AI 抓取失敗：{fetched_data['error']}")
                    else:
                        st.error("🚨 AI 暫時無法找到確切數據，或請求遭拒。")

            temp_ai_fin = st.session_state.ai_fetched_financials.get(curr_id, {})
            has_ai_fin_fetch = bool(temp_ai_fin)
            if temp_ai_fin.get('model_used'):
                st.markdown(f"<div style='text-align:right; color:#FFD700; font-size:0.85rem; margin-top:5px;'>🤖 驅動核心: <b>{temp_ai_fin['model_used']}</b></div>", unsafe_allow_html=True)
                raw_state_key = f"show_ai_raw_panel_{curr_id}"
                if raw_state_key not in st.session_state:
                    st.session_state[raw_state_key] = False

                btn_label = "🧾 隱藏本次 AI 查詢與回報資料" if st.session_state[raw_state_key] else "🧾 顯示本次 AI 查詢與回報資料"
                if st.button(btn_label, key=f"toggle_ai_raw_btn_{curr_id}", use_container_width=True):
                    st.session_state[raw_state_key] = not st.session_state[raw_state_key]
                    st.rerun()

                if st.session_state[raw_state_key]:
                    st.caption("以下為本次 AI 全方位校對與補齊財報的查詢內容與原始回報：")
                    query_preview = temp_ai_fin.get("query_payload")
                    if query_preview:
                        st.code(query_preview, language="json")
                    st.json(temp_ai_fin)
                        
        df_rev_bk = get_monthly_revenue(curr_id, st.session_state.finmind_key)
        df_per_bk = get_pe_pb_data(curr_id, st.session_state.finmind_key)
        fm_health = get_finmind_financial_health(curr_id, st.session_state.finmind_key)
        
        if df_rev_bk is not None and not df_rev_bk.empty:
            latest_rev_month = df_rev_bk['Month'].iloc[-1]
            latest_mom_val = s_float(df_rev_bk['MoM'].iloc[-1])
        else:
            latest_rev_month = "無資料"
            latest_mom_val = None
        
        pe_ratio = s_float(info.get('trailingPE'))
        if (pe_ratio is None or pe_ratio > 1000) and df_per_bk is not None and not df_per_bk.empty:
            if (pd.Timestamp.today() - df_per_bk.iloc[-1]['date']).days < 30: pe_ratio = s_float(df_per_bk['PER'].iloc[-1])
        pb_ratio = s_float(info.get('priceToBook'))
        if (pb_ratio is None or pb_ratio > 500) and df_per_bk is not None and not df_per_bk.empty and 'PBR' in df_per_bk.columns:
            pb_ratio = s_float(df_per_bk['PBR'].iloc[-1])
            
        roe = s_float(info.get('returnOnEquity'))
        sys_de = s_float(info.get('debtToEquity'))
        if sys_de is not None: sys_de = sys_de / 100.0  
        
        gross_margin = s_float(info.get('grossMargins'))
        op_margin = s_float(info.get('operatingMargins'))
        
        if gross_margin is None: gross_margin = fm_health.get('grossMargins')
        if op_margin is None: op_margin = fm_health.get('operatingMargins')
        if sys_de is None: sys_de = fm_health.get('debtToEquity')
        
        rev_growth = s_float(info.get('revenueGrowth'))
        if rev_growth is None and df_rev_bk is not None and not df_rev_bk.empty:
            rev_growth = s_float(df_rev_bk['YoY'].iloc[-1]) / 100.0
        earn_growth = s_float(info.get('earningsGrowth'))
        
        t_eps = s_float(info.get('trailingEps'))
        if t_eps is None and pe_ratio is not None and pe_ratio > 0 and curr_p > 0:
            t_eps = curr_p / pe_ratio
            
        sys_f_eps_calc = s_float(info.get('forwardEps'))

        if pe_ratio is None and t_eps is None and not st.session_state.ai_fetched_financials.get(curr_id):
            st.warning("⚠️ **全球連線受阻**：目前免費資料庫限制了部分股票的抓取。👉 **解決方案**：請點擊上方【🪄 啟動 AI 全方位校對與補齊財報】讓 AI 強制為您抓回最新外資預估！")
        
        ai_fin = st.session_state.ai_fetched_financials.get(curr_id, {})
        ai_pe = s_float(ai_fin.get('pe'))
        ai_pb = s_float(ai_fin.get('pb'))
        ai_t_eps = s_float(ai_fin.get('trailing_eps'))
        ai_f_eps_calc = s_float(ai_fin.get('forward_eps'))
        ai_yoy = s_float(ai_fin.get('yoy'))
        ai_gm = s_float(ai_fin.get('gross_margin'))
        ai_om = s_float(ai_fin.get('operating_margin'))
        ai_roe = s_float(ai_fin.get('roe'))
        ai_de = s_float(ai_fin.get('debt_to_equity'))
        
        # 🚀 接收 AI 抓到的目標價、MoM 與 Dividend Yield，並覆蓋錯誤資料
        ai_target_price = s_float(ai_fin.get('target_price'))
        
        ai_mom = s_float(ai_fin.get('mom'))
        if ai_mom is not None: 
            latest_mom_val = ai_mom * 100
        
        if latest_mom_val is not None:
            latest_mom_str = f"{latest_mom_val:.2f}%"
        else:
            latest_mom_str = "N/A"
            
        ai_dy = s_float(ai_fin.get('dividend_yield'))
        
        raw_ai_period = str(ai_fin.get('data_period', '')).replace('None', '').strip()
        ai_suffix = f"AI({raw_ai_period})" if raw_ai_period else "AI捉取"

        eff_pe = pe_ratio if pe_ratio is not None else ai_pe
        eff_pb = pb_ratio if pb_ratio is not None else ai_pb
        eff_t_eps = t_eps if t_eps is not None else ai_t_eps
        eff_rg = rev_growth if rev_growth is not None else ai_yoy
        eff_eg = earn_growth if earn_growth is not None else ai_yoy
        eff_gm = gross_margin if gross_margin is not None else ai_gm
        eff_om = op_margin if op_margin is not None else ai_om
        eff_roe = roe if roe is not None else ai_roe
        eff_de = sys_de if sys_de is not None else ai_de

        if eff_pe and eff_pe > 0 and eff_pb and eff_pb > 0:
            eff_roe = eff_pb / eff_pe
            roe = eff_roe 
            
        if ai_pe and ai_pe > 0 and ai_pb and ai_pb > 0:
            ai_roe = ai_pb / ai_pe
        
        if ai_f_eps_calc is None and eff_t_eps is not None and eff_eg is not None and -1 <= eff_eg <= 5:
            ai_f_eps_calc = eff_t_eps * (1 + eff_eg)
            
        if sys_f_eps_calc is None and t_eps is not None and earn_growth is not None and -1 <= earn_growth <= 5:
            sys_f_eps_calc = t_eps * (1 + earn_growth)

        # ==========================================
        # 🚀 財務儀表板 (乾淨版)
        # ==========================================
        col_eps1, col_eps2 = st.columns([1, 1])
        with col_eps1:
            target_peg_adj = st.selectbox(
                "🎯 估值情境 (目標 PEG)", 
                [1.0, 1.2, 1.5], 
                format_func=lambda x: "保守 (1.0x)" if x==1.0 else ("穩健 (1.2x)" if x==1.2 else "樂觀高空 (1.5x)"),
                index=0,
                help="教練密技：目標價逆推公式的乘數。大盤熱度高或作夢空間大時可調升至 1.5。"
            )
        with col_eps2:
            suggested_cap = 30.0
            cap_reason = "預設 30x (無毛利率數據)"
            if eff_gm is not None:
                if eff_gm >= 0.50:
                    suggested_cap, cap_reason = 40.0, "建議 40x (高毛利>50%: 軟體/IP/專利壟斷)"
                elif eff_gm >= 0.30:
                    suggested_cap, cap_reason = 30.0, "建議 30x (中高毛利>30%: 高階零組件/利基型)"
                elif eff_gm >= 0.15:
                    suggested_cap, cap_reason = 20.0, "建議 20x (穩健毛利>15%: 傳統優質硬體/代工)"
                else:
                    suggested_cap, cap_reason = 15.0, "建議 15x (低毛利<15%: 紅海競爭/純組裝)"
            
            summary_text = info.get('longBusinessSummary', '') + c_name + info.get('industry', '') + sector_disp
            ai_keywords = ["AI", "伺服器", "CoWoS", "矽光子", "散熱", "CPO", "先進封裝", "半導體設備", "水冷", "ASIC", "資料中心", "輝達", "Nvidia"]
            if any(kw.lower() in summary_text.lower() for kw in ai_keywords):
                suggested_cap += 15.0
                cap_reason += "<br>🚀 <span style='color:#ff4d4d;'>偵測到 AI/先進製程題材，Cap 強制上調 +15x</span>"
                
            if df_per_bk is not None and not df_per_bk.empty:
                recent_date = pd.Timestamp.today() - pd.DateOffset(years=2)
                recent_df = df_per_bk[df_per_bk['date'] >= recent_date]
                if not recent_df.empty:
                    valid_pe = recent_df[recent_df['PER'] < 300]['PER']
                    if not valid_pe.empty:
                        hist_high_pe = valid_pe.quantile(0.9)
                        if hist_high_pe > suggested_cap + 5:
                            suggested_cap = float(math.ceil(hist_high_pe / 5) * 5)
                            cap_reason += f"<br>📈 <span style='color:#FFD700;'>近兩年 AI 週期高位達 {hist_high_pe:.1f}x，動態釋放天花板！</span>"
            
            target_pe_cap = st.number_input("⚙️ 動態本益比天花板 (Cap)", value=float(suggested_cap), step=5.0, help="防禦低基期失真陷阱！系統已根據毛利率與產業題材自動調整合理的極限本益比。")
            st.markdown(f"<div style='color:#00bfff; font-size:0.75rem; margin-top:-10px; line-height:1.2;'>💡 {cap_reason}</div>", unsafe_allow_html=True)

        is_base_normalized = False 

        eff_f_eps = sys_f_eps_calc
        eps_source_text = f"海外系統或反推 ({eff_f_eps:.2f}元)" if eff_f_eps is not None else "系統預估 (無資料)"
        f_eps_display = build_cmp_dual_str(t_eps, sys_f_eps_calc, ai_t_eps, ai_f_eps_calc, 'num', 'num', 'AI推估', show_ai_missing=has_ai_fin_fetch)
        
        sys_forward_pe = s_float(info.get('forwardPE'))
        if sys_forward_pe is None and eff_f_eps is not None and eff_f_eps > 0: sys_forward_pe = curr_p / eff_f_eps
        
        ai_fpe = curr_p / ai_f_eps_calc if ai_f_eps_calc and ai_f_eps_calc > 0 else None
