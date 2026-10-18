# BTC VIP 3.1

Bitstamp BTC/USD M5, M15, H1 closed-candle indicator API. Does not use TradingView API. GET `/api/signal` for fresh data and `/health` for status. A trend bias is NOT an entry signal; the service returns CHO until confirmed entry logic is implemented and tested. Render: Python, build `pip install -r requirements.txt`, start `gunicorn app:app`, free plan.
