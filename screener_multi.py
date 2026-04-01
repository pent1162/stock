#!/usr/bin/env python3
"""
Multi-Market Stock Screener
Markets: A-shares (CN), US, Japan, Taiwan
Criteria:
  - ROE > 15%
  - Revenue YoY Growth > 10%
  - PE < 30 (Japan: < 40)
"""

import warnings
warnings.filterwarnings("ignore")

import os
import time
import pandas as pd
import yfinance as yf

OUTPUT_DIR = "/home/sprite/quant/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "multi_market_screener.xlsx")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Ticker Lists ────────────────────────────────────────────────────────────────
US_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "LLY",
    "JPM", "V", "UNH", "XOM", "TSLA", "JNJ", "WMT", "MA", "PG", "HD",
    "CVX", "MRK"
]
JP_TICKERS = [
    "7203.T", "6758.T", "9984.T", "8306.T", "6861.T", "9432.T", "7974.T",
    "6501.T", "4502.T", "8411.T", "9433.T", "6902.T", "7267.T", "6954.T",
    "4661.T", "8035.T", "2914.T", "9022.T", "7751.T", "6752.T"
]
TW_TICKERS = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "3711.TW",
    "2303.TW", "2891.TW", "2882.TW", "1303.TW", "2886.TW", "2884.TW",
    "1301.TW", "2881.TW", "2002.TW", "5880.TW", "2412.TW", "3034.TW",
    "4938.TW", "2207.TW"
]

# ── Helpers ─────────────────────────────────────────────────────────────────────
def safe_float(val):
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except Exception:
        return None

def pct(val):
    if val is None:
        return None
    return round(val * 100, 2)


# ── yfinance fetch (US / JP / TW) ───────────────────────────────────────────────
def fetch_yf_stocks(tickers, market):
    rows = []
    for tkr in tickers:
        try:
            t = yf.Ticker(tkr)
            info = t.info or {}

            name  = info.get("longName") or info.get("shortName") or tkr
            roe   = safe_float(info.get("returnOnEquity"))
            pe    = safe_float(info.get("trailingPE") or info.get("forwardPE"))

            rev_growth = None
            try:
                fin = t.financials
                if fin is not None and not fin.empty:
                    rev_row = None
                    for label in ["Total Revenue", "Revenue"]:
                        if label in fin.index:
                            rev_row = fin.loc[label]
                            break
                    if rev_row is not None and len(rev_row) >= 2:
                        r0 = safe_float(rev_row.iloc[0])
                        r1 = safe_float(rev_row.iloc[1])
                        if r0 and r1 and r1 != 0:
                            rev_growth = (r0 - r1) / abs(r1)
            except Exception:
                pass

            if rev_growth is None:
                rev_growth = safe_float(info.get("revenueGrowth"))

            rows.append({
                "股票代碼":   tkr,
                "股票名稱":   name,
                "市場":       market,
                "ROE(%)":     pct(roe),
                "營收增速(%)": pct(rev_growth),
                "PE":          round(pe, 2) if pe else None,
            })
            time.sleep(0.3)
        except Exception as e:
            print(f"  [WARN] {tkr}: {e}")
            rows.append({"股票代碼": tkr, "股票名稱": tkr, "市場": market,
                         "ROE(%)": None, "營收增速(%)": None, "PE": None})
    return pd.DataFrame(rows)


def fetch_us_stocks():
    print("[US] Fetching S&P 500 sample ...")
    return fetch_yf_stocks(US_TICKERS, "美股")

def fetch_jp_stocks():
    print("[JP] Fetching Nikkei 225 sample ...")
    return fetch_yf_stocks(JP_TICKERS, "日股")

def fetch_tw_stocks():
    print("[TW] Fetching Taiwan 50 sample ...")
    return fetch_yf_stocks(TW_TICKERS, "台股")


# ── A-shares via akshare ────────────────────────────────────────────────────────
def fetch_a_shares():
    print("[CN] Fetching CSI 300 sample ...")
    rows = []
    try:
        import akshare as ak

        # CSI 300 constituent list
        hs300  = ak.index_stock_cons(symbol="000300")
        codes  = hs300["品种代码"].astype(str).tolist()[:20]
        names  = dict(zip(hs300["品种代码"].astype(str), hs300["品种名称"]))
        print(f"  CSI300 list OK, using first {len(codes)} codes")

        # Batch fetch real-time PE once
        pe_map = {}
        try:
            df_rt    = ak.stock_zh_a_spot_em()
            pe_col   = next((c for c in df_rt.columns if "市盈率" in c), None)
            code_col = next((c for c in df_rt.columns if "代码" in c), df_rt.columns[0])
            if pe_col:
                for _, r in df_rt.iterrows():
                    pe_map[str(r[code_col])] = safe_float(r[pe_col])
            print(f"  PE map built: {len(pe_map)} stocks")
        except Exception as e:
            print(f"  [WARN] PE batch fetch: {e}")

        for code in codes:
            name          = names.get(code, code)
            roe_val       = None
            rev_growth_val = None
            pe_val        = pe_map.get(code)

            # ROE
            try:
                df_fin  = ak.stock_financial_analysis_indicator(symbol=code, start_year="2023")
                if df_fin is not None and not df_fin.empty:
                    roe_col = next((c for c in df_fin.columns
                                    if "净资产收益率" in c or "加权净资产收益率" in c), None)
                    if roe_col:
                        annual = df_fin[df_fin["日期"].astype(str).str.endswith("12-31")]
                        src    = annual if not annual.empty else df_fin
                        v      = safe_float(src.iloc[0][roe_col])
                        roe_val = round(v, 2) if v is not None else None
            except Exception as e:
                print(f"  [WARN] ROE {code}: {e}")

            # Revenue YoY
            try:
                df_abs  = ak.stock_financial_abstract(symbol=code)
                rev_row = df_abs[df_abs["指标"] == "营业总收入"]
                if rev_row.empty:
                    rev_row = df_abs[df_abs["指标"].str.contains("营业.*收入", na=False)]
                if not rev_row.empty:
                    date_cols = [c for c in df_abs.columns
                                 if str(c).isdigit() and len(str(c)) == 8 and str(c).endswith("1231")]
                    if len(date_cols) >= 2:
                        r0 = safe_float(rev_row.iloc[0][date_cols[0]])
                        r1 = safe_float(rev_row.iloc[0][date_cols[1]])
                        if r0 and r1 and r1 != 0:
                            rev_growth_val = round((r0 - r1) / abs(r1) * 100, 2)
            except Exception as e:
                print(f"  [WARN] Rev {code}: {e}")

            rows.append({
                "股票代碼":   code,
                "股票名稱":   name,
                "市場":       "A股",
                "ROE(%)":     roe_val,
                "營收增速(%)": rev_growth_val,
                "PE":          pe_val,
            })
            time.sleep(0.5)

    except Exception as e:
        print(f"  [WARN] akshare A-share fetch failed: {e}")

    if not rows:
        return pd.DataFrame(columns=["股票代碼","股票名稱","市場","ROE(%)","營收增速(%)","PE"])
    return pd.DataFrame(rows)


# ── Screening logic ─────────────────────────────────────────────────────────────
def screen_stocks(df, market):
    pe_threshold = 40 if market == "日股" else 30

    def qualifies(row):
        roe = row["ROE(%)"]
        rev = row["營收增速(%)"]
        pe  = row["PE"]
        if roe is None or rev is None or pe is None:
            return False
        return (roe > 15) and (rev > 10) and (pe < pe_threshold)

    df = df.copy()
    df["是否符合條件"] = df.apply(qualifies, axis=1).map({True: "✓ 符合", False: "✗ 不符合"})
    return df


# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Multi-Market Stock Screener")
    print("=" * 60)

    dfs = {}
    dfs["A股"] = fetch_a_shares()
    dfs["美股"] = fetch_us_stocks()
    dfs["日股"] = fetch_jp_stocks()
    dfs["台股"] = fetch_tw_stocks()

    screened = {}
    for market, df in dfs.items():
        screened[market] = screen_stocks(df, market)

    print()
    print("=" * 60)
    print("  篩選摘要")
    print("=" * 60)
    total_pass = 0
    for market, df in screened.items():
        n_total = len(df)
        n_pass  = (df["是否符合條件"] == "✓ 符合").sum()
        total_pass += n_pass
        pe_thr = 40 if market == "日股" else 30
        print(f"  {market}：{n_pass}/{n_total} 支符合條件  (ROE>15%, 營收增速>10%, PE<{pe_thr})")
    print(f"  合計：{total_pass} 支")
    print()

    all_df   = pd.concat(screened.values(), ignore_index=True)
    passing  = all_df[all_df["是否符合條件"] == "✓ 符合"][
        ["市場","股票代碼","股票名稱","ROE(%)","營收增速(%)","PE"]
    ]
    if not passing.empty:
        print("  符合條件股票：")
        print(passing.to_string(index=False))
    else:
        print("  （無股票通過所有條件）")
    print()

    col_order = ["股票代碼","股票名稱","市場","ROE(%)","營收增速(%)","PE","是否符合條件"]
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for market, df in screened.items():
            out_cols = [c for c in col_order if c in df.columns]
            df[out_cols].to_excel(writer, sheet_name=market, index=False)
    print(f"  Excel 已儲存：{OUTPUT_FILE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
