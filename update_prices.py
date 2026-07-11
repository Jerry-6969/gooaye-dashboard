#!/usr/bin/env python3
"""自動更新 index.html 內 RAW_DATA 的股價（Yahoo Finance）。由 GitHub Actions 排程執行。"""
import re, json, urllib.request, datetime, time, sys

PATH = "index.html"
YEAR = datetime.datetime.utcnow().year


def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=60d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            res = d["chart"]["result"][0]
            ts = res["timestamp"]
            cl = res["indicators"]["quote"][0]["close"]
            pairs = [(t, c) for t, c in zip(ts, cl) if c is not None]
            if len(pairs) < 2:
                return None, None
            cur = pairs[-1][1]
            last_ts = pairs[-1][0]
            p5 = pairs[max(0, len(pairs) - 6)][1]
            p22 = pairs[max(0, len(pairs) - 23)][1]
            ytd_ref = None
            for t, c in pairs:
                dt = datetime.datetime.utcfromtimestamp(t)
                if dt.year == YEAR and dt.month == 1:
                    ytd_ref = c
                    break
            if ytd_ref is None:
                ytd_ref = pairs[0][1]
            is_tw = ".TW" in sym
            price = f"NT${int(round(cur))}" if is_tw else f"${cur:.2f}"
            return {
                "price": price,
                "p7": round((cur / p5 - 1) * 100, 2),
                "p30": round((cur / p22 - 1) * 100, 2),
                "pYTD": round((cur / ytd_ref - 1) * 100, 2),
            }, last_ts
        except Exception:
            time.sleep(2)
    return None, None


html = open(PATH, encoding="utf-8").read()
m = re.search(r"const RAW_DATA = (\[.*?\]);", html, re.DOTALL)
if not m:
    sys.exit("RAW_DATA not found")
data = json.loads(m.group(1))

latest_tw_ts = 0
ok = 0
for item in data:
    pd, ts = fetch(item["yfSymbol"])
    if pd:
        item["pd"] = pd
        ok += 1
        if ".TW" in item["yfSymbol"] and ts and ts > latest_tw_ts:
            latest_tw_ts = ts
    time.sleep(0.4)

print(f"updated {ok}/{len(data)}")
if ok < len(data) * 0.8:
    sys.exit("too many fetch failures; aborting without write")

html = (
    html[: m.start()]
    + "const RAW_DATA = "
    + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    + ";"
    + html[m.end():]
)
if latest_tw_ts:
    dstr = (datetime.datetime.utcfromtimestamp(latest_tw_ts) + datetime.timedelta(hours=8)).strftime("%Y/%m/%d")
    html = re.sub(r"更新：\d{4}/\d{2}/\d{2} 收盤價", f"更新：{dstr} 收盤價", html)

open(PATH, "w", encoding="utf-8").write(html)
print("written")
