'use client';

import ReportRenderer from '@/components/reports/ReportRenderer';
import { REPORT_REGISTRY } from '@/lib/reportRegistry';

const META = REPORT_REGISTRY['sales-attribution'];

export default function SalesAttributionPage() {
  if (!META) return <div className="content-wrap p-6">报表元数据缺失</div>;
  return <ReportRenderer reportMeta={META} />;
}
