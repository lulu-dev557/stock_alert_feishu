import os
import time
import requests
import tushare as ts
import pandas as pd

# ==================== 初始化配置 ====================
# 从 GitHub Secrets 读取配置
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN')
STOCK_LIST_STR = os.environ.get('STOCK_LIST')
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK_URL')

# 基础校验
if not all([TUSHARE_TOKEN, STOCK_LIST_STR, FEISHU_WEBHOOK]):
    raise ValueError("请在 GitHub Secrets 中配置 TUSHARE_TOKEN, STOCK_LIST, FEISHU_WEBHOOK_URL")

# 初始化 Tushare
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# 解析股票列表，并清洗数据（确保是6位数字）
stock_codes = [
    code.strip() for code in STOCK_LIST_STR.split(',') 
    if code.strip().isdigit() and len(code.strip()) == 6
]

if not stock_codes:
    raise ValueError("STOCK_LIST 为空或格式不正确，请检查 Secrets 配置")

# ==================== 核心函数 ====================
def send_feishu_message(content: str):
    """
    发送消息到飞书群
    """
    payload = {
        "msg_type": "text",
        "content": {"text": content}
    }
    try:
        response = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()  # 如果状态码不是200，则抛出异常
        print("飞书消息发送成功")
    except Exception as e:
        print(f"飞书发送失败: {e}")

# ==================== 主逻辑 ====================
def main():
    print(f"开始扫描，共 {len(stock_codes)} 只股票...")
    
    # 用于存储符合条件的股票
    alert_stocks = []

    for code in stock_codes:
        try:
            # 1. 限速，防止 Tushare 限流（非常关键）
            time.sleep(0.5)
            
            # 2. 转换 Tushare 格式 (000903 -> 000903.SZ)
            ts_code = code + (".SZ" if code.startswith(("0", "3")) else ".SH")
            
            # 3. 拉取日线数据
            df = pro.daily(
                ts_code=ts_code,
                start_date="20240101",
                end_date="20990101"
            )
            
            if df is None or df.empty or len(df) < 20:
                print(f"{code} 数据不足，跳过")
                continue
                
            # 4. 计算指标
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma10'] = df['close'].rolling(10).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['vol_ma5'] = df['vol'].rolling(5).mean()
            
            # 取最新一天数据
            last = df.iloc[0]
            
            # 5. 低位异动判断条件（你可以自己改这里的阈值）
            is_low_position = last['close'] <= last['ma20'] * 1.05
            is_volume_break = last['vol'] >= last['vol_ma5'] * 1.5
            is_price_up = last['pct_chg'] > 2 and last['pct_chg'] < 6
            
            if is_low_position and is_volume_break and is_price_up:
                alert_msg = (
                    f"📈 低位异动\n"
                    f"代码: {code}\n"
                    f"涨幅: {last['pct_chg']:.2f}%\n"
                    f"收盘价: {last['close']:.2f}"
                )
                alert_stocks.append(alert_msg)
                print(f"{code} 触发异动条件")
                
        except Exception as e:
            # 单只股票报错，打印但继续执行下一个
            print(f"{code} 处理异常: {e}")
            continue
            
    # ==================== 结果推送 ====================
    if alert_stocks:
        final_content = "🔥 今日低位异动个股：\n\n" + "\n\n".join(alert_stocks)
    else:
        final_content = "✅ 今日扫描完成，未发现符合条件的低位异动个股。"
        
    send_feishu_message(final_content)
    print("脚本执行完毕")

# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
