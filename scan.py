import tushare as ts
import requests
import os
import time

def run_scan():
    token = os.getenv("TUSHARE_TOKEN")
    stock_str = os.getenv("STOCK_LIST", "")
    webhook = os.getenv("FEISHU_WEBHOOK_URL")

    if not token:
        print("未配置 TUSHARE_TOKEN")
        return

    ts.set_token(token)
    pro = ts.pro_api()

    codes = [c.strip() for c in stock_str.split(",") if c.strip()]
    if not webhook:
        print("未配置 FEISHU_WEBHOOK_URL")
        return

    for code in codes:
        try:
            time.sleep(0.3)  # 温和限速，防超限

            # ts_code 格式：000903.SZ / 600038.SH
            ts_code = code + (".SZ" if code.startswith(("0", "3")) else ".SH")

            df = pro.daily(
                ts_code=ts_code,
                start_date="20240101",
                end_date="20990101"
            )
            if df is None or df.empty:
                continue

            last = df.iloc[0]  # pro.daily 默认按日期倒序
            chg = float(last.get("pct_chg", 0))
            vol = float(last.get("vol", 0))
            amount = float(last.get("amount", 0))

            # 简易异动：涨幅>2% 且成交额>5000万（你可改）
            if chg > 2 and amount > 50000000:
                msg = {
                    "msg_type": "text",
                    "content": {
                        "text": f"📈 异动扫描触发\n代码：{code}\n涨幅：{chg:.2f}%\n成交额：{amount/1e4:.0f}万"
                    }
                }
                r = requests.post(webhook, json=msg, timeout=10)
                print(f"{code} 推送 -> {r.status_code}")
        except Exception as e:
            print(f"{code} 异常: {e}")

if __name__ == "__main__":
    run_scan()

requests.post(
    webhook,
    json={"msg_type": "text", "content": {"text": "✅ 扫描完成，今日无符合异动条件个股"}},
    timeout=10
)
print("发送心跳消息完毕")
