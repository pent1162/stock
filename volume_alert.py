#!/usr/bin/env python3
"""
volume_alert.py
放量預警：監控美股、台股、日股成分股，當日成交量 > 過去20日均量的5倍時觸發警報。
"""

import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ─── 設定 ─────────────────────────────────────────────
STOCKS = {
    "US": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "TSLA", "JPM"],
    "TW": ["2330.TW", "2454.TW", "2382.TW", "2317.TW"],
    "JP": ["7203.T", "6758.T", "9984.T"],
}
ALERT_THRESHOLD = 5.0   # 倍數門檻
LOOKBACK_DAYS  = 30     # 抓取天數
MA_WINDOW      = 20     # 均量窗口

OUTPUT_DIR = "/home/sprite/quant/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CURRENCY = {
    "US": "$", "TW": "NT$", "JP": "¥"
}

# ─── 主邏輯 ───────────────────────────────────────────
def run_volume_alert():
    today_str = datetime.now().strftime("%Y%m%d")
    today_label = datetime.now().strftime("%Y-%m-%d")

    alerts = []
    all_data = []

    all_tickers = []
    ticker_market = {}
    for market, tickers in STOCKS.items():
        for t in tickers:
            all_tickers.append(t)
            ticker_market[t] = market

    print(f"[volume_alert] 抓取 {len(all_tickers)} 支股票最近 {LOOKBACK_DAYS} 天數據...")

    for ticker in all_tickers:
        try:
            df = yf.download(
                ticker,
                period=f"{LOOKBACK_DAYS}d",
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            if df is None or len(df) < MA_WINDOW + 1:
                print(f"  [{ticker}] 數據不足，跳過")
                continue

            # 確保欄位名稱正確
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.dropna(subset=["Volume", "Close"])

            # 取最後一筆作為「今日」
            today_vol   = float(df["Volume"].iloc[-1])
            today_close = float(df["Close"].iloc[-1])

            # 前一日收盤（計算漲跌）
            prev_close  = float(df["Close"].iloc[-2]) if len(df) >= 2 else today_close
            pct_chg     = (today_close - prev_close) / prev_close * 100 if prev_close else 0

            # 20日均量（不含今日）
            ma_vol = float(df["Volume"].iloc[-MA_WINDOW-1:-1].mean())

            ratio  = today_vol / ma_vol if ma_vol > 0 else 0

            market = ticker_market[ticker]
            sym    = CURRENCY.get(market, "")

            record = {
                "ticker":      ticker,
                "market":      market,
                "today_vol":   round(today_vol),
                "ma20_vol":    round(ma_vol),
                "ratio":       round(ratio, 2),
                "close":       round(today_close, 2),
                "pct_chg":     round(pct_chg, 2),
                "alert":       ratio > ALERT_THRESHOLD,
                "currency_sym": sym,
            }
            all_data.append(record)

            if ratio > ALERT_THRESHOLD:
                alerts.append(record)
                print(f"  *** ALERT *** {ticker}: {ratio:.1f}x 均量")
            else:
                print(f"  [{ticker}] {ratio:.2f}x (正常)")

        except Exception as e:
            print(f"  [{ticker}] 錯誤: {e}")

    # ─── 輸出 JSON ────────────────────────────────────
    json_path = os.path.join(OUTPUT_DIR, f"volume_alert_{today_str}.json")
    output = {
        "date":       today_label,
        "threshold":  ALERT_THRESHOLD,
        "alerts":     alerts,
        "all_stocks": all_data,
        "generated_at": datetime.now().isoformat(),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[volume_alert] JSON 已儲存: {json_path}")

    # ─── 輸出 Telegram 友好文字 ───────────────────────
    txt_path = os.path.join(OUTPUT_DIR, f"volume_alert_{today_str}.txt")
    lines = [f"🚨 放量預警 {today_label}\n"]

    if not alerts:
        lines.append("✅ 今日無放量異常股票")
    else:
        for r in sorted(alerts, key=lambda x: x["ratio"], reverse=True):
            sign   = "+" if r["pct_chg"] >= 0 else ""
            sym    = r["currency_sym"]
            vol_m  = r["today_vol"]  / 1_000_000
            ma_m   = r["ma20_vol"]   / 1_000_000
            unit   = "M" if vol_m >= 1 else "K"
            vol_d  = vol_m if unit == "M" else r["today_vol"] / 1_000
            ma_d   = ma_m  if unit == "M" else r["ma20_vol"]  / 1_000

            lines.append(
                f"{r['ticker']}｜放量 {r['ratio']:.1f}倍｜收盤 {sym}{r['close']:.1f}｜{sign}{r['pct_chg']:.1f}%"
            )
            lines.append(
                f"成交量：{vol_d:.1f}{unit} vs 均量 {ma_d:.1f}{unit}\n"
            )

    lines.append(f"\n共掃描 {len(all_data)} 支股票，觸發警報 {len(alerts)} 支")

    txt_content = "\n".join(lines)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    print(f"[volume_alert] TXT 已儲存: {txt_path}")
    print("\n" + "="*50)
    print(txt_content)
    print("="*50)

    return output


if __name__ == "__main__":
    run_volume_alert()
