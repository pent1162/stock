#!/usr/bin/env python3
"""
dashboard.py
整合儀表板：把所有模塊輸出整合成一份美觀的每日 HTML 報告。
整合：選股篩選、公告摘要、放量預警、回測績效、研報解析
"""

import json
import os
import glob
from datetime import datetime
import pandas as pd
from pathlib import Path

OUTPUT_DIR = "/home/sprite/quant/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY     = datetime.now().strftime("%Y%m%d")
TODAY_ISO = datetime.now().strftime("%Y-%m-%d")
GEN_TIME  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── 資料載入工具 ──────────────────────────────────────
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def load_xlsx_screener():
    path = "/home/sprite/quant/output/multi_market_screener.xlsx"
    try:
        df = pd.read_excel(path)
        return df.to_dict(orient="records")
    except Exception:
        return []

def load_all_parsed_reports():
    pattern = os.path.join(OUTPUT_DIR, "parsed_report_*.json")
    files   = sorted(glob.glob(pattern))
    reports = []
    for fp in files:
        data = load_json(fp)
        if data:
            reports.append(data)
    return reports

# ─── HTML 元件 ────────────────────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0d1117;
  color: #c9d1d9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
  font-size: 14px;
  padding: 0 0 40px 0;
}
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.header {
  background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
  border-bottom: 1px solid #30363d;
  padding: 24px 32px 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.header h1 { font-size: 22px; color: #e6edf3; font-weight: 700; }
.header h1 span { color: #58a6ff; }
.header .meta { font-size: 12px; color: #6e7681; text-align: right; }
.market-bar {
  background: #161b22;
  border-bottom: 1px solid #21262d;
  padding: 10px 32px;
  display: flex;
  gap: 24px;
  overflow-x: auto;
  white-space: nowrap;
}
.market-item { font-size: 13px; }
.market-item .name { color: #8b949e; margin-right: 6px; }
.market-item .val  { color: #c9d1d9; font-weight: 600; }
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 32px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.full-width { grid-column: 1 / -1; }
.card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 10px;
  padding: 20px 22px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #21262d;
}
.card-title { font-size: 15px; font-weight: 700; color: #e6edf3; }
.card-badge { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #21262d; color: #8b949e; }
.card-badge.alert { background: #3d1f1f; color: #f85149; }
.card-badge.ok    { background: #1a2e1a; color: #3fb950; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 7px 10px; color: #6e7681; font-weight: 600; border-bottom: 1px solid #21262d; font-size: 11px; text-transform: uppercase; }
.data-table td { padding: 8px 10px; border-bottom: 1px solid #161b22; color: #c9d1d9; }
.data-table tr:hover td { background: #1c2128; }
.data-table tr:last-child td { border-bottom: none; }
.up  { color: #3fb950; font-weight: 600; }
.dn  { color: #f85149; font-weight: 600; }
.neu { color: #8b949e; }
.hi  { color: #58a6ff; font-weight: 600; }
.alert-row { background: #1e1515 !important; }
.vol-ratio { font-size: 13px; font-weight: 700; color: #f0883e; }
.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.metric-box { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 12px 14px; text-align: center; }
.metric-box .m-label { font-size: 10px; color: #6e7681; text-transform: uppercase; margin-bottom: 6px; }
.metric-box .m-val   { font-size: 20px; font-weight: 700; }
.metric-box .m-sub   { font-size: 11px; color: #6e7681; margin-top: 4px; }
.news-item { padding: 10px 0; border-bottom: 1px solid #21262d; }
.news-item:last-child { border-bottom: none; }
.ticker-tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 4px; background: #1f2d3d; color: #58a6ff; margin-right: 6px; font-weight: 600; }
.headline { color: #c9d1d9; margin-top: 4px; line-height: 1.5; }
.report-item { padding: 10px 0; border-bottom: 1px solid #21262d; }
.report-item:last-child { border-bottom: none; }
.report-tag { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 3px; margin-right: 5px; font-weight: 600; }
.tag-buy  { background: #1a3a1a; color: #3fb950; }
.tag-sell { background: #3d1f1f; color: #f85149; }
.tag-hold { background: #2d2a1a; color: #d29922; }
.tag-neutral { background: #21262d; color: #8b949e; }
.equity-img { width: 100%; border-radius: 6px; border: 1px solid #30363d; margin-top: 12px; }
.empty-state { text-align: center; padding: 30px; color: #6e7681; font-size: 13px; }
.footer { text-align: center; padding: 20px; color: #6e7681; font-size: 11px; border-top: 1px solid #21262d; margin-top: 20px; }
"""

def render_market_bar(volume_data):
    items_html = ""
    if volume_data and "all_stocks" in volume_data:
        for s in volume_data["all_stocks"][:12]:
            sign = "+" if s["pct_chg"] >= 0 else ""
            cls  = "up" if s["pct_chg"] >= 0 else "dn"
            items_html += f'<div class="market-item"><span class="name">{s["ticker"]}</span><span class="val">{s["currency_sym"]}{s["close"]:.1f}</span> <span class="{cls}">{sign}{s["pct_chg"]:.1f}%</span></div>'
    return f'<div class="market-bar">{items_html}</div>'

def render_screener_card(records):
    if not records:
        return '<div class="empty-state">選股篩選無數據</div>'
    rows = ""
    for r in records[:20]:
        ticker = r.get("Ticker") or r.get("ticker") or r.get("股票代碼") or "-"
        market = r.get("Market") or r.get("market") or r.get("市場") or "-"
        roe    = r.get("ROE(%)") or "-"
        rev    = r.get("營收增速(%)") or "-"
        pe     = r.get("PE") or "-"
        status = r.get("是否符合條件") or "-"
        cls    = "up" if "符合" in str(status) else "neu"
        rows += f'<tr><td class="hi">{ticker}</td><td class="neu">{market}</td><td>{roe}</td><td>{rev}</td><td>{pe}</td><td class="{cls}">{status}</td></tr>'
    return f'<table class="data-table"><thead><tr><th>Ticker</th><th>市場</th><th>ROE%</th><th>營收增速%</th><th>PE</th><th>狀態</th></tr></thead><tbody>{rows}</tbody></table>'

def render_volume_card(data):
    if not data:
        return '<div class="card-header"><span class="card-title">🚨 放量預警</span></div><div class="empty-state">無數據</div>'
    alerts    = data.get("alerts", [])
    threshold = data.get("threshold", 5)
    all_stocks = sorted(data.get("all_stocks", []), key=lambda x: x["ratio"], reverse=True)
    rows = ""
    for s in all_stocks[:15]:
        is_alert = s["ratio"] >= threshold
        row_cls  = 'class="alert-row"' if is_alert else ""
        sign     = "+" if s["pct_chg"] >= 0 else ""
        pct_cls  = "up" if s["pct_chg"] >= 0 else "dn"
        alert_tag = "🚨 " if is_alert else ""
        vol_m = s["today_vol"] / 1_000_000
        ma_m  = s["ma20_vol"]  / 1_000_000
        rows += f'<tr {row_cls}><td class="hi">{alert_tag}{s["ticker"]}</td><td class="neu">{s["market"]}</td><td class="vol-ratio">{s["ratio"]:.1f}x</td><td>{s["currency_sym"]}{s["close"]:.1f}</td><td class="{pct_cls}">{sign}{s["pct_chg"]:.1f}%</td><td class="neu">{vol_m:.1f}M</td><td class="neu">{ma_m:.1f}M</td></tr>'
    badge_cls = "alert" if alerts else "ok"
    badge_txt = f"{len(alerts)} 支觸發" if alerts else "無異常"
    return f'<div class="card-header"><span class="card-title">🚨 放量預警</span><span class="card-badge {badge_cls}">{badge_txt}</span></div><table class="data-table"><thead><tr><th>Ticker</th><th>市場</th><th>量比</th><th>收盤</th><th>漲跌</th><th>今量</th><th>均量20D</th></tr></thead><tbody>{rows}</tbody></table>'

def render_backtest_card(data):
    if not data:
        return '<div class="empty-state">回測數據未找到（請先執行 backtest.py）</div>'
    pm  = data.get("metrics", {}).get("portfolio", {})
    bm  = data.get("metrics", {}).get("benchmark",  {})
    cfg = data.get("config", {})
    img_tag = ""
    if os.path.exists(os.path.join(OUTPUT_DIR, "backtest_equity_curve.png")):
        img_tag = '<img src="backtest_equity_curve.png" class="equity-img" alt="Equity Curve" />'
    cagr_cls = "up" if (pm.get("cagr") or 0) >= 0 else "dn"
    return f'''<div class="metrics-grid">
      <div class="metric-box"><div class="m-label">CAGR</div><div class="m-val {cagr_cls}">{pm.get("cagr","N/A"):+.1f}%</div><div class="m-sub">vs SPY {bm.get("cagr","N/A"):+.1f}%</div></div>
      <div class="metric-box"><div class="m-label">Max Drawdown</div><div class="m-val dn">{pm.get("max_drawdown","N/A"):.1f}%</div><div class="m-sub">vs SPY {bm.get("max_drawdown","N/A"):.1f}%</div></div>
      <div class="metric-box"><div class="m-label">Sharpe Ratio</div><div class="m-val hi">{pm.get("sharpe","N/A"):.2f}</div><div class="m-sub">vs SPY {bm.get("sharpe","N/A"):.2f}</div></div>
      <div class="metric-box"><div class="m-label">月勝率</div><div class="m-val neu">{pm.get("win_rate","N/A"):.1f}%</div><div class="m-sub">vs SPY {bm.get("win_rate","N/A"):.1f}%</div></div>
    </div>
    <div style="font-size:12px;color:#6e7681;margin-bottom:10px;">股票池: {", ".join(cfg.get("qualified",[])[:6])} | 調倉: {cfg.get("rebalance","quarterly")} | 期間: {cfg.get("start_date","")} ~ {cfg.get("end_date","")}</div>
    {img_tag}'''

def render_news_card(news_data):
    if not news_data:
        return '<div class="empty-state">今日公告摘要無數據</div>'
    markets = news_data.get("markets", {})
    html = ""
    for market, items in markets.items():
        for item in items[:4]:
            ticker   = item.get("ticker", "")
            headline = item.get("title", "")[:100]
            emoji    = item.get("category_emoji", "🟡")
            html += f'<div class="news-item"><span class="ticker-tag">{ticker}</span><span>{emoji}</span><div class="headline">{headline}</div></div>'
    return html or '<div class="empty-state">暫無公告</div>'

def render_reports_card(reports):
    if not reports:
        return '<div class="empty-state">無研報解析結果</div>'
    html = ""
    for rpt in reports[:8]:
        ticker = rpt.get("ticker") or "-"
        rating = (rpt.get("rating") or "neutral").lower()
        tp     = rpt.get("target_price") or ""
        thesis = rpt.get("thesis") or []
        if isinstance(thesis, list) and thesis:
            summary = thesis[0][:100]
        else:
            summary = ""
        if "buy" in rating or "增持" in rating or "outperform" in rating:
            tag_cls, tag_txt = "tag-buy", "買入"
        elif "sell" in rating or "減持" in rating or "underperform" in rating:
            tag_cls, tag_txt = "tag-sell", "賣出"
        elif "hold" in rating or "neutral" in rating:
            tag_cls, tag_txt = "tag-hold", "持有"
        else:
            tag_cls, tag_txt = "tag-neutral", rating.upper() or "N/A"
        tp_str = f" TP: {tp}" if tp else ""
        html += f'<div class="report-item"><span class="ticker-tag">{ticker}</span><span class="report-tag {tag_cls}">{tag_txt}</span><span style="font-size:11px;color:#6e7681;">{tp_str}</span>{"<div style=color:#8b949e;font-size:12px;margin-top:3px>" + summary + "</div>" if summary else ""}</div>'
    return html

def build_html(screener, news_data, volume_data, backtest_data, reports):
    alert_count  = len(volume_data.get("alerts", [])) if volume_data else 0
    screen_count = len(screener)
    report_count = len(reports)
    market_bar   = render_market_bar(volume_data)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Quant Dashboard — {TODAY_ISO}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="header">
  <div><h1>📊 Quant <span>Dashboard</span></h1><div style="font-size:13px;color:#8b949e;margin-top:4px;">{TODAY_ISO}</div></div>
  <div class="meta">選股 <strong style="color:#58a6ff">{screen_count}</strong> 支 | 放量預警 <strong style="color:#f85149">{alert_count}</strong> 支 | 研報 <strong style="color:#58a6ff">{report_count}</strong> 份<div style="margin-top:4px;color:#8b949e;">生成時間：{GEN_TIME} UTC</div></div>
</div>
{market_bar}
<div class="container">
  <div class="card">
    <div class="card-header"><span class="card-title">🔍 選股篩選結果</span><span class="card-badge">{screen_count} 支</span></div>
    {render_screener_card(screener)}
  </div>
  <div class="card">{render_volume_card(volume_data)}</div>
  <div class="card">
    <div class="card-header"><span class="card-title">📰 今日公告摘要</span><span class="card-badge">News Digest</span></div>
    {render_news_card(news_data)}
  </div>
  <div class="card">
    <div class="card-header"><span class="card-title">📋 研報解析</span><span class="card-badge">{report_count} 份</span></div>
    {render_reports_card(reports)}
  </div>
  <div class="card full-width">
    <div class="card-header"><span class="card-title">📈 回測績效摘要</span><span class="card-badge">2022–2025 · 季度調倉</span></div>
    {render_backtest_card(backtest_data)}
  </div>
</div>
<div class="footer">Quant Dashboard · Generated at {GEN_TIME} UTC | Data sources: yfinance · For informational purposes only</div>
</body>
</html>"""

def run_dashboard():
    print(f"[dashboard] 生成每日報告 {TODAY_ISO}...")
    screener = load_xlsx_screener()
    print(f"  選股結果: {len(screener)} 筆")
    news_path = os.path.join(OUTPUT_DIR, f"news_digest_{TODAY}.json")
    news_data = load_json(news_path)
    if not news_data:
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "news_digest_*.json")), reverse=True)
        news_data = load_json(files[0]) if files else None
    vol_path = os.path.join(OUTPUT_DIR, f"volume_alert_{TODAY}.json")
    vol_data = load_json(vol_path)
    if not vol_data:
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "volume_alert_*.json")), reverse=True)
        vol_data = load_json(files[0]) if files else None
    bt_data  = load_json(os.path.join(OUTPUT_DIR, "backtest_result.json"))
    reports  = load_all_parsed_reports()
    html     = build_html(screener, news_data, vol_data, bt_data, reports)
    out_path = os.path.join(OUTPUT_DIR, f"dashboard_{TODAY}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n[dashboard] HTML 報告已儲存: {out_path}")
    print(f"  檔案大小: {os.path.getsize(out_path):,} bytes")
    return out_path

if __name__ == "__main__":
    run_dashboard()
