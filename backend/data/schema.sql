-- ==============================================================================
-- 广汽集团经营分析数仓 DDL（DuckDB OLAP）
-- 包含三大核心业务域：整车销售交付域、预算目标域、市场营销支出域
-- ==============================================================================

-- 1. 整车销售交付事实表（日粒度）
CREATE TABLE IF NOT EXISTS fact_sales_daily (
    sale_date DATE,                    -- 销售交付日期 (YYYY-MM-DD)
    brand_name VARCHAR,                -- 品牌：广汽埃安、广汽传祺、昊铂
    model_name VARCHAR,                -- 车型：AION Y, AION S, 传祺GS8, 传祺M8, 传祺影豹, 昊铂GT, 昊铂HT
    region_name VARCHAR,               -- 销售大区：华南区、华东区、华北区、华中区、西南区
    province_name VARCHAR,             -- 省份
    delivered_units INTEGER,           -- 当日实际交付量（辆）
    gross_revenue DOUBLE,              -- 交付开票总营收（元）
    discount_rate DOUBLE,              -- 终端加权平均折扣率 (如 0.085 代表 8.5%)
    customer_leads INTEGER,            -- 当日进店意向留档客流数（组）
    test_drives INTEGER                -- 试乘试驾完成次数（次）
);

-- 2. 集团经营预算与销量目标表（月粒度）
CREATE TABLE IF NOT EXISTS dim_budget_target (
    year_month VARCHAR,                -- 年月标识 (YYYY-MM)
    brand_name VARCHAR,                -- 品牌：广汽埃安、广汽传祺、昊铂
    target_units INTEGER,              -- 预算交付目标（辆）
    target_revenue DOUBLE,             -- 预算总营收目标（元）
    expense_limit DOUBLE               -- 预算营销与运营费用限额（元）
);

-- 3. 市场营销获客支出事实表（日/渠道粒度）
CREATE TABLE IF NOT EXISTS fact_marketing_expenses (
    expense_date DATE,                 -- 费用发生日期 (YYYY-MM-DD)
    brand_name VARCHAR,                -- 品牌：广汽埃安、广汽传祺、昊铂
    channel_name VARCHAR,              -- 投放渠道：懂车帝垂直类、抖音信息流、商圈巡展外拓、区域广播与电梯屏
    expense_category VARCHAR,          -- 费用类别：线上公域投放、线下巡展体验、终端促销补贴
    expense_amount DOUBLE,             -- 实际支出金额（元）
    leads_generated INTEGER            -- 投放带来的集客线索总量（条）
);

-- 4. 经销商库存事实表（日/经销商/车型粒度）— Sprint 8 报表中心新增
CREATE TABLE IF NOT EXISTS fact_dealer_inventory_daily (
    snapshot_date DATE,                -- 库存快照日期
    dealer_name VARCHAR,               -- 经销商名称：广州埃安珠江新城店、长沙传祺麓谷店 等
    brand_name VARCHAR,                -- 所属品牌
    region_name VARCHAR,               -- 所属大区
    model_name VARCHAR,                -- 车型
    inventory_units INTEGER,           -- 期末库存台数
    days_in_stock INTEGER              -- 平均库龄（天），0 表示当月新车
);

-- 5. 客流转化漏斗事件表（事实表）— Sprint 8 报表中心新增
-- 用事件流而非聚合表，便于灵活切维度（车型/大区/渠道）。
CREATE TABLE IF NOT EXISTS fact_funnel_event (
    event_date DATE,                   -- 事件日期
    event_stage VARCHAR,               -- 事件阶段：store_visit / lead_created / test_drive / order_created
    brand_name VARCHAR,                -- 品牌
    region_name VARCHAR,               -- 大区
    dealer_name VARCHAR,               -- 所属门店
    session_id VARCHAR                 -- 会话编号，用于跨阶段串联同一客流
);

-- 6. 经销商主数据维度表
CREATE TABLE IF NOT EXISTS dim_dealer (
    dealer_name VARCHAR,
    brand_name VARCHAR,
    region_name VARCHAR,
    dealer_type VARCHAR                -- 直营店 / 经销店 / 商超店
);
