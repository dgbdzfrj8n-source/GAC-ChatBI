'use client';

import SnapshotBoard from '@/components/reports/SnapshotBoard';

// 驾驶舱大屏：复用报表中心的 SnapshotBoard，保持数据来源 / 视觉一致。
// 仅替换顶部标题与脚注，不重复实现 KPI / 趋势 / 排名 / 预警。

export default function DashboardPage() {
  return (
    <SnapshotBoard
      title="广汽集团经营驾驶舱"
      subtitle="Sprint 5.2 实现 · 数据由 /api/dashboard/snapshot 实时聚合"
    />
  );
}
