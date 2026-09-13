'use client';

// 内层组件：必须 useRole 才能用 NotificationProvider
// 标记 'use client'：Next.js 14 App Router 中，非 'use client' 组件会先被 RSC 预渲染，
// 但 RSC 预渲染阶段不允许调用 hooks（如 useRole），会导致 "d is not a function" 错误。
// 加上 'use client' 后，Next.js 在 RSC 预渲染阶段将其作为 Client Component 组件树来序列化，
// 不再尝试执行 hook，直接渲染空 div 占位，完美规避该问题。
import { useRole } from '@/contexts/RoleContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import NotificationBridge from '@/components/NotificationBridge';
import { BrandProvider } from '@/contexts/BrandContext';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import { PermissionGuard } from '@/components/PermissionGuard';

export function RoleAwareNotificationLayer({ children }: { children: React.ReactNode }) {
  const { role } = useRole();
  return (
    <NotificationProvider role={role}>
      <NotificationBridge />
      {/* 品牌上下文（全局状态） */}
      <BrandProvider>
        {/* ====== 主体：左侧菜单 + 右侧内容 ====== */}
        <div className="flex h-screen overflow-hidden">
          {/* 左侧侧边栏 */}
          <Sidebar />

          {/* 右侧主区域 */}
          <div className="flex-1 flex flex-col overflow-hidden pl-3">
            {/* 顶部栏 */}
            <TopBar />

            {/* 内容区（可滚动；聊天页面会用 chat-full 容器覆盖此处的内边距） */}
            <main className="flex-1 overflow-y-auto bg-gac-gray-50">
              <PermissionGuard>{children}</PermissionGuard>
            </main>
          </div>
        </div>
      </BrandProvider>
    </NotificationProvider>
  );
}
