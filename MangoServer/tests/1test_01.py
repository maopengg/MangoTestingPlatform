# 策略说明：如果运行时间点价格高出昨收5%, 则进入涨幅选股板块，否则清空该板块
import pandas as pd
import numpy as np
from datetime import datetime
from tqcenter import tq 

# 初始化tq
tq.initialize(__file__)

# 1. 基础配置
batch_codes = tq.get_stock_list_in_sector('通达信88')     # 目标板块
start_time = "20251025"                                  # 数据起始日期
target_end = datetime.now().strftime("%Y%m%d")           # 数据结束日期（当前日期）
target_gain = 5.0                                        # 目标涨幅（%），可修改
target_block_name = 'ZFXG'                               # 目标自定义板块简称

# 2. 获取并整理收盘价数据
df_real = tq.get_market_data(
    field_list=['Close'],
    stock_list=batch_codes,
    start_time=start_time,
    end_time=target_end,
    dividend_type='front',  # 前复权
    period='1d',            # 日线
    fill_data=True          # 填充缺失数据
)
# 转换为「日期×股票代码」的收盘价宽表
close_df = tq.price_df(df_real, 'Close', column_names=batch_codes)

# 3. 核心：计算当日相较于昨日的涨幅（%）
# 昨日收盘价（向下平移1行）
prev_close = close_df.shift(1)
# 计算涨幅：(当日收盘价 - 昨日收盘价) / 昨日收盘价 × 100%
daily_gain = (close_df - prev_close) / prev_close * 100

# 4. 筛选符合条件的股票（最新交易日涨幅超target_gain%）
latest_date = daily_gain.index[-1]              # 最新交易日
latest_daily_gain = daily_gain.loc[latest_date] # 每只股票最新交易日的涨幅
# 筛选条件：涨幅 > target_gain%（排除NaN，避免数据异常）
target_stocks = latest_daily_gain[latest_daily_gain > target_gain].sort_values(ascending=False)
target_stocks_list = target_stocks.index.tolist()  # 提取符合条件的股票代码列表

# 5. 结果输出与自定义板块操作（可按需注释）
print(f"\n=== 筛选结果（当日涨幅＞{target_gain}%）===")
if not target_stocks.empty:
    # ===================== 模块1：打印筛选结果 =====================
    print("【模块1：打印筛选结果】")
    print(f"符合条件的股票共 {len(target_stocks)} 只：")
    print(f"{'股票代码':<12} {'昨日收盘价':<12} {'当日收盘价':<12} {'当日涨幅':<10}")
    print("-" * 50)
    for stock_code, gain in target_stocks.items():
        prev_price = prev_close.loc[latest_date, stock_code]
        curr_price = close_df.loc[latest_date, stock_code]
        print(f"{stock_code:<12} {prev_price:<12.2f} {curr_price:<12.2f} {gain:<.2f}%")
    print("-" * 50)

    # ===================== 模块2：添加至自定义板块 =====================
    try:
        print("【模块2：自定义板块操作】")
        tq.send_user_block(block_code=target_block_name, stocks=target_stocks_list, show=True)
        print(f"✅ 已成功将股票添加至自定义板块「{target_block_name}」")
    except Exception as e:
        print(f"❌ 添加自定义板块失败：{e}")
    print("-" * 50)



else:
    # ===================== 模块1：打印空结果 =====================
    print("【模块1：打印筛选结果】")
    print(f"暂无当日涨幅＞{target_gain}%的股票")
    print("-" * 50)

    # ===================== 模块2：清空自定义选板块 =====================
    try:
        print("【模块2：自定义板块操作】")
        tq.send_user_block(block_code=target_block_name, stocks=[],show=True)
        print(f"✅ 已清空自定义板块「{target_block_name}」")
    except Exception as e:
        print(f"❌ 清空自定义板块失败：{e}")
    print("-" * 50)


