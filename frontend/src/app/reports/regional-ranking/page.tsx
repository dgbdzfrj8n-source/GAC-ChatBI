'use client';

import ReportRenderer from '@/components/reports/ReportRenderer';
import { REPORT_REGISTRY } from '@/lib/reportRegistry';

const META = REPORT_REGISTRY['regional-ranking'];

export default function RegionalRankingPage() {
  if (!META) return <div className="content-wrap p-6">报表元数据缺失</div>;
  return <ReportRenderer reportMeta={META} />;
}
