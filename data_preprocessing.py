"""
数据预处理模块
功能：Citi Bike数据下载、数据清洗、特征工程
"""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def download_citibike_data(year=2024, output_dir='./data'):
    """
    下载Citi Bike年度数据
    参数:
        year: 数据年份
        output_dir: 输出目录
    返回:
        full_data: 合并后的DataFrame
    """
    import requests

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    base_url = "https://s3.amazonaws.com/tripdata/"
    dataframes = []

    for month in range(1, 13):
        month_str = f"{year}{month:02d}"
        filename = f"{month_str}-citibike-tripdata.csv.zip"
        url = f"{base_url}{filename}"
        local_path = Path(output_dir) / filename

        if not local_path.exists():
            print(f"  下载: {filename} ...")
            try:
                r = requests.get(url, timeout=120)
                r.raise_for_status()
                local_path.write_bytes(r.content)
            except Exception as e:
                print(f"  下载失败 {month_str}: {e}")
                continue
        else:
            print(f"  已存在: {filename}")

        try:
            df = pd.read_csv(local_path, compression='zip', low_memory=False)
            dataframes.append(df)
            print(f"  {month_str}: {len(df):,} 条记录")
        except Exception as e:
            print(f"  读取失败 {month_str}: {e}")

    if dataframes:
        full_data = pd.concat(dataframes, ignore_index=True)
        print(f"\n合并完成: {len(full_data):,} 条总记录")
        return full_data
    else:
        raise ValueError("未获取到任何数据")


def clean_data(df):
    """
    数据清洗函数
    参数:
        df: 原始DataFrame
    返回:
        clean_df: 清洗后的DataFrame
    """
    print("\n========== 数据清洗 ==========")

    # 1. 缺失值统计
    missing = df.isnull().sum()
    print(f"各字段缺失值:\n{missing[missing > 0]}")

    # 2. 删除关键字段缺失的记录
    key_cols = [
        'start_lat', 'start_lng', 'end_lat', 'end_lng',
        'start_station_name', 'end_station_name'
    ]
    clean_df = df.dropna(subset=key_cols).copy()
    n_removed_null = len(df) - len(clean_df)
    print(f"  删除缺失关键字段记录: {n_removed_null:,} 条")

    # 3. 转换时间字段
    clean_df['started_at'] = pd.to_datetime(clean_df['started_at'])
    clean_df['ended_at'] = pd.to_datetime(clean_df['ended_at'])

    # 4. 计算骑行时长（分钟）
    clean_df['trip_duration_min'] = (
        (clean_df['ended_at'] - clean_df['started_at'])
        .dt.total_seconds() / 60
    )

    # 5. 异常值处理：保留1分钟到720分钟（12小时）之间的骑行
    mask_valid = (
        (clean_df['trip_duration_min'] >= 1) &
        (clean_df['trip_duration_min'] <= 720)
    )
    n_removed_outlier = (~mask_valid).sum()
    clean_df = clean_df[mask_valid].copy()
    print(f"  删除异常时长记录: {n_removed_outlier:,} 条")

    # 6. 坐标范围校验（纽约市）
    lat_ok = (clean_df['start_lat'].between(40.5, 41.0) &
              clean_df['end_lat'].between(40.5, 41.0))
    lng_ok = (clean_df['start_lng'].between(-74.3, -73.6) &
              clean_df['end_lng'].between(-74.3, -73.6))
    clean_df = clean_df[lat_ok & lng_ok].copy()
    print(f"  坐标范围校验后保留: {len(clean_df):,} 条")

    print(f"清洗完成: 原始{len(df):,}条 -> 清洗后{len(clean_df):,}条")
    return clean_df


def feature_engineering(df):
    """
    特征工程函数
    参数:
        df: 清洗后DataFrame
    返回:
        df: 添加新特征后的DataFrame
    """
    print("\n========== 特征工程 ==========")

    # 1. 时间特征
    df['start_hour'] = df['started_at'].dt.hour
    df['start_dayofweek'] = df['started_at'].dt.dayofweek  # 0=周一
    df['start_month'] = df['started_at'].dt.month
    df['start_day'] = df['started_at'].dt.day

    # 2. 星期名称
    day_names = {0: '周一', 1: '周二', 2: '周三', 3: '周四',
                 4: '周五', 5: '周六', 6: '周日'}
    df['start_dayname'] = df['start_dayofweek'].map(day_names)

    # 3. 是否为工作日
    df['is_workday'] = df['start_dayofweek'].isin([0, 1, 2, 3, 4]).astype(int)

    # 4. 季节
    def get_season(month):
        if month in [3, 4, 5]:
            return '春季'
        elif month in [6, 7, 8]:
            return '夏季'
        elif month in [9, 10, 11]:
            return '秋季'
        else:
            return '冬季'
    df['season'] = df['start_month'].apply(get_season)

    # 5. 骑行距离（Haversine公式，单位千米）
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
        return R * 2 * np.arcsin(np.sqrt(a))

    df['trip_distance_km'] = df.apply(
        lambda row: haversine(
            row['start_lat'], row['start_lng'],
            row['end_lat'], row['end_lng']
        ), axis=1
    )

    # 6. 用户类型标识
    df['is_member'] = (df['member_casual'] == 'member').astype(int)
    df['user_type'] = df['member_casual'].map(
        {'member': '会员', 'casual': '临时用户'}
    )

    # 7. 时段分类
    def classify_period(hour):
        if 6 <= hour < 10:
            return '早高峰'
        elif 10 <= hour < 16:
            return '白天平峰'
        elif 16 <= hour < 20:
            return '晚高峰'
        else:
            return '夜间'
    df['time_period'] = df['start_hour'].apply(classify_period)

    new_cols = [c for c in df.columns
                if c not in ['ride_id', 'rideable_type', 'started_at',
                             'ended_at', 'start_station_name',
                             'start_station_id', 'end_station_name',
                             'end_station_id', 'start_lat', 'start_lng',
                             'end_lat', 'end_lng', 'member_casual']]
    print(f"特征工程完成，数据维度: {df.shape}")
    print(f"新增字段: {new_cols}")
    return df


def preprocess_pipeline(year=2024):
    """
    完整数据预处理流水线
    返回:
        processed_df: 处理完成的DataFrame
    """
    raw = download_citibike_data(year)
    clean = clean_data(raw)
    processed = feature_engineering(clean)
    processed.to_csv('./data/processed_citibike_2024.csv', index=False)
    print("\n数据已保存至 ./data/processed_citibike_2024.csv")
    return processed


if __name__ == '__main__':
    df = preprocess_pipeline()
    print(f"\n最终数据集: {df.shape[0]:,} 行 x {df.shape[1]} 列")
