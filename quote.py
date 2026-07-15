"""Global market trend panel for ui_main.render_main_page."""

from ui_common import *


def _trend_color(value):
    if value > 0:
        return "#ff4d4d"
    if value < 0:
        return "#00cc66"
    return "#fff"


def render_market_trend_panel():
    """Render international linkage trend data and return the raw snapshot."""
    st.markdown("<br>", unsafe_allow_html=True)
    trend_data = get_global_market_trend()
    if not trend_data:
        return trend_data

    target_day_text = trend_data.get("target_day", "明日")
    time_status_text = trend_data.get("time_status", "")
    st.markdown(f"#### 🌍 國際連動與{target_day_text}趨勢推估 {time_status_text}", unsafe_allow_html=True)

    trend_html = f"""
    <div style='background:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {trend_data['color']}; margin-bottom: 20px; border-top:1px solid #333; border-right:1px solid #333; border-bottom:1px solid #333;'>
        <div style='font-size:1.15rem; font-weight:bold; color:{trend_data['color']}; margin-bottom:10px;'>{trend_data['trend']}</div>
        <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;'>
            <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>費城半導體 (^SOX)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["sox_p"]:,.2f}</b> <span style='font-size:1rem; color:{_trend_color(trend_data["sox"])};'>({trend_data["sox"]:+.2f}%)</span></div>
            <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台積電 ADR (TSM)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["tsm_p"]:,.2f}</b> <span style='font-size:1rem; color:{_trend_color(trend_data["tsm"])};'>({trend_data["tsm"]:+.2f}%)</span></div>
            <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>納斯達克期貨 (NQ=F)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["nq_p"]:,.2f}</b> <span style='font-size:1rem; color:{_trend_color(trend_data["nq"])};'>({trend_data["nq"]:+.2f}%)</span></div>
            <div style='background:#2c2c2c; padding:8px 15px; border-radius:5px;'><span style='color:#aaa; font-size:0.9rem;'>台股 ETF (EWT)</span><br><b style='font-size:1.1rem; color:#fff;'>{trend_data["ewt_p"]:,.2f}</b> <span style='font-size:1rem; color:{_trend_color(trend_data["ewt"])};'>({trend_data["ewt"]:+.2f}%)</span></div>
        </div>
    </div>
    """
    st.markdown(clean_html(trend_html), unsafe_allow_html=True)
    return trend_data
