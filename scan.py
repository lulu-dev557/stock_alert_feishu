import akshare as ak
import requests
import os

def run_scan():
    stock_str = os.getenv("STOCK_LIST", "")
    codes = [c.strip() for c in stock_str.split(",") if c.strip()]
    webhook = os.getenv("FEISHU_WEBHOOK_URL")

    if not webhook:
        print("未配置 FEISHU_WEBHOOK_URL")
        return

    for code in codes:
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date="20240101",
                end_date="20990101",
                adjust="qfq"
            )
            if df.empty or len(df) < 2:
                continue

            last = df.iloc[-1]
            prev_vol = df["成交量"].iloc[-6:-1].mean()

            chg = float(last["涨跌幅"])
            vol = float(last["成交量"])
            turn = float(last.get("换手率", 0))

            # 异动条件：涨幅>2%、换手>2%、量大于近5日均量1.2倍
            if chg > 2 and turn > 2 and vol > prev_vol * 1.2:
                msg = {
                    "msg_type": "text",
                    "content": {
                        "text": f"📈 异动扫描触发\n代码：{code}\n涨幅：{chg:.2f}%\n换手：{turn:.2f}%\n成交量放大"
                    }
                }
                r = requests.post(webhook, json=msg, timeout=10)
                print(f"{code} 推送 -> {r.status_code}")
        except Exception as e:
            print(f"{code} 异常: {e}")

if __name__ == "__main__":
    run_scan()
