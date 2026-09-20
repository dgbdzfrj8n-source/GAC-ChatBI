/**
 * [P2-SprintC] 静态导出兼容：报告页
 */
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function RunLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
