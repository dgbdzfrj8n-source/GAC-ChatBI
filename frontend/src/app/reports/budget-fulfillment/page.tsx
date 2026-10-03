'use client';

// 预算达成分析报表 (Sprint 8)
// 薄壳：只做路由参数 → ReportRenderer 注入。
// 真实数据 /api/reports/budget-fulfillment?month=YYYY-MM
// 失败降级由 ReportRenderer 内部处理。

import ReportRenderer from '@/components/reports/ReportRenderer';
import { REPORT_REGISTRY } from '@/lib/reportRegistry';

const META = REPORT_REGISTRY['budget-fulfillment'];

export default function BudgetFulfillmentPage() {
  if (!META) {
    return <div className="content-wrap p-6">报表元数据缺失</div>;
  }
  return <ReportRenderer reportMeta={META} />;
}
