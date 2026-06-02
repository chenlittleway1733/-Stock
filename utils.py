"""
共用常數、格式化工具、自選股與 Streamlit Session State 管理。
由原始 app(1).py 拆分而來。
"""
import os
import re
import math
import datetime
import pandas as pd
import streamlit as st

# --- 產業對照表 ---
SECTOR_MAP = {
    "Technology": "科技產業", "Semiconductors": "半導體業", "Consumer Electronics": "消費性電子",
    "Electronic Components": "電子零組件", "Computer Hardware": "電腦及週邊設備",
    "Communication Equipment": "通信網路業", "Software—Infrastructure": "軟體服務業",
    "Financials": "金融保險業", "Banks—Regional": "銀行業", "Life Insurance": "人壽保險",
    "Industrials": "工業", "Marine Shipping": "航運業", "Airlines": "航空業",
    "Auto Parts": "汽車零組件", "Healthcare": "生技醫療業", "Real Estate": "建材營造業",
    "Basic Materials": "原物料/塑化", "Energy": "能源產業", "Utilities": "公用事業"
}



def log_exception(source, context, exc=None):
    """
    集中記錄非致命例外：避免 except: pass 吃掉錯誤。
    - source：資料源或模組名稱，例如 Yahoo / Fugle / FinMind / Gemini / Utils
    - context：發生錯誤的函式或流程
    - exc：例外物件
    """
    src = str(source or "Unknown").strip()
    ctx = str(context or "unknown_context").strip()
    msg = str(exc)[:200] if exc is not None else "unknown error"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event = {"time": now_str, "source": src, "context": ctx, "error": msg}

    try:
        if "error_events" not in st.session_state:
            st.session_state.error_events = []
        st.session_state.error_events.append(event)
        st.session_state.error_events = st.session_state.error_events[-30:]
    except Exception:
        return event
    return event

# ==========================================
# 1. 全局安全轉換與排版函數
# ==========================================
def s_float(val, default=None):
    try:
        if val is None: return default
        v = float(val)
        if math.isnan(v) or math.isinf(v): return default
        return v
    except (TypeError, ValueError, OverflowError):
        return default

def to_pct(val):
    try:
        if val is None or pd.isna(val): return "N/A"
        return f"{val * 100:.2f}%"
    except (TypeError, ValueError, OverflowError):
        return "N/A"

def to_val_str(v, fmt="pct"):
    if v is None or pd.isna(v): return "N/A"
    if fmt == "pct": return f"{v * 100:.2f}%"
    if fmt == "x": return f"{v:.1f}x"
    return f"{v:.2f}"

def p_fmt(orig, ai_val, fmt="pct", suffix="AI捉取"):
    s = to_val_str(orig, fmt)
    if ai_val is not None and not pd.isna(ai_val):
        s += f" ({to_val_str(float(ai_val), fmt)}, {suffix})"
    return s

def p_dual(o1, o2, a1, a2, suffix="AI捉取"):
    s = f"{to_val_str(o1, 'num')} / {to_val_str(o2, 'num')}"
    if (a1 is not None and not pd.isna(a1)) or (a2 is not None and not pd.isna(a2)):
        sa1 = to_val_str(float(a1) if a1 is not None else None, 'num')
        sa2 = to_val_str(float(a2) if a2 is not None else None, 'num')
        s += f" ({sa1} / {sa2}, {suffix})"
    return s

def build_cmp_str(orig, ai_val, fmt="pct", suffix="AI推估", show_ai_missing=False, period=""):
    s = to_val_str(orig, fmt)
    if ai_val is not None and not pd.isna(ai_val):
        ai_text = to_val_str(float(ai_val), fmt)
    elif show_ai_missing:
        ai_text = "AI找不到數據"
    else:
        return s
    
    time_str = f", {period}" if period else ""
    s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({suffix}: {ai_text}{time_str})</span>"
    return s

def build_cmp_dual_str(o1, o2, a1, a2, fmt1="num", fmt2="num", suffix="AI推估", show_ai_missing=False, period=""):
    s1 = to_val_str(o1, fmt1)
    s2 = to_val_str(o2, fmt2)
    s = f"{s1} / <span style='color:#00bfff;'>{s2}</span>" if (fmt1=="num" and fmt2=="num") else f"{s1} / {s2}"
    has_ai = ((a1 is not None and not pd.isna(a1)) or (a2 is not None and not pd.isna(a2)))
    if not has_ai and not show_ai_missing:
        return s
    sa1 = to_val_str(float(a1) if a1 is not None and not pd.isna(a1) else None, fmt1)
    sa2 = to_val_str(float(a2) if a2 is not None and not pd.isna(a2) else None, fmt2)
    if sa1 == "N/A":
        sa1 = "AI找不到數據"
    if sa2 == "N/A":
        sa2 = "AI找不到數據"
        
    time_str = f", {period}" if period else ""
    s += f"<br><span style='color:#FFD700; font-size:0.85rem;'>({suffix}: {sa1} / {sa2}{time_str})</span>"
    return s

def clean_html(html_str):
    return re.sub(r'[\r\n\t]+', ' ', html_str).strip()



def format_quality_value(val, fmt="num"):
    """資料品質表專用格式化：避免 UI 端重複處理百分比/倍數/金額。"""
    if val is None:
        return "NULL"
    try:
        if pd.isna(val):
            return "NULL"
    except Exception:
        pass
    try:
        v = float(val)
        if fmt == "pct":
            return f"{v * 100:.2f}%"
        if fmt == "x":
            return f"{v:.2f}x"
        if fmt == "price":
            return f"{v:,.2f}"
        if fmt == "int":
            return f"{v:,.0f}"
        return f"{v:,.2f}"
    except Exception:
        text = str(val).strip()
        return text if text else "NULL"


def get_ai_field_source_meta(ai_fin, field_key):
    """取得 AI 單一財務欄位的來源資訊。相容 _ai_source_trace、_sources、field_sources。"""
    if not isinstance(ai_fin, dict) or not field_key:
        return {}
    trace = ai_fin.get("_ai_source_trace") or ai_fin.get("_sources") or ai_fin.get("field_sources") or {}
    if not isinstance(trace, dict):
        return {}
    meta = trace.get(field_key) or {}
    if isinstance(meta, str):
        return {"source": meta}
    return meta if isinstance(meta, dict) else {}

def format_ai_source_detail(ai_fin, field_key, fallback_period="", fallback_source="AI補齊"):
    """將 AI 來源名稱與日期壓成適合放進資料品質表的文字。"""
    meta = get_ai_field_source_meta(ai_fin, field_key)
    source = str(meta.get("source") or meta.get("publisher") or fallback_source or "AI補齊").strip()
    data_period = ai_fin.get("data_period", "") if isinstance(ai_fin, dict) else ""
    date = str(meta.get("published_date") or meta.get("date") or meta.get("data_date") or meta.get("period") or fallback_period or data_period or "").strip()
    note = str(meta.get("note") or "").strip()
    parts = [source]
    if date:
        parts.append(date)
    if note:
        parts.append(note[:40])
    return "｜".join([x for x in parts if x])

def get_ai_source_url(ai_fin, field_key):
    """取得 AI 單一欄位來源網址；若單欄未提供，回傳空字串。"""
    meta = get_ai_field_source_meta(ai_fin, field_key)
    return str(meta.get("source_url") or meta.get("url") or meta.get("link") or "").strip()

def build_ai_source_trace_report(ai_fin):
    """把 AI 回傳的逐欄來源整理成 DataFrame，供 UI 檢視。"""
    if not isinstance(ai_fin, dict):
        return pd.DataFrame()
    trace = ai_fin.get("_ai_source_trace") or ai_fin.get("_sources") or ai_fin.get("field_sources") or {}
    if not isinstance(trace, dict) or not trace:
        return pd.DataFrame()
    rows = []
    for key, meta in trace.items():
        if isinstance(meta, str):
            meta = {"source": meta}
        if not isinstance(meta, dict):
            continue
        rows.append({
            "欄位代碼": key,
            "欄位名稱": meta.get("label") or key,
            "AI值": format_quality_value(ai_fin.get(key), "num"),
            "來源": meta.get("source") or meta.get("publisher") or "—",
            "發布日/期間": meta.get("published_date") or meta.get("date") or meta.get("data_date") or meta.get("period") or ai_fin.get("data_period") or "—",
            "來源網址": meta.get("source_url") or meta.get("url") or meta.get("link") or "—",
            "備註": meta.get("note") or "—",
        })
    return pd.DataFrame(rows)



# ==========================================
# 1.0.1 系統 / AI 分歧警告層
# ==========================================
def _relative_gap(a, b, denominator="min"):
    """計算兩個數值的相對差距。預設以較小絕對值作為分母，符合「分歧警告」需求。"""
    a = s_float(a)
    b = s_float(b)
    if a is None or b is None:
        return None
    base_candidates = [abs(x) for x in [a, b] if x is not None and abs(x) > 1e-12]
    if not base_candidates:
        return None
    if denominator == "avg":
        base = sum(base_candidates) / len(base_candidates)
    elif denominator == "max":
        base = max(base_candidates)
    else:
        base = min(base_candidates)
    if base <= 1e-12:
        return None
    return abs(a - b) / base


def _fmt_gap_pct(gap):
    return "N/A" if gap is None else f"{gap * 100:.1f}%"


def build_divergence_warnings(
    *,
    system_forward_eps=None,
    ai_forward_eps=None,
    system_yoy=None,
    ai_yoy=None,
    system_peg=None,
    ai_peg=None,
    system_fair_value=None,
    ai_fair_value=None,
    system_de=None,
    ai_de=None,
    stock_id="",
    stock_name="",
):
    """
    建立「系統值 vs AI值」分歧警告。

    目的：
    - EPS / YoY / PEG / 合理價 / D/E 發生重大矛盾時，不讓使用者只看到單一結論。
    - 此函式只產生警告，不直接修改估值模型，避免和前面的資料校驗層互相干擾。
    """
    label = f"{stock_name} ({stock_id})" if stock_name and stock_id else (stock_name or stock_id or "目前標的")
    warnings = []

    def add(rule, message, severity="warning", system_value=None, ai_value=None, gap=None, suggestion=""):
        warnings.append({
            "規則": rule,
            "嚴重度": severity,
            "警告文字": message,
            "系統值": system_value,
            "AI值": ai_value,
            "差距": gap,
            "建議處理": suggestion or "請先確認資料口徑，再使用估值結論。",
        })

    # 1) Forward EPS 分歧：abs(system-ai)/min(abs(system),abs(ai)) > 30%
    eps_gap = _relative_gap(system_forward_eps, ai_forward_eps, "min")
    if eps_gap is not None and eps_gap > 0.30:
        add(
            "EPS 分歧",
            f"{label} 的 Forward EPS 預估分歧過大，估值可信度下降。",
            "danger" if eps_gap > 0.50 else "warning",
            format_quality_value(system_forward_eps, "num"),
            format_quality_value(ai_forward_eps, "num"),
            _fmt_gap_pct(eps_gap),
            "請優先確認 Forward EPS 是單一券商、AI 推估，還是多家法人共識；可操作估值應採較保守 EPS。",
        )

    # 2) YoY 分歧：系統 YoY 與 AI YoY 差距 > 20 個百分點
    sy = s_float(system_yoy)
    ay = s_float(ai_yoy)
    if sy is not None and ay is not None:
        yoy_gap_pp = abs(sy - ay) * 100
        if yoy_gap_pp > 20:
            add(
                "YoY 分歧",
                f"{label} 的營收年增率口徑可能混淆，請確認單月 YoY / 累計 YoY / yfinance revenueGrowth。",
                "warning",
                format_quality_value(sy, "pct"),
                format_quality_value(ay, "pct"),
                f"{yoy_gap_pp:.1f} 個百分點",
                "月營收判斷應優先採公告月份的單月 YoY；AI 若抓到累計 YoY，不能直接比較。",
            )

    # 3) PEG 矛盾：系統 PEG < 1 且 AI PEG > 3，或反向發生
    sp = s_float(system_peg)
    ap = s_float(ai_peg)
    if sp is not None and ap is not None and sp > 0 and ap > 0:
        if (sp < 1 and ap > 3) or (ap < 1 and sp > 3):
            add(
                "PEG 矛盾",
                f"{label} 的 PEG 結論矛盾，請勿直接判定低估或高估。",
                "danger",
                format_quality_value(sp, "x"),
                format_quality_value(ap, "x"),
                _fmt_gap_pct(_relative_gap(sp, ap, "min")),
                "請回頭檢查 Forward P/E 與成長率分母，特別是低基期 EPS 或 AI 成長率口徑。",
            )

    # 4) 合理價分歧：公式合理價與 AI 公式合理價差距 > 50%
    fair_gap = _relative_gap(system_fair_value, ai_fair_value, "min")
    if fair_gap is not None and fair_gap > 0.50:
        add(
            "合理價分歧",
            f"{label} 的系統公式合理價與 AI 公式合理價分歧過大，請以保守情境為主。",
            "danger" if fair_gap > 1.00 else "warning",
            format_quality_value(system_fair_value, "price"),
            format_quality_value(ai_fair_value, "price"),
            _fmt_gap_pct(fair_gap),
            "不要把公式合理價或極限價直接視為買賣目標；應等待可操作估值區間完成後再判斷。",
        )

    # 5) D/E 分歧：系統 D/E 與 AI D/E 差距 > 50%
    de_gap = _relative_gap(system_de, ai_de, "min")
    if de_gap is not None and de_gap > 0.50:
        add(
            "D/E 分歧",
            f"{label} 的負債權益比資料口徑不一致，防禦力評分應降級。",
            "warning",
            format_quality_value(system_de, "x"),
            format_quality_value(ai_de, "x"),
            _fmt_gap_pct(de_gap),
            "請確認 D/E 是倍數、百分比、還是總負債/股東權益欄位來源不同。",
        )

    return warnings


def build_divergence_warning_report(warnings):
    """將分歧警告整理成 DataFrame，供 Streamlit 顯示。"""
    return pd.DataFrame(warnings or [], columns=["規則", "嚴重度", "警告文字", "系統值", "AI值", "差距", "建議處理"])

def infer_quality_status(adopted_value, system_value=None, ai_value=None, is_stale=False, notes=""):
    """依欄位是否有採用值、是否過期、是否被校驗提醒標記，產生一致的品質狀態。"""
    note_text = str(notes or "")
    if adopted_value is None:
        return "❌ 缺資料"
    if is_stale:
        return "⚠️ 可能過期"
    high_risk_keywords = ["校驗失敗", "不合理", "已排除", "NULL", "過舊", "錯置", "幻覺"]
    if any(k in note_text for k in high_risk_keywords):
        return "⚠️ 已校正/需留意"
    if system_value is not None and ai_value is not None:
        return "✅ 系統+AI交叉"
    return "✅ 可用"


def build_financial_quality_report(rows):
    """將各欄位資料來源、AI 補值、採用值與品質狀態統一整理成 DataFrame。"""
    table = []
    for r in rows or []:
        fmt = r.get("fmt", "num")
        system_value = r.get("system_value")
        ai_value = r.get("ai_value")
        adopted_value = r.get("adopted_value")
        notes = r.get("notes", "")
        table.append({
            "資料欄位": r.get("field", ""),
            "系統來源": r.get("system_source", "系統"),
            "系統值": format_quality_value(system_value, fmt),
            "AI來源/日期": r.get("ai_source", "未啟動AI") if ai_value is None else r.get("ai_source", "AI補齊"),
            "AI來源網址": r.get("ai_source_url", "—") or "—",
            "AI值": format_quality_value(ai_value, fmt),
            "採用值": format_quality_value(adopted_value, fmt),
            "採用來源": r.get("adopted_source", "系統優先/AI備援"),
            "最新日期/期間": r.get("period", "未揭露"),
            "品質狀態": infer_quality_status(adopted_value, system_value, ai_value, r.get("is_stale", False), notes),
            "備註": notes or "—",
        })
    return pd.DataFrame(table)


# ==========================================
# 1.1 財務資料合理性校驗 / 欄位錯位防呆
# ==========================================
def normalize_financial_ratio(val, default=None):
    """將一般百分比欄位統一成小數格式：31.5 -> 0.315；0.315 -> 0.315。
    注意：D/E 不可使用此函式，因為 2.69 可能代表 2.69 倍，而不是 2.69%。
    """
    v = s_float(val, default)
    if v is None:
        return default
    # Yahoo / AI / 不同 API 有時會把百分比以 31.5 而非 0.315 回傳
    if abs(v) > 1.5 and abs(v) <= 100:
        return v / 100.0
    return v


def normalize_debt_to_equity(val, default=None):
    """將 D/E 統一成「倍數」：0.608=60.8%；2.69=269%；132.1=132.1%。

    為什麼要獨立處理：
    - 毛利率/ROE 這類欄位的 12.01 通常代表 12.01%。
    - 但 D/E 的 2.69 常代表 2.69 倍，而不是 2.69%。
    - yfinance 或台灣財報來源常回傳 132.1 代表 132.1%，需轉成 1.321 倍。
    """
    v = s_float(val, default)
    if v is None:
        return default

    av = abs(v)
    # 2.69 這種常見寫法多半是 2.69 倍 = 269%。
    if 1.5 < av <= 10:
        return v
    # 60.8 / 132.1 / 269 這種通常是百分比數字。
    if 10 < av <= 1000:
        return v / 100.0
    # 0.608 / 1.321 這種已是倍數。
    return v

def normalize_revenue_month(val):
    """將 2026-04 / 2026年4月 / 202604 等格式盡量統一成 YYYY/MM。"""
    if val is None:
        return ""
    s = str(val).strip().replace("None", "")
    if not s:
        return ""
    m = re.search(r"(20\d{2})\D{0,3}(0?[1-9]|1[0-2])", s)
    if m:
        return f"{int(m.group(1)):04d}/{int(m.group(2)):02d}"
    m = re.search(r"(20\d{2})(0[1-9]|1[0-2])", s)
    if m:
        return f"{int(m.group(1)):04d}/{int(m.group(2)):02d}"
    return s


def previous_calendar_month(today=None):
    """回傳查詢日之前一個日曆月份，格式 YYYY/MM。

    例：2026/06/01 查詢時，上一個日曆月份是 2026/05。
    這個欄位只用來產生「某月尚未公告」提示，不可拿來假設最新公告月份。
    """
    today = today or datetime.date.today()
    first_day = today.replace(day=1)
    prev_last_day = first_day - datetime.timedelta(days=1)
    return prev_last_day.strftime("%Y/%m")


def expected_latest_revenue_month(today=None, announcement_day=10):
    """依台股月營收公告節奏推估「應已公告的最新月份」。

    多數公司月營收於次月 10 日前公告。若查詢日期仍在 10 日含以前，
    不能把上一個日曆月份視為理所當然已公告，避免 6/1 查詢時把 5 月
    誤標為最新公告月份。因此：
    - 每月 1～10 日：保守預期最新公告月份為「前兩個月」。
    - 每月 11 日起：保守預期最新公告月份為「上一個月」。

    注意：真正顯示仍以資料來源回傳的 actual_revenue_month 為準。
    """
    today = today or datetime.date.today()
    first_day = today.replace(day=1)
    prev_last_day = first_day - datetime.timedelta(days=1)
    if today.day <= announcement_day:
        prev_first = prev_last_day.replace(day=1)
        expected_last_day = prev_first - datetime.timedelta(days=1)
        return expected_last_day.strftime("%Y/%m")
    return prev_last_day.strftime("%Y/%m")


def revenue_month_is_older(actual_month, expected_month=None):
    actual = normalize_revenue_month(actual_month)
    expected = normalize_revenue_month(expected_month or expected_latest_revenue_month())
    try:
        return bool(actual and expected and actual < expected)
    except Exception:
        return False


def build_revenue_month_notice(actual_month, today=None):
    """建立月營收月份提示文字，避免把查詢月份或上一月份誤當公告月份。

    Returns
    -------
    dict: {actual_month, previous_month, expected_month, display_label, notice, is_pending_previous_month, is_older_than_expected}
    """
    actual = normalize_revenue_month(actual_month)
    previous_month = previous_calendar_month(today)
    expected = expected_latest_revenue_month(today)
    is_pending_previous = bool(actual and previous_month and actual < previous_month)
    is_older = revenue_month_is_older(actual, expected) if actual else False

    notice = ""
    if not actual:
        display_label = "公告月份：未取得"
    else:
        display_label = f"公告月份：{actual}"
        if is_pending_previous:
            try:
                pending_m = int(previous_month.split("/")[1])
                notice = f"{pending_m} 月營收尚未公告，目前最新公告月份為 {actual}。"
            except Exception:
                notice = f"{previous_month} 營收尚未公告，目前最新公告月份為 {actual}。"
        elif is_older:
            notice = f"月營收資料可能落後；目前最新公告月份為 {actual}，保守預期應至少為 {expected}。"

    return {
        "actual_month": actual,
        "previous_month": previous_month,
        "expected_month": expected,
        "display_label": display_label,
        "notice": notice,
        "is_pending_previous_month": is_pending_previous,
        "is_older_than_expected": is_older,
    }


def validate_and_correct_financial_metrics(system_vals, ai_vals=None, monthly_rev_df=None, stock_id="", stock_name=""):
    """
    財務資料品質閘門：
    1) 營益率不可高於毛利率；
    2) 最新單月 YoY 優先採用月營收資料，不直接吃 yfinance revenueGrowth；
    3) D/E 若疑似單位錯置或與 AI/財報校對差距過大，先剔除系統值；
    4) AI 交叉校對值也必須通過合理區間，否則設為 NULL，避免幻覺進入估值模型。

    回傳：corrected_system, normalized_ai, warnings
    """
    ai_vals = ai_vals or {}
    corrected = dict(system_vals or {})
    ai_norm = dict(ai_vals or {})
    warnings = []
    label = f"{stock_name} ({stock_id})" if stock_name and stock_id else (stock_name or stock_id or "目前標的")

    # v1.24 欄位相容：rev_growth/revenue_yoy、mom/revenue_mom 新舊欄位可互通。
    if ai_norm.get("revenue_yoy") is None and ai_norm.get("rev_growth") is not None:
        ai_norm["revenue_yoy"] = ai_norm.get("rev_growth")
    if ai_norm.get("rev_growth") is None and ai_norm.get("revenue_yoy") is not None:
        ai_norm["rev_growth"] = ai_norm.get("revenue_yoy")

    # 統一百分比欄位尺度；D/E 需獨立正規化，避免 2.69 倍被誤判成 2.69%。
    for key in ["gross_margin", "operating_margin", "rev_growth", "revenue_yoy", "revenue_mom", "earnings_cagr", "eps_growth_yoy"]:
        corrected[key] = normalize_financial_ratio(corrected.get(key))
        ai_norm[key] = normalize_financial_ratio(ai_norm.get(key))
    corrected["debt_to_equity"] = normalize_debt_to_equity(corrected.get("debt_to_equity"))
    ai_norm["debt_to_equity"] = normalize_debt_to_equity(ai_norm.get("debt_to_equity"))

    def is_reasonable_ratio(v, lo=-1.0, hi=1.0):
        return v is None or (lo <= v <= hi)

    def margin_pair_is_valid(gm, om):
        if not is_reasonable_ratio(gm, -1.0, 1.0) or not is_reasonable_ratio(om, -1.0, 1.0):
            return False
        if gm is None or om is None:
            return True
        # 營益率理論上不得高於毛利率；0.3% 容許極小四捨五入誤差
        return om <= gm + 0.003

    sys_gm = corrected.get("gross_margin")
    sys_om = corrected.get("operating_margin")
    ai_gm = ai_norm.get("gross_margin")
    ai_om = ai_norm.get("operating_margin")

    if not margin_pair_is_valid(sys_gm, sys_om):
        warnings.append(
            f"{label} 的毛利率/營益率校驗失敗：系統值 {to_val_str(sys_gm, 'pct')} / {to_val_str(sys_om, 'pct')} 不合理，已排除系統毛利率與營益率。"
        )
        corrected["gross_margin"] = None
        corrected["operating_margin"] = None

    if not margin_pair_is_valid(ai_gm, ai_om):
        warnings.append(
            f"{label} 的 AI 毛利率/營益率也未通過校驗：{to_val_str(ai_gm, 'pct')} / {to_val_str(ai_om, 'pct')}，已設為 NULL，避免 AI 幻覺進入估值。"
        )
        ai_norm["gross_margin"] = None
        ai_norm["operating_margin"] = None

    # 最新單月 YoY：優先用月營收表，不用 yfinance info 的 revenueGrowth 當月 YoY
    try:
        if monthly_rev_df is not None and not monthly_rev_df.empty and "YoY" in monthly_rev_df.columns:
            monthly_yoy_pct = s_float(monthly_rev_df["YoY"].iloc[-1])
            monthly_yoy = monthly_yoy_pct / 100.0 if monthly_yoy_pct is not None else None
            monthly_period = ""
            if "Month" in monthly_rev_df.columns:
                monthly_period = normalize_revenue_month(monthly_rev_df["Month"].iloc[-1])
            if monthly_yoy is not None and -1.0 <= monthly_yoy <= 10.0:
                old_sys_yoy = corrected.get("rev_growth")
                if old_sys_yoy is not None and abs(old_sys_yoy - monthly_yoy) >= 0.10:
                    period_text = f"({monthly_period})" if monthly_period else ""
                    warnings.append(
                        f"{label} 的 yfinance revenueGrowth={to_val_str(old_sys_yoy, 'pct')}，系統月營收快取{period_text} YoY={to_val_str(monthly_yoy, 'pct')}；已先以月營收快取取代 yfinance 值。若 AI 同月份交叉校對不一致，畫面與打包提示詞會再改用 AI 同月份值。"
                    )
                corrected["rev_growth"] = monthly_yoy
                corrected["revenue_yoy"] = monthly_yoy
    except Exception:
        pass

    # AI YoY 也做合理範圍防呆；極端值多半是抓到錯欄或摘要幻覺
    ai_yoy = ai_norm.get("rev_growth")
    if ai_yoy is not None and not (-1.0 <= ai_yoy <= 10.0):
        warnings.append(
            f"{label} 的 AI 營收 YoY={to_val_str(ai_yoy, 'pct')} 超出合理範圍，已設為 NULL。"
        )
        ai_norm["rev_growth"] = None

    # D/E：系統值與 AI 值雙層防呆。D/E > 800% 直接視為高風險異常值，不進估值模型。
    def debt_to_equity_is_valid(v):
        return v is None or (0 <= v <= 8.0)

    sys_de = corrected.get("debt_to_equity")
    ai_de = ai_norm.get("debt_to_equity")

    if not debt_to_equity_is_valid(ai_de):
        warnings.append(
            f"{label} 的 AI D/E={to_val_str(ai_de, 'pct')} 超出 800% 安全上限，已設為 NULL，避免 AI 幻覺污染模型。"
        )
        ai_norm["debt_to_equity"] = None
        ai_de = None

    if sys_de is not None:
        if not debt_to_equity_is_valid(sys_de):
            warnings.append(f"{label} 的 D/E 系統值 {to_val_str(sys_de, 'pct')} 超出合理範圍，已排除。")
            corrected["debt_to_equity"] = None
        elif ai_de is not None:
            # 例如系統 0.76% vs AI 31.53%，極可能是單位或欄位錯位
            if sys_de < 0.02 and ai_de >= 0.10:
                warnings.append(
                    f"{label} 的 D/E 疑似單位/欄位錯位：系統 {to_val_str(sys_de, 'pct')} vs AI {to_val_str(ai_de, 'pct')}，已排除系統 D/E。"
                )
                corrected["debt_to_equity"] = None
            elif abs(sys_de - ai_de) >= max(0.15, abs(ai_de) * 0.80):
                warnings.append(
                    f"{label} 的 D/E 與交叉校對差距過大：系統 {to_val_str(sys_de, 'pct')} vs AI {to_val_str(ai_de, 'pct')}，已排除系統 D/E。"
                )
                corrected["debt_to_equity"] = None

    # 最終防線：系統值被排除時，如果 AI 也不可用，後續 eff_de 會自然維持 None/NULL。
    return corrected, ai_norm, warnings



def build_eps_breakdown_report(rows):
    """
    將 EPS 拆欄資料整理成 DataFrame。
    目的：避免「目前 EPS」混用最新單季、TTM、年度、Forward EPS。
    rows 每列建議包含：field, definition, system_value, ai_value, adopted_value, source, period, notes。
    """
    import pandas as pd

    def _fmt_eps(v):
        v = s_float(v)
        return "NULL" if v is None else f"{v:.2f}"

    out = []
    for r in rows or []:
        out.append({
            "EPS欄位": r.get("field", ""),
            "定義/用途": r.get("definition", ""),
            "系統值": _fmt_eps(r.get("system_value")),
            "AI值": _fmt_eps(r.get("ai_value")),
            "採用值": _fmt_eps(r.get("adopted_value")),
            "採用來源": r.get("source", ""),
            "期間/口徑": r.get("period", ""),
            "備註": r.get("notes", ""),
        })
    return pd.DataFrame(out)


def pick_first_number(*values):
    """回傳第一個可轉成 float 的數字。"""
    for v in values:
        x = s_float(v)
        if x is not None:
            return x
    return None

def validate_ai_financial_json(ai_fin, stock_id="", stock_name=""):
    """
    AI 財報 JSON 集中驗證器：
    在 Gemini 回傳後、進入 UI/估值模型前，統一完成數值轉型、合理區間檢查與目標價排序防呆。

    驗證原則：
    1) 可修正的單位問題先修正，例如百分比 25.5 -> 0.255、D/E 132.1 -> 1.321。
    2) 明顯不合理的值設為 None，不讓 AI 幻覺污染估值模型。
    3) 目標價高/均/低若只是順序錯置，會排序修正；若為負值或荒謬值則排除。
    4) 所有修正記錄在 _ai_validation_warnings，供 UI 顯示與除錯。
    """
    if not isinstance(ai_fin, dict):
        return ai_fin

    data = dict(ai_fin)
    warnings = []
    invalid_fields = []
    label = f"{stock_name} ({stock_id})" if stock_name and stock_id else (stock_name or stock_id or "目前標的")

    def add_warning(field, message):
        invalid_fields.append(field)
        warnings.append(message)

    def num(field, default=None):
        v = s_float(data.get(field), default)
        data[field] = v
        return v

    def null_field(field, reason):
        data[field] = None
        add_warning(field, f"{label} AI 欄位 {field} 已排除：{reason}")

    # 數值欄位基本轉型
    numeric_fields = [
        "pe",
        # EPS 拆欄：保留 legacy 欄位，也支援新標準欄位。
        "trailing_eps", "forward_eps",
        "latest_quarter_eps", "ttm_eps", "fiscal_year_eps",
        "forward_eps_system", "forward_eps_ai", "forward_eps_consensus",
        "pb", "target_price", "target_price_high",
        "target_price_avg", "target_price_low", "target_price_analyst_count", "free_cash_flow",
        "current_ratio", "shares_outstanding"
    ]
    for field in numeric_fields:
        if field in data:
            num(field)

    # EPS 拆欄向下相容：舊版 AI 只回 trailing_eps / forward_eps 時，映射到新口徑。
    if data.get("ttm_eps") is None and data.get("trailing_eps") is not None:
        data["ttm_eps"] = data.get("trailing_eps")
    if data.get("trailing_eps") is None and data.get("ttm_eps") is not None:
        data["trailing_eps"] = data.get("ttm_eps")
    if data.get("forward_eps_ai") is None and data.get("forward_eps") is not None:
        data["forward_eps_ai"] = data.get("forward_eps")
    if data.get("forward_eps") is None:
        data["forward_eps"] = data.get("forward_eps_consensus") or data.get("forward_eps_ai") or data.get("forward_eps_system")

    # 百分比/比率欄位標準化。AI 常把 25.5% 寫成 25.5，這裡轉為 0.255。
    ratio_fields = ["gross_margin", "operating_margin", "roe", "yoy", "mom", "dividend_yield"]
    for field in ratio_fields:
        if field in data:
            data[field] = normalize_financial_ratio(data.get(field))

    if "debt_to_equity" in data:
        data["debt_to_equity"] = normalize_debt_to_equity(data.get("debt_to_equity"))

    # 估值倍數合理性
    pe = data.get("pe")
    if pe is not None and (pe < 0 or pe > 300):
        null_field("pe", f"P/E={pe:.2f} 超出 0～300 安全範圍")

    pb = data.get("pb")
    if pb is not None and (pb < 0 or pb > 100):
        null_field("pb", f"P/B={pb:.2f} 超出 0～100 安全範圍")

    # EPS：允許虧損，但極端值通常是單位或股本欄位誤抓
    for field in ["trailing_eps", "forward_eps", "latest_quarter_eps", "ttm_eps", "fiscal_year_eps", "forward_eps_system", "forward_eps_ai", "forward_eps_consensus"]:
        v = data.get(field)
        if v is not None and abs(v) > 10000:
            null_field(field, f"EPS={v:,.2f} 絕對值過大，疑似單位錯置")

    # 毛利率/營益率/ROE/成長/殖利率
    gm = data.get("gross_margin")
    om = data.get("operating_margin")
    if gm is not None and not (-1.0 <= gm <= 1.0):
        null_field("gross_margin", f"毛利率={gm:.4f} 超出 -100%～100%")
        gm = None
    if om is not None and not (-1.0 <= om <= 1.0):
        null_field("operating_margin", f"營益率={om:.4f} 超出 -100%～100%")
        om = None
    if gm is not None and om is not None and om > gm + 0.003:
        data["gross_margin"] = None
        data["operating_margin"] = None
        add_warning("gross_margin", f"{label} AI 毛利率/營益率邏輯不合理：營益率 {om:.2%} 高於毛利率 {gm:.2%}，兩欄皆設為 NULL。")
        add_warning("operating_margin", f"{label} AI 毛利率/營益率邏輯不合理：營益率 {om:.2%} 高於毛利率 {gm:.2%}，兩欄皆設為 NULL。")

    roe = data.get("roe")
    if roe is not None and not (-1.0 <= roe <= 1.0):
        null_field("roe", f"ROE={roe:.2%} 超出 -100%～100%")

    yoy = data.get("yoy")
    if yoy is not None and not (-1.0 <= yoy <= 10.0):
        null_field("yoy", f"YoY/CAGR={yoy:.2%} 超出 -100%～1000% 安全範圍")

    mom = data.get("mom")
    if mom is not None and not (-1.0 <= mom <= 5.0):
        null_field("mom", f"MoM={mom:.2%} 超出 -100%～500% 安全範圍")

    dy = data.get("dividend_yield")
    if dy is not None and not (0 <= dy <= 0.20):
        null_field("dividend_yield", f"殖利率={dy:.2%} 超出 0%～20%，疑似百分比尺度錯誤或抓錯欄位")

    de = data.get("debt_to_equity")
    if de is not None and not (0 <= de <= 8.0):
        null_field("debt_to_equity", f"D/E={de:.2f} 倍超出 0～8 倍安全範圍")

    cr = data.get("current_ratio")
    if cr is not None and not (0 <= cr <= 20):
        null_field("current_ratio", f"流動比率={cr:.2f} 超出 0～20 安全範圍")

    shares = data.get("shares_outstanding")
    if shares is not None and shares <= 0:
        null_field("shares_outstanding", "總發行股數/股本不可小於等於 0")

    # 目標價合理性與 high/avg/low 排序
    price_fields = ["target_price", "target_price_high", "target_price_avg", "target_price_low"]
    for field in price_fields:
        v = data.get(field)
        if v is not None and v <= 0:
            null_field(field, f"目標價={v} 不可小於等於 0")

    hi = data.get("target_price_high")
    avg = data.get("target_price_avg")
    lo = data.get("target_price_low")
    if hi is not None and avg is not None and lo is not None:
        if not (hi >= avg >= lo):
            sorted_vals = sorted([hi, avg, lo], reverse=True)
            data["target_price_high"], data["target_price_avg"], data["target_price_low"] = sorted_vals
            add_warning("target_price_high", f"{label} AI 目標價高/均/低順序錯置，已自動排序為 high≥avg≥low：{sorted_vals[0]:.2f}/{sorted_vals[1]:.2f}/{sorted_vals[2]:.2f}")
    elif hi is not None and lo is not None and hi < lo:
        data["target_price_high"], data["target_price_low"] = lo, hi
        add_warning("target_price_high", f"{label} AI 目標價 high/low 順序錯置，已交換。")

    # target_price 若缺漏，用 avg 補；若和 avg 差太大，以 avg 為主，避免 target_price 抓到個別券商極端值。
    avg = data.get("target_price_avg")
    tp = data.get("target_price")
    if tp is None and avg is not None:
        data["target_price"] = avg
    elif tp is not None and avg is not None and avg > 0 and abs(tp - avg) / avg > 0.5:
        data["target_price"] = avg
        add_warning("target_price", f"{label} AI target_price 與平均目標價差距超過 50%，已改採 target_price_avg。")

    cnt = data.get("target_price_analyst_count")
    if cnt is not None:
        if cnt < 0 or cnt > 100:
            null_field("target_price_analyst_count", f"分析師人數={cnt:.0f} 超出 0～100 安全範圍")
        else:
            data["target_price_analyst_count"] = int(round(cnt))

    # data_period 至少轉字串，避免後續 UI 出現 None。
    data["data_period"] = str(data.get("data_period") or "").strip()

    # 記錄驗證結果，UI 可直接顯示。
    data["_ai_validation_warnings"] = warnings
    data["_ai_invalid_fields"] = sorted(set(invalid_fields))
    data["_ai_validation_status"] = "⚠️ 已校正/排除部分 AI 欄位" if warnings else "✅ AI JSON 合理性驗證通過"
    return data


# ==========================================
# 1.0.3 最終操作燈號：可買 / 觀望 / 不建議 / 資料異常
# ==========================================
def _confidence_label_from_score(score):
    """將 0-100 分轉成文字可信度。"""
    try:
        v = float(score)
    except Exception:
        return "資料不足"
    if v >= 80:
        return "高"
    if v >= 65:
        return "中高"
    if v >= 50:
        return "中"
    if v >= 35:
        return "偏低"
    return "低"


def build_final_operation_signal(
    *,
    current_price=None,
    valuation_separation=None,
    divergence_warnings=None,
    target_confidence=None,
    industry_profile=None,
    pe=None,
    forward_pe=None,
    peg=None,
    pb=None,
    roe=None,
    debt_to_equity=None,
    revenue_yoy=None,
    gross_margin=None,
    operating_margin=None,
    has_ai_fin_fetch=False,
):
    """
    產生最終操作燈號。

    燈號定義：
    - 可買：資料一致、估值落在可操作區間下緣附近、基本面未明顯轉弱。
    - 觀望：基本面可，但估值未到買點，或資料有輕度分歧。
    - 不建議：價格高於可操作區間、估值偏高、產業模型不適合純 P/E 買進，或基本面不支撐。
    - 資料異常：關鍵欄位嚴重分歧、可操作區間無法建立、AI / 系統資料矛盾嚴重。

    回傳 dict，含 signal、scores、reason、report。
    """
    valuation_separation = valuation_separation or {}
    warnings = divergence_warnings or []
    industry_profile = industry_profile or {}
    target_confidence = target_confidence or valuation_separation.get("target_confidence") or classify_target_price_confidence(None)

    cp = s_float(current_price)
    op_low = s_float(valuation_separation.get("operable_low"))
    op_mid = s_float(valuation_separation.get("operable_mid"))
    op_high = s_float(valuation_separation.get("operable_high"))
    warning_count = int(valuation_separation.get("warning_count", len(warnings)) or 0)
    danger_count = int(valuation_separation.get("danger_count", sum(1 for w in warnings if str(w.get("嚴重度", "")).lower() == "danger")) or 0)

    pe_model_suitable = bool(industry_profile.get("pe_model_suitable", True))
    target_rank = int(target_confidence.get("rank", 1) or 1)

    # 異常值防呆
    abnormal_reasons = []
    fy = s_float(forward_pe)
    pe_v = s_float(pe)
    peg_v = s_float(peg)
    pb_v = s_float(pb)
    roe_v = s_float(roe)
    de_v = s_float(debt_to_equity)
    yoy_v = s_float(revenue_yoy)
    gm_v = s_float(gross_margin)
    om_v = s_float(operating_margin)

    if danger_count >= 2:
        abnormal_reasons.append("重大分歧警告達 2 項以上")
    if warning_count >= 4:
        abnormal_reasons.append("系統 / AI 分歧警告過多")
    if op_low is None or op_high is None:
        abnormal_reasons.append("可操作估值區間無法建立")
    if om_v is not None and gm_v is not None and om_v > gm_v + 0.05:
        abnormal_reasons.append("營益率高於毛利率，財報口徑疑似異常")
    if de_v is not None and de_v > 8:
        abnormal_reasons.append("D/E 異常偏高，需確認單位")
    if peg_v is not None and peg_v < 0:
        abnormal_reasons.append("PEG 為負值，成長估值不可直接使用")

    # 三個可信度分數：資料、估值、操作。
    data_score = 85
    data_score -= warning_count * 8
    data_score -= danger_count * 18
    if has_ai_fin_fetch:
        data_score += 5
    if target_rank <= 2:
        data_score -= 8
    if abnormal_reasons:
        data_score -= 18
    data_score = max(0, min(100, data_score))

    valuation_score = 75
    if fy is not None:
        if fy > 35:
            valuation_score -= 20
        elif fy > 25:
            valuation_score -= 10
        elif fy < 15 and fy > 0:
            valuation_score += 8
    if peg_v is not None:
        if peg_v > 2:
            valuation_score -= 16
        elif 0 < peg_v <= 1:
            valuation_score += 10
    if pb_v is not None and pb_v > 4:
        valuation_score -= 8
    if not pe_model_suitable:
        valuation_score -= 15
    if op_low is not None and op_high is not None and cp is not None:
        if cp <= op_low:
            valuation_score += 8
        elif cp > op_high:
            valuation_score -= 15
    valuation_score -= danger_count * 12
    valuation_score = max(0, min(100, valuation_score))

    operation_score = min(data_score, valuation_score)
    if roe_v is not None and roe_v >= 0.15:
        operation_score += 5
    if yoy_v is not None and yoy_v > 0:
        operation_score += 5
    if de_v is not None and de_v > 1.5:
        operation_score -= 8
    if target_rank <= 2:
        operation_score -= 6
    operation_score = max(0, min(100, operation_score))

    # 燈號決策
    reasons = []
    color = "#FFD700"
    signal = "觀望"

    if abnormal_reasons:
        signal = "資料異常"
        color = "#ff4d4d"
        reasons.extend(abnormal_reasons)
        advice = "先修正資料與口徑，不做買賣判斷。"
    elif not pe_model_suitable:
        signal = "不建議"
        color = "#ff8c00"
        reasons.append("產業模型不適合用純 P/E 公式價作買進依據")
        advice = "若屬題材 / 事件驅動股，請改用題材、籌碼、訂單與技術面人工確認。"
    elif cp is not None and op_low is not None and op_high is not None:
        if cp <= op_low and data_score >= 65 and valuation_score >= 65 and danger_count == 0:
            signal = "可買"
            color = "#00cc66"
            reasons.append("現價低於或接近可操作估值區間下緣，且資料分歧不嚴重")
            advice = "可考慮分批，仍需搭配技術面、籌碼與停損。"
        elif cp <= op_high and operation_score >= 50:
            signal = "觀望"
            color = "#FFD700"
            reasons.append("現價位於可操作估值區間內，尚未形成明確便宜買點")
            advice = "不追高，等待回檔或右側確認。"
        else:
            signal = "不建議"
            color = "#ff8c00"
            reasons.append("現價高於可操作估值區間，追價風險偏高")
            advice = "不把公式極限價當作買進目標。"
    else:
        signal = "觀望"
        color = "#FFD700"
        reasons.append("關鍵資料不足，無法產生明確買進燈號")
        advice = "補齊 EPS、月營收、法人目標價與分歧檢查後再判斷。"

    if signal == "可買" and target_rank <= 2:
        signal = "觀望"
        color = "#FFD700"
        reasons.append("法人目標價樣本數偏低，可買燈號降為觀望")
        advice = "可列入觀察，不宜直接重倉。"

    report = pd.DataFrame([
        {"項目": "最終操作燈號", "結果": signal, "說明": advice},
        {"項目": "資料可信度", "結果": f"{data_score:.0f} / 100（{_confidence_label_from_score(data_score)}）", "說明": f"分歧警告 {warning_count} 項，重大 {danger_count} 項。"},
        {"項目": "估值可信度", "結果": f"{valuation_score:.0f} / 100（{_confidence_label_from_score(valuation_score)}）", "說明": "依 Forward P/E、PEG、P/B、產業模型與可操作區間判斷。"},
        {"項目": "操作可信度", "結果": f"{operation_score:.0f} / 100（{_confidence_label_from_score(operation_score)}）", "說明": "取資料與估值可信度後，再納入 ROE、營收 YoY、D/E 與法人樣本數。"},
        {"項目": "可操作估值區間", "結果": "NULL" if op_low is None else f"{op_low:,.2f}～{op_high:,.2f}", "說明": "用保守 EPS、法人樣本數、分歧警告與產業模型折減。"},
        {"項目": "主要原因", "結果": "；".join(reasons) if reasons else "—", "說明": industry_profile.get("warning_note", "—")},
    ])

    return {
        "signal": signal,
        "color": color,
        "advice": advice,
        "reasons": reasons,
        "data_score": data_score,
        "valuation_score": valuation_score,
        "operation_score": operation_score,
        "data_confidence": _confidence_label_from_score(data_score),
        "valuation_confidence": _confidence_label_from_score(valuation_score),
        "operation_confidence": _confidence_label_from_score(operation_score),
        "report": report,
    }

def get_watchlist():
    watchlist = []
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "," in line: watchlist.append(line.split(",")[0].strip())
        except Exception as e:
            log_exception("Utils", "get_watchlist:read_stocklist", e)
    return watchlist

def load_stocklist_structure():
    """解析 stocklist.txt 為 (分類順序, 分類->[(code,name)], 錯誤訊息)。"""
    cat_order = []
    cat_map = {}
    errors = []
    current_cat = None

    if not os.path.exists("stocklist.txt"):
        return [], {}, []

    try:
        with open("stocklist.txt", "r", encoding="utf-8") as f:
            for ln, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                if "," in line:
                    parts = [p.strip() for p in line.split(",", 1)]
                    if len(parts) != 2 or not parts[0] or not parts[1]:
                        errors.append(f"第 {ln} 行格式錯誤：{line}")
                        continue
                    if current_cat is None:
                        current_cat = "未分類"
                        cat_order.append(current_cat)
                        cat_map[current_cat] = []
                    cat_map[current_cat].append((parts[0], parts[1]))
                else:
                    current_cat = line
                    if current_cat not in cat_map:
                        cat_order.append(current_cat)
                        cat_map[current_cat] = []
    except Exception as e:
        errors.append(f"讀取失敗：{str(e)}")

    return cat_order, cat_map, errors

def save_stocklist_structure(cat_order, cat_map):
    lines = []
    for cat in cat_order:
        lines.append(f"{cat}\n")
        for code, name in cat_map.get(cat, []):
            lines.append(f"{code},{name}\n")
        lines.append("\n")
    with open("stocklist.txt", "w", encoding="utf-8") as f:
        f.writelines(lines)

def validate_stocklist_structure(cat_order, cat_map):
    issues = []
    seen = set()
    for cat in cat_order:
        if not cat or "," in cat:
            issues.append(f"分類名稱不合法：{cat}")
        for code, name in cat_map.get(cat, []):
            if not code.isdigit():
                issues.append(f"代號非純數字：{code} ({name})")
            if code in seen:
                issues.append(f"重複代號：{code}")
            seen.add(code)
    return issues

def add_category_to_stocklist(category_name):
    cat = category_name.strip()
    if not cat:
        return False, "分類名稱不可空白。"
    if "," in cat:
        return False, "分類名稱不可包含逗號。"
    cat_order, cat_map, _ = load_stocklist_structure()
    if cat in cat_map:
        return False, "分類已存在。"
    cat_order.append(cat)
    cat_map[cat] = []
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已新增分類：{cat}"

def add_stock_to_category(code, name, category):
    sc = str(code).strip()
    sn = str(name).strip()
    if not sc or not sn:
        return False, "股票代號與名稱皆不可空白。"
    if not sc.isdigit():
        return False, "股票代號必須為純數字。"
    cat_order, cat_map, _ = load_stocklist_structure()
    if category not in cat_map:
        cat_order.append(category)
        cat_map[category] = []
    for c in cat_order:
        for ec, _ in cat_map.get(c, []):
            if ec == sc:
                return False, f"代號 {sc} 已存在於分類「{c}」。"
    cat_map[category].append((sc, sn))
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已加入 {sc} {sn} 到「{category}」。"

def remove_stock_from_stocklist(code):
    sc = str(code).strip()
    cat_order, cat_map, _ = load_stocklist_structure()
    removed = False
    for c in cat_order:
        old_len = len(cat_map.get(c, []))
        cat_map[c] = [(ec, en) for ec, en in cat_map.get(c, []) if ec != sc]
        if len(cat_map[c]) != old_len:
            removed = True
    if not removed:
        return False, f"找不到代號 {sc}。"
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已刪除代號 {sc}。"

def move_stock_to_category(code, target_category):
    sc = str(code).strip()
    target = str(target_category).strip()
    if not target:
        return False, "目標分類不可空白。"
    cat_order, cat_map, _ = load_stocklist_structure()
    found = None
    for c in cat_order:
        for i, (ec, en) in enumerate(cat_map.get(c, [])):
            if ec == sc:
                found = (c, i, en)
                break
        if found:
            break
    if not found:
        return False, f"找不到代號 {sc}。"
    from_cat, idx, name = found
    if target not in cat_map:
        cat_order.append(target)
        cat_map[target] = []
    if from_cat == target:
        return False, "已在同一分類。"
    cat_map[from_cat].pop(idx)
    cat_map[target].append((sc, name))
    save_stocklist_structure(cat_order, cat_map)
    return True, f"已將 {sc} 移動至「{target}」。"

def move_stock_order_within_category(category, code, direction="up"):
    cat_order, cat_map, _ = load_stocklist_structure()
    if category not in cat_map:
        return False, "分類不存在。"
    arr = cat_map[category]
    idx = next((i for i, (c, _) in enumerate(arr) if c == str(code).strip()), -1)
    if idx == -1:
        return False, "找不到該代號。"
    if direction == "up" and idx > 0:
        arr[idx-1], arr[idx] = arr[idx], arr[idx-1]
    elif direction == "down" and idx < len(arr)-1:
        arr[idx+1], arr[idx] = arr[idx], arr[idx+1]
    else:
        return False, "已在邊界，無法移動。"
    cat_map[category] = arr
    save_stocklist_structure(cat_order, cat_map)
    return True, "排序已更新。"

def toggle_watchlist(code, name):
    lines = []
    if os.path.exists("stocklist.txt"):
        try:
            with open("stocklist.txt", "r", encoding="utf-8") as f: lines = f.readlines()
        except Exception as e:
            log_exception("Utils", "toggle_watchlist:read_stocklist", e)
    new_lines = []
    is_removed = False
    for line in lines:
        if "," in line and line.split(",")[0].strip() == str(code):
            is_removed = True
            continue
        new_lines.append(line)
    if not is_removed:
        if new_lines and not new_lines[-1].endswith("\n"): new_lines[-1] = new_lines[-1] + "\n"
        new_lines.append(f"{code},{name}\n")
    with open("stocklist.txt", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def get_streak(series):
    streak = 0
    for val in reversed(series.tolist()):
        if val > 0:
            if streak >= 0: streak += 1
            else: break
        elif val < 0:
            if streak <= 0: streak -= 1
            else: break
        else:
            break
    return streak

# ==========================================
# 2. Session State 初始化 & 狀態管理
# ==========================================
def init_session_state():
    if 'selected_stock' not in st.session_state: st.session_state.selected_stock = "2330"
    if 'topic_results' not in st.session_state: st.session_state.topic_results = None
    if 'show_whale' not in st.session_state: st.session_state.show_whale = False
    if 'api_key' not in st.session_state: st.session_state.api_key = ""
    if 'fugle_key' not in st.session_state: st.session_state.fugle_key = "" 
    if 'finmind_key' not in st.session_state: st.session_state.finmind_key = "" 
    if 'ai_fetched_financials' not in st.session_state: st.session_state.ai_fetched_financials = {}
    if 'show_pk' not in st.session_state: st.session_state.show_pk = False
    if 'ai_industry_result' not in st.session_state: st.session_state.ai_industry_result = None
    if 'run_screener' not in st.session_state: st.session_state.run_screener = False
    if 'quick_select' not in st.session_state: st.session_state.quick_select = "-- 快速切換標的 --"
    if 'stock_input_widget' not in st.session_state: st.session_state.stock_input_widget = "2330"
    if 'show_watchlist_manager' not in st.session_state: st.session_state.show_watchlist_manager = False
    if 'w_valuation' not in st.session_state: st.session_state.w_valuation = 35
    if 'w_growth' not in st.session_state: st.session_state.w_growth = 30
    if 'w_chip' not in st.session_state: st.session_state.w_chip = 20
    if 'w_revenue' not in st.session_state: st.session_state.w_revenue = 15
    if 'data_health_stats' not in st.session_state:
        st.session_state.data_health_stats = {
            "Yahoo": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "Fugle": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "FinMind": {"last_success": None, "error_count": 0, "last_status": "N/A"},
            "Gemini": {"last_success": None, "error_count": 0, "last_status": "N/A"},
        }

def log_data_health(source, ok, status_code=None):
    src = str(source).strip()
    if not src:
        return
    if 'data_health_stats' not in st.session_state:
        init_session_state()
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

def reset_all_states_on_stock_change(stock_code):
    st.session_state.selected_stock = stock_code
    st.session_state.quick_select = "-- 快速切換標的 --"
    st.session_state.show_pk = False
    st.session_state.ai_industry_result = None
    st.session_state.run_screener = False

# ==========================================
# 🌟 這裡就是修正的部分：加入 .get() 安全讀取機制
# ==========================================
def on_stock_input_change():
    new_stock = st.session_state.get('stock_input_widget', '2330')
    selected_stock = st.session_state.get('selected_stock', '2330')
    
    if new_stock != selected_stock: 
        reset_all_states_on_stock_change(new_stock)

def on_quick_select_change():
    selected = st.session_state.get('quick_select', '-- 快速切換標的 --')
    selected_stock = st.session_state.get('selected_stock', '2330')
    
    if selected != "-- 快速切換標的 --":
        if not selected.startswith("🏷️"):
            q_code = selected.replace("　🔸 ", "").split(" ")[0].strip()
            if q_code != selected_stock: 
                reset_all_states_on_stock_change(q_code)
        st.session_state.quick_select = "-- 快速切換標的 --"

def get_selected_model_id():
    """AI 財報/分析模型鎖定付費版高階模型，避免自動降級造成資料失真。"""
    return "gemini-3.1-pro-preview"

# ==========================================
# 1.0.2 法人目標價可信度 + 公式估值 / 可操作估值分離
# ==========================================
def classify_target_price_confidence(analyst_count):
    """
    依分析師樣本數判斷法人目標價可信度。
    規則：NULL=低；1-2=偏低；3-5=中；6-10=中高；10以上=高。
    """
    n = s_float(analyst_count)
    if n is None:
        return {
            "level": "低",
            "rank": 1,
            "label": "低可信",
            "message": "分析師人數為 NULL，不宜視為市場共識。",
            "color": "#ff4d4d",
        }
    n = int(n)
    if n <= 0:
        return {"level": "低", "rank": 1, "label": "低可信", "message": "無有效分析師樣本，不宜視為市場共識。", "color": "#ff4d4d"}
    if n <= 2:
        return {"level": "偏低", "rank": 2, "label": "偏低可信", "message": "僅 1-2 位分析師，僅供參考，需人工確認來源。", "color": "#ff9900"}
    if n <= 5:
        return {"level": "中", "rank": 3, "label": "中可信", "message": "3-5 位分析師，可作區間參考，但需檢查 EPS 口徑是否一致。", "color": "#FFD700"}
    if n <= 10:
        return {"level": "中高", "rank": 4, "label": "中高可信", "message": "6-10 位分析師，可納入基準估值參考。", "color": "#66ccff"}
    return {"level": "高", "rank": 5, "label": "高可信", "message": "10 位以上分析師，可視為較可靠共識，但仍需確認資料日期。", "color": "#00cc66"}


def _positive_numbers(*values):
    out = []
    for v in values:
        fv = s_float(v)
        if fv is not None and fv > 0:
            out.append(fv)
    return out


def build_target_price_confidence_report(analyst_count, high=None, avg=None, low=None, rationale=""):
    """將法人目標價可信度整理成單列表格。"""
    c = classify_target_price_confidence(analyst_count)
    return pd.DataFrame([{
        "分析師人數": "NULL" if s_float(analyst_count) is None else int(s_float(analyst_count)),
        "可信度": c["level"],
        "系統標籤": c["label"],
        "最高價": format_quality_value(high, "price"),
        "平均價": format_quality_value(avg, "price"),
        "最低價": format_quality_value(low, "price"),
        "判斷說明": c["message"],
        "核心理由": rationale or "—",
    }])


def build_valuation_separation_report(
    *,
    current_price=None,
    system_formula_fair_value=None,
    ai_formula_fair_value=None,
    system_formula_extreme_value=None,
    ai_formula_extreme_value=None,
    broker_target_avg=None,
    broker_target_low=None,
    analyst_count=None,
    system_forward_eps=None,
    ai_forward_eps=None,
    consensus_forward_eps=None,
    target_pe_cap=None,
    divergence_warnings=None,
    industry_profile=None,
    dynamic_cap_pack=None,
    pb_ratio=None,
):
    """
    產生「公式估值」與「可操作估值區間」分離報告。

    原則：
    - 公式合理估值 / 公式極限價：純公式輸出，不直接作買賣依據。
    - 可操作估值區間：用保守 EPS、法人樣本數與分歧警告折減後產生。
    - 此函式只提供風險調整後區間，不取代人工投資判斷。
    """
    target_conf = classify_target_price_confidence(analyst_count)
    warnings = divergence_warnings or []
    danger_count = sum(1 for w in warnings if str(w.get("嚴重度", "")).lower() == "danger")
    warning_count = len(warnings)
    industry_profile = industry_profile or {}
    industry_label = industry_profile.get("model_label", "一般產業 / 尚未分類")
    industry_discount = s_float(industry_profile.get("operable_discount_factor"))
    if industry_discount is None or industry_discount <= 0:
        industry_discount = 1.0
    industry_discount = max(0.50, min(industry_discount, 1.05))
    pe_model_suitable = bool(industry_profile.get("pe_model_suitable", True))
    dynamic_cap_pack = dynamic_cap_pack or {}
    primary_valuation = str(industry_profile.get("primary_valuation") or "")
    pb_range = industry_profile.get("pb_range")
    pb_model_active = primary_valuation.startswith("pb_cycle") or (dynamic_cap_pack.get("valuation_mode") == "pb_cycle")

    conservative_eps_candidates = _positive_numbers(consensus_forward_eps, system_forward_eps, ai_forward_eps)
    conservative_eps = min(conservative_eps_candidates) if conservative_eps_candidates else None

    # 可納入可操作估值的基準價：系統/AI公式合理價為主；法人平均目標價需至少中可信才納入；法人低標可作風險下緣參考。
    base_candidates = _positive_numbers(system_formula_fair_value, ai_formula_fair_value)
    if target_conf["rank"] >= 3:
        base_candidates.extend(_positive_numbers(broker_target_avg))
    if not base_candidates and conservative_eps is not None and s_float(target_pe_cap) is not None:
        # 沒有公式價時，用保守 EPS × 65% Cap 作保守替代，不使用完整極限 Cap。
        base_candidates.append(conservative_eps * max(float(target_pe_cap) * 0.65, 1))

    formula_base = min(base_candidates) if base_candidates else None

    # 第 17-B：P/B 週期模型。金融、記憶體、面板、航運等產業不硬套 P/E。
    pb_operable_low = pb_operable_high = pb_bvps = None
    if pb_model_active:
        try:
            pb_val = s_float(pb_ratio)
            cp_val = s_float(current_price)
            if cp_val is not None and pb_val is not None and pb_val > 0:
                pb_bvps = cp_val / pb_val
            if isinstance(pb_range, (tuple, list)) and len(pb_range) == 2 and pb_bvps is not None:
                pb_low = s_float(pb_range[0]); pb_high = s_float(pb_range[1])
                if pb_low is not None and pb_high is not None:
                    pb_operable_low = pb_bvps * pb_low
                    pb_operable_high = pb_bvps * pb_high
                    formula_base = (pb_operable_low + pb_operable_high) / 2
        except Exception:
            pass

    # 依法人可信度與分歧警告折減可操作價格。
    conf_discount_map = {5: 1.00, 4: 0.95, 3: 0.90, 2: 0.82, 1: 0.75}
    discount = conf_discount_map.get(target_conf["rank"], 0.75)
    if danger_count >= 1:
        discount *= 0.75
    elif warning_count >= 2:
        discount *= 0.85
    elif warning_count == 1:
        discount *= 0.92

    # 第 13 階段：依產業模型折減可操作估值。題材股或不適用 P/E 模型者，額外降級。
    discount *= industry_discount
    if not pe_model_suitable:
        discount *= 0.85

    operable_mid = formula_base * discount if formula_base is not None else None
    operable_low = operable_mid * 0.90 if operable_mid is not None else None
    operable_high = operable_mid * 1.10 if operable_mid is not None else None

    cp = s_float(current_price)
    if pb_model_active and pb_operable_low is not None and pb_operable_high is not None:
        operable_low = pb_operable_low
        operable_high = pb_operable_high
        operable_mid = (operable_low + operable_high) / 2
        action_hint = "P/B 週期模型已建立，P/E 僅作輔助，請搭配週期位置與報價/運價判斷"
    elif not pe_model_suitable:
        action_hint = "產業模型不適合純 P/E 買進判斷，請改看題材、籌碼、訂單與現金流"
    elif operable_low is None or operable_high is None or warning_count >= 3 or danger_count >= 2:
        action_hint = "資料異常 / 先確認資料"
    elif cp is not None and cp <= operable_low:
        action_hint = "接近可操作區間下緣，可進一步人工確認"
    elif cp is not None and cp <= operable_high:
        action_hint = "位於可操作區間內，仍需搭配技術面與籌碼"
    elif cp is not None and cp > operable_high:
        action_hint = "高於可操作區間，不宜把公式極限價當追價目標"
    else:
        action_hint = "觀望 / 資料不足"

    rows = [
        {
            "估值類型": "系統公式合理估值",
            "數值": format_quality_value(system_formula_fair_value, "price"),
            "用途": "純公式輸出，用於觀察估值中樞，不直接作買賣依據。",
            "可信度/限制": "受 Forward EPS、成長率與 PEG 參數影響。",
        },
        {
            "估值類型": "AI公式合理估值",
            "數值": format_quality_value(ai_formula_fair_value, "price"),
            "用途": "AI 補值後的公式輸出，用於和系統公式交叉檢查。",
            "可信度/限制": "若 AI EPS 或 YoY 與系統分歧，需降級使用。",
        },
        {
            "估值類型": "系統公式極限價",
            "數值": format_quality_value(system_formula_extreme_value, "price"),
            "用途": "情境上限 / 風險提醒，不作為買進目標價。",
            "可信度/限制": "Forward EPS × Cap，容易被樂觀 EPS 放大。",
        },
        {
            "估值類型": "AI公式極限價",
            "數值": format_quality_value(ai_formula_extreme_value, "price"),
            "用途": "AI 輸入值推算的情境上限，只供壓力測試。",
            "可信度/限制": "AI 來源不明或樣本數不足時，可信度降低。",
        },
        {
            "估值類型": "產業估值模型",
            "數值": industry_label,
            "用途": "依股票所屬產業決定主要估值框架與折減係數。",
            "可信度/限制": industry_profile.get("warning_note", "若分類不準，請人工調整 stocklist.txt 或產業模型規則。"),
        },
        {
            "估值類型": "Dynamic Cap 2.0 可操作倍率",
            "數值": "NULL" if dynamic_cap_pack.get("final_cap") is None else f"{float(dynamic_cap_pack.get('final_cap')):.1f}x",
            "用途": "中性可操作倍率；已納入資料可信度、估值風險與流動性折扣。",
            "可信度/限制": dynamic_cap_pack.get("explanation", "若為 P/B 週期模型，P/E Cap 僅作輔助。"),
        },
        {
            "估值類型": "Dynamic Cap 2.0 可操作倍率區間",
            "數值": "NULL" if dynamic_cap_pack.get("operable_cap_low") is None else f"{float(dynamic_cap_pack.get('operable_cap_low')):.1f}x～{float(dynamic_cap_pack.get('operable_cap_high')):.1f}x",
            "用途": "循環復甦股與資料分歧情境下，不只看單點倍率，而是看保守～中性～偏樂觀可操作範圍。",
            "可信度/限制": "此區間不等於公式極限價；高於區間時不宜追價。",
        },
        {
            "估值類型": "Dynamic Cap 2.0 公式/樂觀倍率",
            "數值": "NULL" if dynamic_cap_pack.get("formula_cap") is None else f"公式 {float(dynamic_cap_pack.get('formula_cap')):.1f}x｜樂觀 {float(dynamic_cap_pack.get('optimistic_cap')):.1f}x｜Hard {float(dynamic_cap_pack.get('hard_ceiling_cap')):.1f}x",
            "用途": "公式合理倍率與樂觀情境倍率分開顯示，避免把折扣後可操作倍率誤當公式極限價。",
            "可信度/限制": "Hard ceiling 僅為強制上限，不作買進目標。",
        },
        {
            "估值類型": "可操作估值區間",
            "數值": "NULL" if operable_low is None else f"{operable_low:,.2f}～{operable_high:,.2f}",
            "用途": "用保守 EPS、Dynamic Cap 2.0、法人樣本數、分歧警告與產業模型折減後的輔助區間。",
            "可信度/限制": (f"P/B 週期模型；BVPS 推估：{pb_bvps:.2f}；P/B 區間：{pb_range}" if pb_model_active and pb_bvps is not None else f"法人目標價可信度：{target_conf['level']}；分歧警告：{warning_count} 項；產業折減：{industry_discount:.2f}；總折減係數：約 {discount:.2f}。"),
        },
    ]
    return {
        "target_confidence": target_conf,
        "conservative_eps": conservative_eps,
        "formula_base": formula_base,
        "discount": discount,
        "industry_profile": industry_profile,
        "industry_discount": industry_discount,
        "operable_low": operable_low,
        "operable_mid": operable_mid,
        "operable_high": operable_high,
        "action_hint": action_hint,
        "warning_count": warning_count,
        "danger_count": danger_count,
        "dynamic_cap_pack": dynamic_cap_pack,
        "pb_model_active": pb_model_active,
        "pb_bvps": pb_bvps,
        "pb_operable_low": pb_operable_low,
        "pb_operable_high": pb_operable_high,
        "report": pd.DataFrame(rows),
    }
