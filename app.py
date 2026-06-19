"""
BikeSharingInsight - 共享单车使用模式交互式数据可视化分析平台
基于Streamlit框架构建，地图使用高德地图
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import folium
from streamlit_folium import st_folium, folium_static
from baidu_utils import wgs84_to_gcj02
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="BikeSharingInsight",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown('''
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.2rem;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 10px;
    }
</style>
''', unsafe_allow_html=True)


# ============================================================
# 数据生成（自动生成测试数据，无需外部文件）
# ============================================================
def _generate_sample_data():
    """内置数据生成：上海共享单车30站点/10万条记录"""
    from datetime import datetime, timedelta

    stations = [
        ('人民广场站',31.2304,121.4737),('南京东路站',31.2381,121.4843),
        ('陆家嘴站',31.2357,121.5002),('徐家汇站',31.1947,121.4345),
        ('静安寺站',31.2256,121.4446),('中山公园站',31.2196,121.4123),
        ('五角场站',31.3020,121.5142),('世纪大道站',31.2317,121.5202),
        ('上海火车站',31.2502,121.4583),('虹桥火车站',31.1882,121.3265),
        ('新天地站',31.2192,121.4734),('豫园站',31.2275,121.4903),
        ('打浦桥站',31.2073,121.4675),('漕河泾站',31.1706,121.3962),
        ('张江高科站',31.2061,121.5910),('金桥站',31.2597,121.5914),
        ('龙阳路站',31.2037,121.5561),('上海南站',31.1544,121.4305),
        ('七宝站',31.1556,121.3510),('莘庄站',31.1093,121.3802),
        ('浦东大道站',31.2394,121.5263),('外高桥站',31.3491,121.5888),
        ('四川北路站',31.2523,121.4836),('大华站',31.2680,121.4121),
        ('长寿路站',31.2405,121.4353),('江苏路站',31.2207,121.4326),
        ('金沙江路站',31.2321,121.4138),('龙华站',31.1737,121.4527),
        ('上海体育馆站',31.1829,121.4390),('虹口足球场站',31.2713,121.4754),
    ]
    names=[s[0] for s in stations]
    lats=[s[1] for s in stations]
    lngs=[s[2] for s in stations]
    ns=len(stations)

    np.random.seed(42)
    n=100000
    start_dates,end_dates=[],[]
    for i in range(n):
        d=datetime(2024,1,1)+timedelta(days=np.random.randint(0,365))
        w=d.weekday()>=5
        pw=np.array([0.005,0.003,0.002,0.002,0.003,0.008,0.02,0.04,0.06,0.08,0.09,0.10,0.11,0.12,0.11,0.09,0.07,0.05,0.04,0.03,0.02,0.01,0.008,0.006])
        pn=np.array([0.003,0.002,0.002,0.003,0.005,0.02,0.07,0.12,0.08,0.04,0.03,0.04,0.05,0.04,0.03,0.04,0.08,0.12,0.07,0.04,0.03,0.02,0.01,0.005])
        h=np.random.choice(range(24),p=(pw if w else pn)/(pw if w else pn).sum())
        start_dt=d.replace(hour=h,minute=np.random.randint(0,60))
        ut='member' if np.random.random()<0.62 else 'casual'
        dur=float(np.clip(np.random.lognormal(2.3,0.7) if ut=='member' else np.random.lognormal(2.9,0.9),1,720))
        start_dates.append(start_dt)
        end_dates.append(start_dt+timedelta(minutes=dur))

    si=np.random.randint(0,ns,n)
    ei=np.random.randint(0,ns,n)
    ei[si==ei]=(ei[si==ei]+np.random.randint(1,ns,(si==ei).sum()))%ns

    df=pd.DataFrame({
        'ride_id':[f'RIDE_{i:07d}' for i in range(n)],
        'rideable_type':np.random.choice(['electric_bike','classic_bike'],n,p=[0.55,0.45]),
        'started_at':start_dates,'ended_at':end_dates,
        'start_station_name':[names[i] for i in si],
        'start_station_id':[f'S{i:03d}' for i in si],
        'end_station_name':[names[i] for i in ei],
        'end_station_id':[f'S{i:03d}' for i in ei],
        'start_lat':[lats[i]+np.random.normal(0,0.0001) for i in si],
        'start_lng':[lngs[i]+np.random.normal(0,0.0001) for i in si],
        'end_lat':[lats[i]+np.random.normal(0,0.0001) for i in ei],
        'end_lng':[lngs[i]+np.random.normal(0,0.0001) for i in ei],
        'member_casual':np.where(np.random.random(n)<0.62,'member','casual'),
    })
    df['started_at']=pd.to_datetime(df['started_at'])
    df['ended_at']=pd.to_datetime(df['ended_at'])
    df['trip_duration_min']=(df['ended_at']-df['started_at']).dt.total_seconds()/60
    df['start_hour']=df['started_at'].dt.hour
    df['start_dayofweek']=df['started_at'].dt.dayofweek
    df['start_month']=df['started_at'].dt.month
    dn={0:'周一',1:'周二',2:'周三',3:'周四',4:'周五',5:'周六',6:'周日'}
    df['start_dayname']=df['start_dayofweek'].map(dn)
    df['is_workday']=df['start_dayofweek'].isin([0,1,2,3,4]).astype(int)
    df['season']=df['start_month'].apply(lambda m:'春季' if m in[3,4,5] else '夏季' if m in[6,7,8] else '秋季' if m in[9,10,11] else '冬季')
    def hv(lat1,lon1,lat2,lon2):
        R=6371;lat1,lon1,lat2,lon2=map(np.radians,[lat1,lon1,lat2,lon2])
        return R*2*np.arcsin(np.sqrt(np.sin((lat2-lat1)/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2))
    df['trip_distance_km']=df.apply(lambda r:hv(r['start_lat'],r['start_lng'],r['end_lat'],r['end_lng']),axis=1)
    df['is_member']=(df['member_casual']=='member').astype(int)
    df['user_type']=df['member_casual'].map({'member':'会员','casual':'临时用户'})
    df['time_period']=df['start_hour'].apply(lambda h:'早高峰' if 6<=h<10 else '白天平峰' if 10<=h<16 else '晚高峰' if 16<=h<20 else '夜间')
    return df


# ============================================================
# 数据加载与缓存
# ============================================================
@st.cache_data(ttl=3600)
def load_data():
    """加载数据：优先读取文件，不存在则自动生成"""
    import os
    data_path = './data/processed_citibike_2024.csv'
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df['started_at'] = pd.to_datetime(df['started_at'])
        df['ended_at'] = pd.to_datetime(df['ended_at'])
    else:
        df = _generate_sample_data()
    return df


@st.cache_data
def load_station_stats(df):
    """预计算站点级别统计"""
    station_stats = df.groupby('start_station_name').agg(
        trip_count=('ride_id', 'count'),
        avg_duration=('trip_duration_min', 'mean'),
        member_ratio=('is_member', 'mean'),
        start_lat=('start_lat', 'mean'),
        start_lng=('start_lng', 'mean'),
    ).reset_index()
    station_stats['member_ratio_pct'] = (
        station_stats['member_ratio'] * 100
    ).round(1)
    return station_stats


@st.cache_data
def load_hourly_data(df):
    """预计算按小时聚合数据"""
    hourly = df.groupby(
        ['start_hour', 'user_type']
    ).size().reset_index(name='count')
    return hourly


# ============================================================
# 数据加载
# ============================================================
try:
    df = load_data()
    station_stats = load_station_stats(df)
    hourly_data = load_hourly_data(df)
    data_loaded = True
except Exception as e:
    st.error(f"数据加载失败: {e}")
    st.info("请先运行 data_preprocessing.py 生成预处理数据文件")
    data_loaded = False


# ============================================================
# 侧边栏 - 全局筛选器
# ============================================================
if data_loaded:
    st.sidebar.title("🚲 BikeSharingInsight")
    st.sidebar.markdown("---")

    # 日期范围筛选
    min_date = df['started_at'].min().date()
    max_date = df['started_at'].max().date()

    date_range = st.sidebar.date_input(
        "选择时间范围",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = ((df['started_at'].dt.date >= start_date) &
                (df['started_at'].dt.date <= end_date))
        filtered_df = df[mask]
    else:
        filtered_df = df

    # 用户类型筛选
    user_types = st.sidebar.multiselect(
        "选择用户类型",
        options=['会员', '临时用户'],
        default=['会员', '临时用户']
    )
    if user_types:
        filtered_df = filtered_df[filtered_df['user_type'].isin(user_types)]

    st.sidebar.markdown(f"当前筛选记录: **{len(filtered_df):,}** 条")

    # 分析模块选择
    st.sidebar.markdown("---")
    module = st.sidebar.radio(
        "选择分析模块",
        ["📊 数据概览", "⏰ 时间分析",
         "🗺️ 空间分析", "👤 用户分析", "🔬 聚类分析"]
    )


# ============================================================
# 主内容区
# ============================================================
st.markdown(
    '<p class="main-header">🚲 共享单车使用模式分析平台</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p class="sub-header">BikeSharingInsight — '
    '基于Citi Bike数据的交互式可视化分析</p>',
    unsafe_allow_html=True
)

if not data_loaded:
    st.stop()


# ============================================================
# 模块1: 数据概览
# ============================================================
if module == "📊 数据概览":
    st.header("📊 数据概览")

    # KPI指标卡片
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总骑行次数", f"{len(filtered_df):,}")
    with col2:
        st.metric(
            "站点数量",
            f"{filtered_df['start_station_name'].nunique():,}"
        )
    with col3:
        st.metric(
            "平均时长(分钟)",
            f"{filtered_df['trip_duration_min'].mean():.1f}"
        )
    with col4:
        st.metric(
            "会员占比",
            f"{filtered_df['is_member'].mean():.1%}"
        )
    with col5:
        st.metric(
            "平均距离(km)",
            f"{filtered_df['trip_distance_km'].mean():.2f}"
        )

    st.markdown("---")

    # 数据预览
    st.subheader("数据预览")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.dataframe(
            filtered_df[[
                'started_at', 'start_station_name',
                'end_station_name', 'trip_duration_min',
                'trip_distance_km', 'user_type'
            ]].head(20),
            use_container_width=True,
            height=400
        )
    with col_b:
        st.markdown("**数据维度**")
        st.write(f"行数: {len(filtered_df):,}")
        st.write(f"列数: {filtered_df.shape[1]}")
        st.markdown("**关键统计**")
        med = filtered_df['trip_duration_min'].median()
        st.write(f"时长中位数: {med:.1f}分钟")
        q75 = filtered_df['trip_duration_min'].quantile(0.75)
        st.write(f"时长75分位: {q75:.1f}分钟")

    # 用户类型饼图
    st.subheader("用户类型分布")
    fig_pie = px.pie(
        filtered_df, names='user_type',
        color='user_type',
        color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
        hole=0.4
    )
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)


# ============================================================
# 模块2: 时间分析
# ============================================================
elif module == "⏰ 时间分析":
    st.header("⏰ 骑行时间分析")

    time_granularity = st.radio(
        "选择时间粒度",
        ["按小时", "按星期", "按月份"],
        horizontal=True
    )

    if time_granularity == "按小时":
        st.subheader("24小时骑行量分布")

        workday_filter = st.checkbox("仅显示工作日", value=False)

        if workday_filter:
            plot_df = filtered_df[filtered_df['is_workday'] == 1]
        else:
            plot_df = filtered_df

        hourly = plot_df.groupby(
            ['start_hour', 'user_type']
        ).size().reset_index(name='count')

        fig = px.line(
            hourly, x='start_hour', y='count', color='user_type',
            color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
            markers=True,
            labels={
                'start_hour': '小时',
                'count': '骑行次数',
                'user_type': '用户类型'
            }
        )
        fig.update_layout(height=450, hovermode='x unified')
        fig.update_xaxes(tickmode='linear', tick0=0, dtick=1)
        st.plotly_chart(fig, use_container_width=True)

    elif time_granularity == "按星期":
        st.subheader("每日骑行量分布")

        daily = filtered_df.groupby(
            ['start_dayofweek', 'start_dayname']
        ).size().reset_index(name='count')
        day_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        daily['start_dayname'] = pd.Categorical(
            daily['start_dayname'],
            categories=day_order,
            ordered=True
        )
        daily = daily.sort_values('start_dayname')

        fig = px.bar(
            daily, x='start_dayname', y='count',
            color='count', color_continuous_scale='Blues',
            text_auto='.2s',
            labels={'start_dayname': '星期', 'count': '骑行次数'}
        )
        fig.update_layout(height=400, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    elif time_granularity == "按月份":
        st.subheader("月度骑行量趋势")

        monthly = filtered_df.groupby(
            ['start_month', 'user_type']
        ).size().reset_index(name='count')

        fig = px.bar(
            monthly, x='start_month', y='count', color='user_type',
            color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
            barmode='group',
            labels={
                'start_month': '月份',
                'count': '骑行次数',
                'user_type': '用户类型'
            }
        )
        fig.update_layout(height=450)
        fig.update_xaxes(tickmode='linear', dtick=1)
        st.plotly_chart(fig, use_container_width=True)

    # 骑行时长分布
    st.markdown("---")
    st.subheader("骑行时长分布")

    fig_hist = px.histogram(
        filtered_df[filtered_df['trip_duration_min'] <= 90],
        x='trip_duration_min',
        color='user_type',
        color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
        nbins=60,
        marginal='box',
        opacity=0.7,
        labels={
            'trip_duration_min': '骑行时长(分钟)',
            'count': '频次'
        }
    )
    fig_hist.update_layout(height=450, bargap=0.05)
    st.plotly_chart(fig_hist, use_container_width=True)


# ============================================================
# 模块3: 空间分析 (高德地图)
# ============================================================
elif module == "🗺️ 空间分析":
    st.header("🗺️ 站点空间分析 (高德地图)")

    top_n = st.slider(
        "显示Top N站点",
        min_value=5, max_value=30, value=15, step=5
    )

    top_stations = station_stats.nlargest(top_n, 'trip_count').copy()

    # WGS-84 -> GCJ-02 坐标转换
    top_stations['gcj_lng'] = 0.0
    top_stations['gcj_lat'] = 0.0
    for i, row in top_stations.iterrows():
        gcj_lng, gcj_lat = wgs84_to_gcj02(row['start_lng'], row['start_lat'])
        top_stations.at[i, 'gcj_lng'] = gcj_lng
        top_stations.at[i, 'gcj_lat'] = gcj_lat

    st.subheader(f"上海共享单车 Top {top_n} 站点分布")

    # 用高德地图瓦片创建 folium 地图
    center_lat = top_stations['gcj_lat'].mean()
    center_lng = top_stations['gcj_lng'].mean()

    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=12,
        tiles=None,
        width='100%',
        height=550
    )

    # 高德地图瓦片层（国内访问稳定，无需API Key）
    amap_tile_url = (
        'https://webrd0{s}.is.autonavi.com/appmaptile'
        '?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}'
    )
    folium.TileLayer(
        tiles=amap_tile_url,
        attr='高德地图',
        name='高德地图',
        subdomains='1234',
        overlay=False,
        control=True
    ).add_to(m)

    # 添加站点标记（使用GCJ-02坐标）
    max_count = top_stations['trip_count'].max()
    for _, row in top_stations.iterrows():
        radius = max(5, int(20 * row['trip_count'] / max_count))
        popup_text = (
            f"<b>{row['start_station_name']}</b><br>"
            f"骑行次数: {row['trip_count']:,}<br>"
            f"平均时长: {row['avg_duration']:.1f} 分钟<br>"
            f"会员占比: {row['member_ratio_pct']:.1f}%"
        )
        folium.CircleMarker(
            location=[row['gcj_lat'], row['gcj_lng']],
            radius=radius,
            popup=folium.Popup(popup_text, max_width=250),
            color='#2196F3',
            fill=True,
            fill_color='#2196F3',
            fill_opacity=0.6,
            weight=1
        ).add_to(m)

    # 热力图层
    heat_data = [
        [row['gcj_lat'], row['gcj_lng'], row['trip_count']]
        for _, row in top_stations.iterrows()
    ]
    from folium.plugins import HeatMap
    HeatMap(
        heat_data,
        radius=25,
        blur=15,
        max_zoom=13,
        gradient={0.2: '#2196F3', 0.5: '#4CAF50', 0.8: '#FF9800', 1.0: '#F44336'}
    ).add_to(m)

    folium.LayerControl().add_to(m)

    # 在Streamlit中显示
    st_folium(m, width=None, height=550, returned_objects=[])

    # 站点排行表
    st.markdown("---")
    st.subheader("站点骑行量排行")
    display_df = top_stations[['start_station_name', 'trip_count',
                               'avg_duration', 'member_ratio_pct']].copy()
    display_df.columns = ['站点名称', '骑行次数', '平均时长(分钟)', '会员占比(%)']
    display_df = display_df.sort_values('骑行次数', ascending=False)
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )


# ============================================================
# 模块4: 用户分析
# ============================================================
elif module == "👤 用户分析":
    st.header("👤 用户行为分析")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("用户类型占比")
        user_counts = filtered_df['user_type'].value_counts()
        fig_pie = px.pie(
            values=user_counts.values,
            names=user_counts.index,
            color=user_counts.index,
            color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
            hole=0.5
        )
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("各用户类型平均骑行时长")
        avg_dur = filtered_df.groupby('user_type')[
            'trip_duration_min'
        ].mean()
        fig_bar = px.bar(
            x=avg_dur.index, y=avg_dur.values,
            color=avg_dur.index,
            color_discrete_map={'会员': '#2196F3', '临时用户': '#FF9800'},
            text_auto='.1f',
            labels={'x': '用户类型', 'y': '平均骑行时长(分钟)'}
        )
        fig_bar.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # 骑行类型对比
    st.markdown("---")
    st.subheader("骑行类型选择对比")

    bike_type = filtered_df.groupby(
        ['user_type', 'rideable_type']
    ).size().reset_index(name='count')
    fig_bike = px.bar(
        bike_type, x='user_type', y='count', color='rideable_type',
        barmode='group',
        labels={
            'user_type': '用户类型',
            'count': '骑行次数',
            'rideable_type': '车辆类型'
        }
    )
    fig_bike.update_layout(height=400)
    st.plotly_chart(fig_bike, use_container_width=True)

    # 时段偏好热力图
    st.markdown("---")
    st.subheader("用户类型 x 时段 骑行热力图")

    heatmap_data = filtered_df.pivot_table(
        index='user_type',
        columns='time_period',
        values='ride_id',
        aggfunc='count',
        fill_value=0
    )
    heatmap_data = heatmap_data.div(
        heatmap_data.sum(axis=1), axis=0
    ) * 100

    fig_heat = px.imshow(
        heatmap_data,
        text_auto='.1f',
        aspect='auto',
        color_continuous_scale='Blues',
        labels={
            'x': '时段', 'y': '用户类型',
            'color': '占比(%)'
        }
    )
    fig_heat.update_layout(height=300)
    st.plotly_chart(fig_heat, use_container_width=True)


# ============================================================
# 模块5: 聚类分析
# ============================================================
elif module == "🔬 聚类分析":
    st.header("🔬 K-Means用户聚类分析")

    st.markdown("""
    基于站点级别的骑行行为特征(骑行频次、平均时长、高峰时段比例、周末比例)，
    使用K-Means算法对站点进行分类，揭示不同站点的使用模式。
    """)

    # 计算站点特征
    station_features = filtered_df.groupby('start_station_name').agg(
        trip_count=('ride_id', 'count'),
        avg_duration=('trip_duration_min', 'mean'),
        peak_ratio=('time_period', lambda x:
                    x.isin(['早高峰', '晚高峰']).mean()),
        weekend_ratio=('is_workday', lambda x: (x == 0).mean())
    ).dropna()

    min_trips = st.slider("最小骑行次数筛选", 100, 5000, 500, 100)
    station_features = station_features[
        station_features['trip_count'] >= min_trips
    ]

    st.write(f"参与聚类的站点数: {len(station_features)}")

    # K-Means聚类
    feature_cols = [
        'trip_count', 'avg_duration',
        'peak_ratio', 'weekend_ratio'
    ]
    X = station_features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    k = st.slider("选择聚类数K", 2, 6, 3, 1)

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    station_features['cluster'] = labels

    # 聚类散点图
    st.subheader("聚类结果可视化")
    col_a, col_b = st.columns(2)

    with col_a:
        fig_scatter = px.scatter(
            station_features,
            x='trip_count',
            y='avg_duration',
            color='cluster',
            size='trip_count',
            hover_name=station_features.index,
            labels={
                'trip_count': '骑行次数',
                'avg_duration': '平均时长(分钟)',
                'cluster': '聚类'
            },
            color_continuous_scale='Viridis'
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_b:
        fig_box = px.box(
            station_features,
            x='cluster',
            y='peak_ratio',
            color='cluster',
            labels={'cluster': '聚类', 'peak_ratio': '高峰时段比例'}
        )
        fig_box.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    # 聚类特征统计
    st.markdown("---")
    st.subheader("各聚类群体特征统计")

    cluster_stats = station_features.groupby('cluster').agg(
        站点数=('trip_count', 'count'),
        平均骑行次数=('trip_count', 'mean'),
        平均骑行时长=('avg_duration', 'mean'),
        高峰比例=('peak_ratio', 'mean'),
        周末比例=('weekend_ratio', 'mean')
    ).round(2)

    st.dataframe(cluster_stats, use_container_width=True)

    # 雷达图对比
    st.markdown("---")
    st.subheader("聚类特征雷达图")

    radar_data = cluster_stats[
        ['平均骑行次数', '平均骑行时长', '高峰比例', '周末比例']
    ]
    radar_normalized = (radar_data - radar_data.min()) / \
                       (radar_data.max() - radar_data.min())

    categories = list(radar_normalized.columns)
    fig_radar = go.Figure()

    colors = ['#2196F3', '#FF9800', '#4CAF50',
              '#E91E63', '#9C27B0', '#00BCD4']
    for i, (idx, row) in enumerate(radar_normalized.iterrows()):
        fig_radar.add_trace(go.Scatterpolar(
            r=row.values.tolist() + [row.values[0]],
            theta=categories + [categories[0]],
            name=f'聚类{idx} (n={cluster_stats.loc[idx, "站点数"]})',
            fill='toself',
            opacity=0.3,
            line=dict(color=colors[i % len(colors)])
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(range=[0, 1])),
        height=500
    )
    st.plotly_chart(fig_radar, use_container_width=True)


# ============================================================
# 页脚
# ============================================================
st.markdown("---")
st.markdown(
    "📊 **BikeSharingInsight** | 数据来源: Citi Bike NYC | "
    "开发框架: Streamlit + Plotly | (c) 2024",
    help="共享单车使用模式与城市出行特征分析课程项目"
)
