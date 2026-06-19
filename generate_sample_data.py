"""
生成测试用共享单车数据（约10万条），用于截图演示
运行: python generate_sample_data.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

Path('./data').mkdir(exist_ok=True)
Path('./figures').mkdir(exist_ok=True)

np.random.seed(42)

n = 100_000  # 10万条记录

# 纽约市真实站点（缩小版）
stations = [
    ("W 21 St & 6 Ave", 40.7417, -73.9922),
    ("Broadway & W 58 St", 40.7669, -73.9824),
    ("8 Ave & W 31 St", 40.7505, -73.9942),
    ("Lafayette St & E 8 St", 40.7287, -73.9920),
    ("E 17 St & Broadway", 40.7373, -73.9904),
    ("W 41 St & 8 Ave", 40.7566, -73.9903),
    ("University Pl & E 14 St", 40.7347, -73.9920),
    ("E 47 St & Park Ave", 40.7546, -73.9745),
    ("W 45 St & 6 Ave", 40.7571, -73.9836),
    ("E 72 St & 2 Ave", 40.7683, -73.9587),
    ("Carmine St & 6 Ave", 40.7305, -74.0010),
    ("E 10 St & Avenue A", 40.7267, -73.9808),
    ("Riverside Dr & W 72 St", 40.7858, -73.9840),
    ("W 106 St & Amsterdam Ave", 40.8002, -73.9640),
    ("E 86 St & Lexington Ave", 40.7802, -73.9542),
    ("Centre St & Worth St", 40.7146, -74.0026),
    ("Henry St & Atlantic Ave", 40.6901, -73.9949),
    ("Fulton St & Clermont Ave", 40.6866, -73.9704),
    ("Jay St & York St", 40.7008, -73.9872),
    ("S Portland Ave & Hanson Pl", 40.6849, -73.9748),
    ("St Marks Pl & 2 Ave", 40.7279, -73.9865),
    ("1 Ave & E 16 St", 40.7336, -73.9817),
    ("Greenwich Ave & 8 Ave", 40.7394, -74.0028),
    ("W 4 St & 7 Ave S", 40.7320, -74.0024),
    ("MacDougal St & Prince St", 40.7273, -73.9988),
    ("Mott St & Prince St", 40.7230, -73.9957),
    ("Bank St & Hudson St", 40.7370, -74.0075),
    ("Cleveland Pl & Spring St", 40.7221, -73.9965),
    ("Perry St & Bleecker St", 40.7343, -74.0056),
    ("Grand St & Havemeyer St", 40.7129, -73.9565),
]

station_names = [s[0] for s in stations]
station_lats = [s[1] for s in stations]
station_lngs = [s[2] for s in stations]
n_stations = len(stations)

# 生成时间序列（2024全年）
start_dates = []
end_dates = []

for i in range(n):
    # 随机日期
    day_offset = np.random.randint(0, 365)
    ride_date = datetime(2024, 1, 1) + timedelta(days=day_offset)

    # 工作日 vs 周末模式
    is_weekend = ride_date.weekday() >= 5
    if is_weekend:
        p_weekend = np.array([0.005,0.003,0.002,0.002,0.003,0.008,0.02,0.04,
                              0.06,0.08,0.09,0.10,0.11,0.12,0.11,0.09,
                              0.07,0.05,0.04,0.03,0.02,0.01,0.008,0.006])
        p_weekend = p_weekend / p_weekend.sum()
        hour = np.random.choice(range(24), p=p_weekend)
    else:
        p_workday = np.array([0.003,0.002,0.002,0.003,0.005,0.02,0.07,0.12,
                              0.08,0.04,0.03,0.04,0.05,0.04,0.03,0.04,
                              0.08,0.12,0.07,0.04,0.03,0.02,0.01,0.005])
        p_workday = p_workday / p_workday.sum()
        hour = np.random.choice(range(24), p=p_workday)

    minute = np.random.randint(0, 60)
    start_dt = ride_date.replace(hour=hour, minute=minute)

    # 会员vs临时用户
    user_type = np.random.choice(['member', 'casual'], p=[0.62, 0.38])

    # 骑行时长（对数正态分布）
    if user_type == 'member':
        duration = np.random.lognormal(mean=2.3, sigma=0.7)
    else:
        duration = np.random.lognormal(mean=2.9, sigma=0.9)
    duration = np.clip(duration, 1, 720)

    end_dt = start_dt + timedelta(minutes=float(duration))

    start_dates.append(start_dt)
    end_dates.append(end_dt)

# 随机分配站点
start_idx = np.random.randint(0, n_stations, n)
end_idx = np.random.randint(0, n_stations, n)

# 确保起点和终点不同
mask_same = start_idx == end_idx
end_idx[mask_same] = (end_idx[mask_same] + np.random.randint(1, n_stations, mask_same.sum())) % n_stations

df = pd.DataFrame({
    'ride_id': [f"RIDE_{i:07d}" for i in range(n)],
    'rideable_type': np.random.choice(
        ['electric_bike', 'classic_bike'], n, p=[0.55, 0.45]
    ),
    'started_at': start_dates,
    'ended_at': end_dates,
    'start_station_name': [station_names[i] for i in start_idx],
    'start_station_id': [f"S{i:03d}" for i in start_idx],
    'end_station_name': [station_names[i] for i in end_idx],
    'end_station_id': [f"S{i:03d}" for i in end_idx],
    'start_lat': [station_lats[i] + np.random.normal(0, 0.0001) for i in start_idx],
    'start_lng': [station_lngs[i] + np.random.normal(0, 0.0001) for i in start_idx],
    'end_lat': [station_lats[i] + np.random.normal(0, 0.0001) for i in end_idx],
    'end_lng': [station_lngs[i] + np.random.normal(0, 0.0001) for i in end_idx],
    'member_casual': np.where(
        np.random.random(n) < 0.62, 'member', 'casual'
    ),
})

# 保存原始数据
df.to_csv('./data/citibike_2024_raw.csv', index=False)
print(f"原始数据已保存: {len(df):,} 条记录")

# 直接生成预处理后的数据（跳过下载步骤）
# 相当于运行了 data_preprocessing.py 的结果
df['started_at'] = pd.to_datetime(df['started_at'])
df['ended_at'] = pd.to_datetime(df['ended_at'])
df['trip_duration_min'] = (df['ended_at'] - df['started_at']).dt.total_seconds() / 60
df['start_hour'] = df['started_at'].dt.hour
df['start_dayofweek'] = df['started_at'].dt.dayofweek
df['start_month'] = df['started_at'].dt.month
day_names = {0:'周一',1:'周二',2:'周三',3:'周四',4:'周五',5:'周六',6:'周日'}
df['start_dayname'] = df['start_dayofweek'].map(day_names)
df['is_workday'] = df['start_dayofweek'].isin([0,1,2,3,4]).astype(int)
def get_season(m):
    if m in [3,4,5]: return '春季'
    elif m in [6,7,8]: return '夏季'
    elif m in [9,10,11]: return '秋季'
    else: return '冬季'
df['season'] = df['start_month'].apply(get_season)

# Haversine距离
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1,lon1,lat2,lon2 = map(np.radians, [lat1,lon1,lat2,lon2])
    dlat, dlon = lat2-lat1, lon2-lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

df['trip_distance_km'] = df.apply(
    lambda r: haversine(r['start_lat'],r['start_lng'],r['end_lat'],r['end_lng']),
    axis=1
)
df['is_member'] = (df['member_casual']=='member').astype(int)
df['user_type'] = df['member_casual'].map({'member':'会员','casual':'临时用户'})
def classify(h):
    if 6<=h<10: return '早高峰'
    elif 10<=h<16: return '白天平峰'
    elif 16<=h<20: return '晚高峰'
    else: return '夜间'
df['time_period'] = df['start_hour'].apply(classify)

df.to_csv('./data/processed_citibike_2024.csv', index=False)
print(f"预处理数据已保存: {len(df):,} 条记录 (含{df.shape[1]}个字段)")
print(f"会员: {df['is_member'].sum():,} ({df['is_member'].mean():.1%})")
print(f"站点数: {df['start_station_name'].nunique()}")
print(f"时间跨度: {df['started_at'].min()} ~ {df['started_at'].max()}")
print("\n数据已就绪，可以运行: streamlit run app.py")
