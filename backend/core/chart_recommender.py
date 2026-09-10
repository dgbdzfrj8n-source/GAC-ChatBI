"""
ECharts 智能可视化推荐器 (Chart Recommender)
核心职责：
1. 分析 SQL 查询结果的列名特征、数据类型与行数；
2. 自动推断最优的可视化展现形态（折线图 line、柱状图 bar、环形饼图 pie/ring、双轴复合图 dual_axis、表格 table）；
3. 生成可以直接供给前端 Next.js ECharts 组件消费的标准化 Option JSON，具备车企商务美感与交互 Tooltip。
"""

from typing import Dict, Any, List, Optional

# 常见时间维度列识别模式
TIME_DIMENSIONS = {"sale_date", "date", "year_month", "month", "year", "quarter"}
# 常见类别维度列识别模式
CATEGORY_DIMENSIONS = {"brand_name", "model_name", "region_name", "province_name", "channel_name", "expense_category"}
# 常见比率/百分比指标识别模式
PERCENT_METRICS = {"fulfillment_rate", "rate", "fulfillment_rate_pct", "discount_rate", "conversion_rate", "roi", "cpl"}

# 车企商务配色板（埃安绿/广汽红/科技蓝等）
GAC_PALETTE = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4"]

class ChartRecommender:
    def __init__(self):
        pass

    def recommend(self, query: str, columns: List[str], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据列特征与数据模式推断图表类型，并组装完整的 ECharts Option
        """
        if not data or not columns:
            return {"chart_type": "table", "echarts_option": None}

        # 区分维度列 (String/Date) 与 指标数值列 (Number)
        dim_cols = []
        metric_cols = []

        sample_row = data[0]
        for col in columns:
            val = sample_row.get(col)
            if isinstance(val, (int, float)) and col.lower() not in TIME_DIMENSIONS:
                metric_cols.append(col)
            else:
                dim_cols.append(col)

        # 若未成功分离（例如全部是数字或全部是字符），按第一列维度、其余指标兜底
        if not dim_cols and len(columns) > 1:
            dim_cols = [columns[0]]
            metric_cols = columns[1:]
        elif not metric_cols and len(columns) > 1:
            metric_cols = [columns[-1]]
            dim_cols = columns[:-1]

        primary_dim = dim_cols[0] if dim_cols else columns[0]
        dim_lower = primary_dim.lower()

        # 1. 规则推断：多指标且包含百分比 -> 双轴图
        has_percent = any(any(pm in m.lower() for pm in PERCENT_METRICS) for m in metric_cols)
        has_volume = any(not any(pm in m.lower() for pm in PERCENT_METRICS) for m in metric_cols)
        if len(metric_cols) >= 2 and has_percent and has_volume:
            return self._build_dual_axis_chart(query, primary_dim, metric_cols, data)

        # 2. 规则推断：时间维度 -> 折线趋势图
        if any(td in dim_lower for td in TIME_DIMENSIONS):
            return self._build_line_chart(query, primary_dim, metric_cols, data)

        # 3. 规则推断：占比或渠道构成且行数 <= 6 -> 环形饼图
        if any(kw in query for kw in ["占比", "分布", "构成"]) and len(data) <= 6:
            metric_col = metric_cols[0] if metric_cols else columns[-1]
            return self._build_pie_chart(query, primary_dim, metric_col, data)

        # 4. 规则推断：常规类别对比（行数 <= 20） -> 柱状对比图
        if len(data) <= 20:
            return self._build_bar_chart(query, primary_dim, metric_cols, data)

        # 5. 兜底：行数过多或结构复杂 -> 表格
        return {"chart_type": "table", "echarts_option": None}

    def _build_line_chart(self, title: str, x_dim: str, metrics: List[str], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        x_data = [str(r.get(x_dim, "")) for r in data]
        series = []
        
        for idx, m in enumerate(metrics):
            series.append({
                "name": m,
                "type": "line",
                "smooth": True,
                "data": [r.get(m, 0) for r in data],
                "itemStyle": {"color": GAC_PALETTE[idx % len(GAC_PALETTE)]},
                "areaStyle": {
                    "opacity": 0.15
                }
            })

        option = {
            "title": {"text": title, "textStyle": {"fontSize": 14, "fontWeight": "normal", "color": "#1F2937"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"top": "bottom", "data": metrics},
            "grid": {"left": "4%", "right": "4%", "bottom": "12%", "containLabel": True},
            "xAxis": {"type": "category", "data": x_data, "axisLine": {"lineStyle": {"color": "#9CA3AF"}}},
            "yAxis": {"type": "value", "splitLine": {"lineStyle": {"type": "dashed", "color": "#E5E7EB"}}},
            "series": series
        }
        return {"chart_type": "line", "echarts_option": option}

    def _build_bar_chart(self, title: str, x_dim: str, metrics: List[str], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        x_data = [str(r.get(x_dim, "")) for r in data]
        series = []
        
        for idx, m in enumerate(metrics):
            series.append({
                "name": m,
                "type": "bar",
                "barMaxWidth": 35,
                "itemStyle": {"borderRadius": [4, 4, 0, 0], "color": GAC_PALETTE[idx % len(GAC_PALETTE)]},
                "data": [r.get(m, 0) for r in data]
            })

        option = {
            "title": {"text": title, "textStyle": {"fontSize": 14, "fontWeight": "normal", "color": "#1F2937"}},
            "tooltip": {"trigger": "axis"},
            "legend": {"top": "bottom", "data": metrics},
            "grid": {"left": "4%", "right": "4%", "bottom": "12%", "containLabel": True},
            "xAxis": {"type": "category", "data": x_data, "axisLabel": {"interval": 0, "rotate": 15 if len(x_data) > 6 else 0}},
            "yAxis": {"type": "value", "splitLine": {"lineStyle": {"type": "dashed", "color": "#E5E7EB"}}},
            "series": series
        }
        return {"chart_type": "bar", "echarts_option": option}

    def _build_pie_chart(self, title: str, name_col: str, val_col: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        pie_data = [{"name": str(r.get(name_col, "")), "value": r.get(val_col, 0)} for r in data]
        option = {
            "title": {"text": title, "textStyle": {"fontSize": 14, "fontWeight": "normal", "color": "#1F2937"}, "left": "center"},
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"top": "bottom"},
            "color": GAC_PALETTE,
            "series": [
                {
                    "name": title,
                    "type": "pie",
                    "radius": ["40%", "70%"],
                    "avoidLabelOverlap": False,
                    "itemStyle": {"borderRadius": 6, "borderColor": "#fff", "borderWidth": 2},
                    "label": {"show": True, "formatter": "{b}: {d}%"},
                    "data": pie_data
                }
            ]
        }
        return {"chart_type": "pie", "echarts_option": option}

    def _build_dual_axis_chart(self, title: str, x_dim: str, metrics: List[str], data: List[Dict[str, Any]]) -> Dict[str, Any]:
        x_data = [str(r.get(x_dim, "")) for r in data]
        vol_col = next((m for m in metrics if not any(pm in m.lower() for pm in PERCENT_METRICS)), metrics[0])
        rate_col = next((m for m in metrics if any(pm in m.lower() for pm in PERCENT_METRICS)), metrics[-1])

        option = {
            "title": {"text": title, "textStyle": {"fontSize": 14, "fontWeight": "normal", "color": "#1F2937"}},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
            "legend": {"top": "bottom", "data": [vol_col, rate_col]},
            "grid": {"left": "4%", "right": "4%", "bottom": "12%", "containLabel": True},
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": [
                {"type": "value", "name": vol_col, "splitLine": {"lineStyle": {"type": "dashed", "color": "#E5E7EB"}}},
                {"type": "value", "name": rate_col + "(%)", "position": "right", "splitLine": {"show": False}}
            ],
            "series": [
                {
                    "name": vol_col,
                    "type": "bar",
                    "barMaxWidth": 35,
                    "itemStyle": {"borderRadius": [4, 4, 0, 0], "color": "#2563EB"},
                    "data": [r.get(vol_col, 0) for r in data]
                },
                {
                    "name": rate_col,
                    "type": "line",
                    "yAxisIndex": 1,
                    "smooth": True,
                    "itemStyle": {"color": "#10B981"},
                    "lineStyle": {"width": 3},
                    "data": [r.get(rate_col, 0) for r in data]
                }
            ]
        }
        return {"chart_type": "dual_axis", "echarts_option": option}

if __name__ == "__main__":
    recommender = ChartRecommender()
    sample_data = [
        {"brand_name": "广汽埃安", "actual_units": 4462, "fulfillment_rate_pct": 96.68},
        {"brand_name": "广汽传祺", "actual_units": 3223, "fulfillment_rate_pct": 102.58},
        {"brand_name": "昊铂", "actual_units": 813, "fulfillment_rate_pct": 100.99}
    ]
    res = recommender.recommend("2025年3月各品牌交付量与达成率", ["brand_name", "actual_units", "fulfillment_rate_pct"], sample_data)
    print("推荐图表类型:", res["chart_type"])
    print("ECharts 系列:", [s["name"] for s in res["echarts_option"]["series"]])
