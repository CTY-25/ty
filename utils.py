"""
工具函数模块
"""
import pandas as pd
import numpy as np
from datetime import datetime


def format_number(num):
    """格式化大数字显示"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))


def get_date_range_summary(df, date_col='started_at'):
    """获取日期范围摘要"""
    start = df[date_col].min()
    end = df[date_col].max()
    days = (end - start).days
    return {
        'start': start.strftime('%Y-%m-%d'),
        'end': end.strftime('%Y-%m-%d'),
        'days': days,
        'months': round(days / 30, 1)
    }


def calculate_growth_rate(current, previous):
    """计算环比增长率"""
    if previous == 0:
        return float('inf') if current > 0 else 0
    return (current - previous) / previous * 100


def resample_time_series(df, freq='D'):
    """
    时间序列重采样
    参数:
        df: 包含started_at列的DataFrame
        freq: 重采样频率 ('H'=小时, 'D'=天, 'W'=周, 'M'=月)
    返回:
        重采样后的Series
    """
    return df.set_index('started_at').resample(freq).size()


def detect_anomalies(series, threshold=2.0):
    """
    基于Z-score的异常检测
    参数:
        series: 数据序列
        threshold: Z-score阈值
    返回:
        异常值掩码
    """
    z_scores = np.abs((series - series.mean()) / series.std())
    return z_scores > threshold


def export_summary_report(df, output_path='./summary_report.txt'):
    """导出数据摘要报告"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("共享单车数据摘要报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"总骑行次数: {len(df):,}\n")
        start = df['started_at'].min()
        end = df['started_at'].max()
        f.write(f"数据时间跨度: {start} 至 {end}\n")
        f.write(f"站点总数: {df['start_station_name'].nunique()}\n")
        f.write(f"\n--- 骑行时长统计 ---\n")
        f.write(df['trip_duration_min'].describe().to_string())
        f.write(f"\n\n--- 用户类型分布 ---\n")
        f.write(df['user_type'].value_counts().to_string())
        f.write("\n\n报告生成完毕。\n")

    print(f"摘要报告已保存至: {output_path}")
