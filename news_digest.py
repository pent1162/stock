#!/usr/bin/env python3
"""
每日公告摘要腳本
自動抓取美股、台股、日股、A股最新公告/新聞，分類整理成結構化報告
"""

import json
import time
import re
from datetime import datetime
from collections import defaultdict

try:
    import yfinance as yf
except ImportError:
    raise SystemExit("請先安裝 yfinance: pip install yfinance")

# ─── 股票清單 ───────────────────────────────────────────────
STOCKS = {
    "US":  ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "TSLA", "JPM"],
    "TW":  ["2330.TW", "2454.TW", "2382.TW", "2317.TW"],
    "JP":  ["7203.T", "6758.T", "9984.T"],
    "CN":  ["600519", "000858", "300750"],
}

MARKET_FLAG = {"US": "🇺🇸", "TW": "🇹🇼", "JP": "🇯🇵", "CN": "🇨🇳"}
MARKET_NAME = {"US": "美股", "TW": "台股", "JP": "日股", "CN": "A股"}

# ─── 分類關鍵字 ─────────────────────────────────────────────
BULLISH_KW = [
    "beat", "record", "buyback", "dividend", "acquisition", "surge", "rally",
    "upgrade", "bullish", "profit", "growth", "wins", "awarded", "contract",
    "業績增長", "回購", "分紅", "中標", "合同", "增長", "創新高", "訂單"
]
BEARISH_KW = [
    "miss", "loss", "recall", "lawsuit", "fine", "sec", "probe", "investigation",
    "downgrade", "bearish", "decline", "drop", "cut", "warning", "risk",
    "虧損", "業績下滑", "罰款", "訴訟", "調查", "下滑", "虧損"
]
EARNINGS_KW = [
    "earnings", "revenue", "quarterly", "annual", "eps", "results", "guidance",
    "fiscal", "q1", "q2", "q3", "q4", "forecast", "outlook",
    "季報", "年報", "業績預告", "財報"
]


def classify_news(title: str) -> tuple[str, str]:
    """根據標題關鍵字分類，回傳 (emoji, label)"""
    t = title.lower()
    # 財報優先度低，先查利好/利空
    is_bullish = any(kw in t for kw in BULLISH_KW)
    is_bearish = any(kw in t for kw in BEARISH_KW)
    is_earnings = any(kw in t for kw in EARNINGS_KW)

    if is_bullish and not is_bearish:
        return "🟢", "重大利好"
    elif is_bearish and not is_bullish:
        return "🔴", "重大利空"
    elif is_earnings:
        return "📊", "財報相關"
    else:
        return "🟡", "中性公告"


def fetch_yfinance_news(ticker: str, max_news: int = 5) -> list[dict]:
    """用 yfinance 抓單支股票新聞"""
    try:
        t = yf.Ticker(ticker)
        raw = t.news
        if not raw:
            return []
        results = []
        for item in raw[:max_news]:
            # yfinance >= 0.2.x 新聞結構
            content = item.get("content", {})
            if isinstance(content, dict):
                title = content.get("title", "") or item.get("title", "")
                url   = ""
                click = content.get("clickThroughUrl") or content.get("canonicalUrl") or {}
                if isinstance(click, dict):
                    url = click.get("url", "")
                summary = content.get("summary", "") or ""
                pub_raw = content.get("pubDate", "") or ""
            else:
                title   = item.get("title", "")
                url     = item.get("link", "")
                summary = item.get("summary", "") or ""
                pub_raw = item.get("providerPublishTime", "")
                if isinstance(pub_raw, (int, float)):
                    pub_raw = datetime.utcfromtimestamp(pub_raw).strftime("%Y-%m-%d %H:%M")

            if not title:
                continue

            emoji, label = classify_news(title)
            results.append({
                "ticker": ticker,
                "title": title,
                "url": url,
                "summary": summary[:200] if summary else "",
                "published": str(pub_raw)[:16],
                "category_emoji": emoji,
                "category_label": label,
            })
        return results
    except Exception as e:
        print(f"  [WARN] {ticker} yfinance 失敗: {e}")
        return []


def fetch_akshare_news(symbol: str) -> list[dict]:
    """用 akshare 抓 A 股新聞，網路不通直接跳過"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=symbol)
        if df is None or df.empty:
            return []
        results = []
        # 欄位：關鍵詞, 新聞標題, 新聞內容, 發布時間, 文章來源, 新聞連結
        seen = set()
        for _, row in df.head(5).iterrows():
            title = str(row.get("新聞標題", "") or row.get("title", ""))
            if not title or title in seen:
                continue
            seen.add(title)
            url     = str(row.get("新聞連結", "") or row.get("url", ""))
            pub_raw = str(row.get("發布時間", "") or row.get("pub_time", ""))[:16]
            emoji, label = classify_news(title)
            results.append({
                "ticker": symbol,
                "title": title,
                "url": url,
                "summary": "",
                "published": pub_raw,
                "category_emoji": emoji,
                "category_label": label,
            })
        return results
    except Exception as e:
        print(f"  [SKIP] A股 {symbol} akshare 跳過: {e}")
        return []


def deduplicate(news_list: list[dict]) -> list[dict]:
    """去除重複標題"""
    seen = set()
    out = []
    for n in news_list:
        key = n["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            out.append(n)
    return out


def build_telegram_report(all_news: dict, today: str) -> str:
    """生成 Telegram 格式文字報告"""
    lines = [f"📰 每日公告摘要 - {today}", ""]

    total = 0
    bullish = 0
    bearish = 0

    for market in ["US", "TW", "JP", "CN"]:
        items = all_news.get(market, [])
        if not items:
            continue
        flag = MARKET_FLAG[market]
        name = MARKET_NAME[market]
        lines.append(f"{flag} {name}")
        for n in items:
            short_title = n["title"][:60] + ("..." if len(n["title"]) > 60 else "")
            lines.append(f"{n['category_emoji']} {n['ticker']} | {short_title}")
            total += 1
            if n["category_emoji"] == "🟢":
                bullish += 1
            elif n["category_emoji"] == "🔴":
                bearish += 1
        lines.append("")

    lines.append(f"共 {total} 則公告，其中 {bullish} 則重大利好，{bearish} 則重大利空")
    return "\n".join(lines)


def print_terminal_report(all_news: dict, today: str):
    """終端打印分市場、分類別報告"""
    print("\n" + "═" * 60)
    print(f"  📰 每日公告摘要  {today}")
    print("═" * 60)

    cat_order = ["🟢", "🔴", "📊", "🟡"]
    cat_name  = {"🟢": "重大利好", "🔴": "重大利空", "📊": "財報相關", "🟡": "中性公告"}

    for market in ["US", "TW", "JP", "CN"]:
        items = all_news.get(market, [])
        if not items:
            continue
        flag = MARKET_FLAG[market]
        name = MARKET_NAME[market]
        print(f"\n{flag}  {name} ({len(items)} 則)")
        print("-" * 50)

        grouped = defaultdict(list)
        for n in items:
            grouped[n["category_emoji"]].append(n)

        for emoji in cat_order:
            if emoji not in grouped:
                continue
            print(f"  {emoji} {cat_name[emoji]}")
            for n in grouped[emoji]:
                title = n["title"][:70] + ("..." if len(n["title"]) > 70 else "")
                print(f"    [{n['ticker']}] {title}")
                if n["published"]:
                    print(f"           時間: {n['published']}")

    print("\n" + "═" * 60)


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    date_str = datetime.now().strftime("%Y%m%d")
    all_news: dict[str, list[dict]] = {}

    # ── 美股、台股、日股 via yfinance ──
    for market in ["US", "TW", "JP"]:
        print(f"\n抓取 {MARKET_NAME[market]} 新聞...")
        collected = []
        for ticker in STOCKS[market]:
            print(f"  {ticker} ...", end="", flush=True)
            news = fetch_yfinance_news(ticker, max_news=5)
            print(f" {len(news)} 則")
            collected.extend(news)
            time.sleep(0.5)  # rate limiting
        all_news[market] = deduplicate(collected)

    # ── A股 via akshare ──
    print(f"\n抓取 A股 新聞（akshare，失敗自動跳過）...")
    cn_collected = []
    for symbol in STOCKS["CN"]:
        print(f"  {symbol} ...", end="", flush=True)
        news = fetch_akshare_news(symbol)
        print(f" {len(news)} 則")
        cn_collected.extend(news)
        time.sleep(0.5)
    all_news["CN"] = deduplicate(cn_collected)

    # ── 終端報告 ──
    print_terminal_report(all_news, today)

    # ── 儲存 JSON ──
    json_path = f"/home/sprite/quant/output/news_digest_{date_str}.json"
    payload = {
        "date": today,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "markets": all_news,
        "stats": {
            "total": sum(len(v) for v in all_news.values()),
            "bullish": sum(1 for v in all_news.values() for n in v if n["category_emoji"] == "🟢"),
            "bearish": sum(1 for v in all_news.values() for n in v if n["category_emoji"] == "🔴"),
        }
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON 已儲存: {json_path}")

    # ── 儲存 Telegram 報告 ──
    tg_path = f"/home/sprite/quant/output/news_telegram_{date_str}.txt"
    tg_report = build_telegram_report(all_news, today)
    with open(tg_path, "w", encoding="utf-8") as f:
        f.write(tg_report)
    print(f"✅ Telegram 報告已儲存: {tg_path}")

    # ── 打印完整 Telegram 報告 ──
    print("\n" + "─" * 60)
    print("  Telegram 報告預覽")
    print("─" * 60)
    print(tg_report)
    print("─" * 60)


if __name__ == "__main__":
    main()
