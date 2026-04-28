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

from utils import s_float

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
            data = res.json().get('data', [])
            if data:
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['date'])
                df.set_index('Date', inplace=True)
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                return df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
    except: pass
    return pd.DataFrame()

def get_financials_from_ai(stock_name, stock_id, api_key, model_name="gemini-2.5-flash"):
    if not api_key: return {"error": "未提供 API Key"}
    api_key = api_key.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    current_year = datetime.date.today().year
    target_year = current_year if datetime.date.today().month < 9 else current_year + 1
    
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

    必須嚴格回傳包含上述 13 個欄位的 JSON 格式。百分比請轉換為小數，數值請直接輸出數字。若查無資料，該欄位請填 null。
    絕對不要輸出 markdown 標記或其他文字。"""
    
    payload = {
        "contents": [{"parts": [{"text": f"請啟提搜尋引擎，查詢台股 {stock_name} ({stock_id}) 最新財報新聞、營收 MoM，以及 {target_year} 法人預測 EPS 與 最新目標價"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "tools": [{"google_search": {}}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
        
        if res.status_code != 200:
            return {"error": f"API 連線被拒絕 (代碼 {res.status_code})。細節：{res.text[:150]}"}
            
        text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        s_idx = text.find('{')
        e_idx = text.rfind('}')
        if s_idx != -1 and e_idx != -1:
            clean_text = text[s_idx:e_idx+1]
            return json.loads(clean_text)
        else:
            return {"error": "AI 回傳的格式不正確，無法萃取 JSON 資料。"}
    except requests.exceptions.Timeout:
        return {"error": "連線逾時 (超過 60 秒)，請稍後再試。"}
    except Exception as e: 
        return {"error": f"發生未預期的例外狀況：{str(e)}"}

@st.cache_data(ttl=86400)
def get_peers_from_ai(stock_name, stock_id, api_key):
    if not api_key: return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": f"請尋找 {stock_name} ({stock_id}) 的同業競爭對手"}]}], 
        "systemInstruction": {"parts": [{"text": "請列出與目標公司核心業務最直接競爭的 3~5 家台股上市櫃公司代號。必須是純數字 JSON 陣列格式：[\"2383\", \"3044\"]。絕對不要輸出其他文字。"}]},
        "tools": [{"google_search": {}}]
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
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
        "tools": [{"google_search": {}}]
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=90)
        fallback_msg = ""
        if res.status_code == 404 and model_name != "gemini-2.5-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
            res = requests.post(fallback_url, headers={"Content-Type": "application/json"}, json=payload, timeout=90)
            fallback_msg = f"> 💡 **系統提示**：您指定的 `{model_name}` 尚未開放或輸入錯誤，系統已自動降級使用 `Gemini 2.5 Flash` 為您完成分析。\n\n---\n\n"
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
        "tools": [{"google_search": {}}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 404 and model_name != "gemini-2.5-flash":
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            response = requests.post(fallback_url, headers=headers, json=payload, timeout=60)
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
        data = res.json()
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
            data_str = json_match.group(1)
            def ext_val(key, is_pct=False):
                safe_area = data_str[:len(data_str)//2]
                m = re.search(rf'"{key}"\s*:\s*(?:{{"raw"\s*:\s*)?"?([+-]?\d+(?:\.\d+)?)"?', safe_area)
                if m: return float(m.group(1)) / 100.0 if is_pct else float(m.group(1))
                return None
            info['trailingPE'] = ext_val('peRatio') or ext_val('trailingPE')
            info['priceToBook'] = ext_val('pbRatio') or ext_val('priceToBook')
            info['trailingEps'] = ext_val('eps') or ext_val('trailingEps')
            info['dividendYield'] = ext_val('dividendYield', True)
            
            info['targetHighPrice'] = ext_val('targetHighPrice')
            info['targetMeanPrice'] = ext_val('targetMeanPrice')
            info['targetLowPrice'] = ext_val('targetLowPrice')

        def fuzzy_ext(keyword, is_pct=False):
            idx = text.find(keyword)
            if idx != -1:
                matches = re.findall(r'>\s*([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(%)?\s*<', text[idx:idx+300])
                if matches:
                    try: return float(matches[0][0].replace(',', '')) / 100.0 if is_pct or matches[0][1] == '%' else float(matches[0][0].replace(',', ''))
                    except: pass
            return None

        if 'trailingPE' not in info or not info['trailingPE']: info['trailingPE'] = fuzzy_ext('本益比')
        if 'priceToBook' not in info or not info['priceToBook']: info['priceToBook'] = fuzzy_ext('股價淨值比')
        if 'trailingEps' not in info or not info['trailingEps']: info['trailingEps'] = fuzzy_ext('EPS')
        if 'dividendYield' not in info or not info['dividendYield']: info['dividendYield'] = fuzzy_ext('殖利率', True)
        
        info['grossMargins'] = fuzzy_ext('毛利率', True) or fuzzy_ext('營業毛利率', True)
        info['operatingMargins'] = fuzzy_ext('營業利益率', True) or fuzzy_ext('營益率', True)
        info['returnOnEquity'] = fuzzy_ext('ROE', True) or fuzzy_ext('權益報酬率', True)
        
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
