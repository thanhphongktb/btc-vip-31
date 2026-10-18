import os, json, time, math, urllib.request
from datetime import datetime, timezone
from flask import Flask, jsonify, Response
app = Flask(__name__)
BASE = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"
FRAMES = {"M5":300,"M15":900,"H1":3600}
def fetch(step):
    url=f"{BASE}?step={step}&limit=300&exclude_current_candle=true"
    req=urllib.request.Request(url,headers={"User-Agent":"BTCVIP31/1.0"})
    with urllib.request.urlopen(req,timeout=12) as r:
        raw=json.load(r)
    rows=raw["data"]["ohlc"]
    out=sorted([{"t":int(x["timestamp"]),"o":float(x["open"]),"h":float(x["high"]),"l":float(x["low"]),"c":float(x["close"]),"v":float(x["volume"])} for x in rows],key=lambda x:x["t"])
    if len(out)<210: raise ValueError("Insufficient candles")
    return out
def ema(xs,n):
    k=2/(n+1); v=sum(xs[:n])/n
    for x in xs[n:]: v=x*k+v*(1-k)
    return v
def rsi(xs,n=14):
    diffs=[xs[i]-xs[i-1] for i in range(1,len(xs))]
    gains=[max(d,0) for d in diffs]; losses=[max(-d,0) for d in diffs]
    ag=sum(gains[:n])/n; al=sum(losses[:n])/n
    for g,l in zip(gains[n:],losses[n:]): ag=(ag*(n-1)+g)/n; al=(al*(n-1)+l)/n
    return 100 if al==0 else 100-100/(1+ag/al)
def atr(rows,n=14):
    tr=[max(rows[i]["h"]-rows[i]["l"],abs(rows[i]["h"]-rows[i-1]["c"]),abs(rows[i]["l"]-rows[i-1]["c"])) for i in range(1,len(rows))]
    a=sum(tr[:n])/n
    for x in tr[n:]: a=(a*(n-1)+x)/n
    return a
def analyze(rows,step):
    now=int(time.time()); last=rows[-1]; age=now-(last["t"]+step)
    if age < -15 or age > step+90: raise ValueError(f"Stale or unclosed candle: age_seconds={age}")
    closes=[x["c"] for x in rows]; e20=ema(closes,20); e50=ema(closes,50); e200=ema(closes,200)
    rs=rsi(closes); av=atr(rows)
    previous=rows[-21:-1]
    support=min(x["l"] for x in previous); resistance=max(x["h"] for x in previous)
    trend="UP" if last["c"]>e20>e50>e200 else "DOWN" if last["c"]<e20<e50<e200 else "MIXED"
    return {"close":round(last["c"],2),"closed_candle_utc":datetime.fromtimestamp(last["t"]+step,timezone.utc).isoformat(),"age_seconds":age,"ema20":round(e20,2),"ema50":round(e50,2),"ema200":round(e200,2),"rsi14":round(rs,2),"atr14":round(av,2),"support_20":round(support,2),"resistance_20":round(resistance,2),"trend":trend}
@app.get("/")
def home():
    return jsonify({"name":"BTC VIP 3.1","source":"Bitstamp BTC/USD, not TradingView API","routes":["/health","/api/signal","/openapi.yaml"]})
@app.get("/health")
def health(): return jsonify({"status":"ok","utc":datetime.now(timezone.utc).isoformat()})
@app.get("/api/signal")
def signal():
    try:
        frames={k:analyze(fetch(v),v) for k,v in FRAMES.items()}
        m5,m15,h1=(frames[x] for x in ("M5","M15","H1"))
        direction="BUY" if all(x["trend"]=="UP" for x in (m5,m15,h1)) and 50<=m5["rsi14"]<=70 else "SELL" if all(x["trend"]=="DOWN" for x in (m5,m15,h1)) and 30<=m5["rsi14"]<=50 else "CHO"
        # Trend alignment alone is NOT a sufficient entry trigger.
        return jsonify({"status":"ok","symbol":"BITSTAMP:BTCUSD","actual_data_source":"Bitstamp public OHLC API","time_utc":datetime.now(timezone.utc).isoformat(),"frames":frames,"trend_bias":direction,"signal":"CHO","entry":None,"sl":None,"tp1":None,"tp2":None,"reason":"No validated breakout/retest or pullback confirmation; trend bias is not an executable entry.","warning":"Not investment advice. Validate against your broker quotes."})
    except Exception as e:
        return jsonify({"status":"unavailable","signal":"CHO","error":str(e),"time_utc":datetime.now(timezone.utc).isoformat()}),503
@app.get("/openapi.yaml")
def schema():
    return Response("""openapi: 3.1.0
info:
  title: BTC VIP 3.1 Signal API
  version: 1.0.0
servers:
  - url: https://REPLACE_WITH_RENDER_DOMAIN
paths:
  /api/signal:
    get:
      operationId: getBtcVipSignal
      summary: Get verified Bitstamp BTCUSD multi-timeframe analysis
      responses:
        '200':
          description: Fresh BTCUSD indicators and conservative signal
        '503':
          description: Source unavailable or stale
""",mimetype="text/yaml")
