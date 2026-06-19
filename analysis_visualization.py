"""
数据分析和静态可视化模块
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")


def descriptive_stats(df):
    """
    描述性统计分析
    """
    print("\n========== 描述性统计分析 ==========")

    # 整体统计
    print(f"总记录数: {len(df):,}")
    print(f"时间范围: {df['started_at'].min()} 至 {df['started_at'].max()}")
    print(f"站点数: {df['start_station_name'].nunique()}")
    print(f"\n骑行时长统计 (分钟):")
    print(df['trip_duration_min'].describe())
    print(f"\n骑行距离统计 (公里):")
    print(df['trip_distance_km'].describe())

    # 按用户类型分组统计
    print("\n--- 按用户类型分组统计 ---")
    for utype in ['会员', '临时用户']:
        subset = df[df['user_type'] == utype]
        print(f"\n{utype}:")
        print(f"  记录数: {len(subset):,}")
        print(f"  平均时长: {subset['trip_duration_min'].mean():.1f} 分钟")
        print(f"  中位时长: {subset['trip_duration_min'].median():.1f} 分钟")
        print(f"  平均距离: {subset['trip_distance_km'].mean():.2f} km")


def plot_hourly_pattern(df, save_path='./figures/hourly_pattern.png'):
    """
    绘制24小时骑行量分布图
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 工作日
    workday = df[df['is_workday'] == 1]
    hourly_workday = workday.groupby('start_hour').size()
    axes[0].plot(hourly_workday.index, hourly_workday.values,
                 'o-', color='#2196F3', linewidth=2, markersize=5)
    axes[0].fill_between(hourly_workday.index, 0, hourly_workday.values,
                         alpha=0.2, color='#2196F3')
    axes[0].set_title('工作日骑行量24小时分布', fontsize=14)
    axes[0].set_xlabel('小时')
    axes[0].set_ylabel('骑行次数')
    axes[0].axvspan(7, 9, alpha=0.1, color='orange', label='早高峰')
    axes[0].axvspan(17, 19, alpha=0.1, color='red', label='晚高峰')
    axes[0].legend()

    # 周末
    weekend = df[df['is_workday'] == 0]
    hourly_weekend = weekend.groupby('start_hour').size()
    axes[1].plot(hourly_weekend.index, hourly_weekend.values,
                 's-', color='#4CAF50', linewidth=2, markersize=5)
    axes[1].fill_between(hourly_weekend.index, 0, hourly_weekend.values,
                         alpha=0.2, color='#4CAF50')
    axes[1].set_title('周末骑行量24小时分布', fontsize=14)
    axes[1].set_xlabel('小时')
    axes[1].set_ylabel('骑行次数')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图已保存: {save_path}")
    return fig


def plot_monthly_trend(df, save_path='./figures/monthly_trend.png'):
    """
    绘制月度骑行量趋势图
    """
    monthly = df.groupby('start_month').size()

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#90CAF9' if m in [12, 1, 2]
              else '#81C784' if m in [3, 4, 5]
              else '#FFB74D' if m in [6, 7, 8]
              else '#E57373'
              for m in monthly.index]
    bars = ax.bar(monthly.index, monthly.values, color=colors, edgecolor='white')

    for bar, val in zip(bars, monthly.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5000,
                f'{val:,}', ha='center', va='bottom', fontsize=9)

    ax.set_title('2024年各月份骑行量变化趋势', fontsize=14)
    ax.set_xlabel('月份')
    ax.set_ylabel('骑行次数')
    ax.set_xticks(range(1, 13))
    month_labels = ['1月', '2月', '3月', '4月', '5月', '6月',
                    '7月', '8月', '9月', '10月', '11月', '12月']
    ax.set_xticklabels(month_labels)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#90CAF9', label='冬季'),
        Patch(facecolor='#81C784', label='春季'),
        Patch(facecolor='#FFB74D', label='夏季'),
        Patch(facecolor='#E57373', label='秋季')
    ]
    ax.legend(handles=legend_elements, loc='upper left')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_duration_distribution(df, save_path='./figures/duration_dist.png'):
    """
    绘制骑行时长分布直方图
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    member_data = df[df['is_member'] == 1]['trip_duration_min']
    casual_data = df[df['is_member'] == 0]['trip_duration_min']

    ax.hist(member_data.clip(upper=60), bins=60, alpha=0.6,
            color='#2196F3', label='会员', density=True)
    ax.hist(casual_data.clip(upper=60), bins=60, alpha=0.6,
            color='#FF9800', label='临时用户', density=True)

    ax.set_title('骑行时长分布（会员 vs 临时用户）', fontsize=14)
    ax.set_xlabel('骑行时长（分钟）')
    ax.set_ylabel('密度')
    ax.legend()
    ax.axvline(x=df['trip_duration_min'].median(), color='red',
               linestyle='--', linewidth=1.5, label='整体中位数')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def plot_station_top10(df, save_path='./figures/station_top10.png'):
    """
    绘制Top10站点使用频率柱状图
    """
    station_counts = df['start_station_name'].value_counts().head(10)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, 10))
    bars = ax.barh(range(10), station_counts.values[::-1], color=colors[::-1])

    ax.set_yticks(range(10))
    ax.set_yticklabels([s[:35] for s in station_counts.index[::-1]], fontsize=9)
    ax.set_xlabel('骑行次数')
    ax.set_title('骑行出发量Top 10站点', fontsize=14)
    for bar, val in zip(bars, station_counts.values[::-1]):
        ax.text(bar.get_width() + 1000, bar.get_y() + bar.get_height()/2,
                f'{val:,}', va='center', fontsize=9)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    return fig


def user_clustering(df, n_clusters=3):
    """
    用户行为聚类分析
    """
    print("\n========== K-Means用户聚类 ==========")

    # 构建用户级特征
    user_features = df.groupby('start_station_name').agg(
        trip_count=('ride_id', 'count'),
        avg_duration=('trip_duration_min', 'mean'),
        peak_ratio=('is_workday', lambda x: (
            df.loc[x.index, 'time_period'].isin(['早高峰', '晚高峰']).sum()
            / len(x)
        )),
        weekend_ratio=('is_workday', lambda x: (x == 0).mean())
    ).dropna()

    # 标准化
    feature_cols = ['trip_count', 'avg_duration', 'peak_ratio', 'weekend_ratio']
    X = user_features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 肘部法则
    sse = []
    for k in range(1, 11):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        sse.append(kmeans.inertia_)

    # 最佳K值聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    silhouette = silhouette_score(X_scaled, labels)

    print(f"最佳聚类数 K={n_clusters}")
    print(f"轮廓系数: {silhouette:.3f}")
    for i in range(n_clusters):
        mask = labels == i
        print(f"\n群体{i+1} (样本数: {mask.sum()}):")
        print(f"  平均骑行次数: {X[mask, 0].mean():.0f}")
        print(f"  平均骑行时长: {X[mask, 1].mean():.1f} 分钟")
        print(f"  高峰比例: {X[mask, 2].mean():.2%}")
        print(f"  周末比例: {X[mask, 3].mean():.2%}")

    return user_features, labels, sse, silhouette


if __name__ == '__main__':
    df = pd.read_csv('./data/processed_citibike_2024.csv')
    df['started_at'] = pd.to_datetime(df['started_at'])
    descriptive_stats(df)
    plot_hourly_pattern(df)
    plot_monthly_trend(df)
    plot_duration_distribution(df)
    plot_station_top10(df)
    user_clustering(df)
