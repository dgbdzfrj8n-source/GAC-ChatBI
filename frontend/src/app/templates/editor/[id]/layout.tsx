/**
 * [P2-SprintC] 静态导出兼容：
 * - next export 要求所有动态路由声明 generateStaticParams
 * - 这里给一个 dummy id 让 build 通过；运行时由客户端组件接管
 */
export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function EditorLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
