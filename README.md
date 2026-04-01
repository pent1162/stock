# Quant Trading System

Multi-market quantitative trading system covering US, Taiwan, Japan, and China A-shares.

## Modules
- `screener_multi.py` — Multi-market stock screener (ROE, Revenue Growth, PE filters)
- `news_digest.py` — Daily news digest with sentiment classification
- `research_parser.py` — PDF research report parser (extracts target price, rating, key factors)
- `volume_alert.py` — Volume spike alert (>5x average volume)
- `backtest.py` — Historical backtest engine with performance metrics
- `dashboard.py` — Daily HTML dashboard integrating all modules

## Schedule (Taipei Time)
- Mon 08:00 — Weekly stock screener
- Mon-Fri 09:30 — Volume spike alerts
- Mon-Fri 15:30 — Japan market close digest
- Mon-Fri 17:00 — US + Taiwan news digest
- Mon-Fri 17:30 — Daily integrated dashboard
