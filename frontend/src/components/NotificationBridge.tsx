'use client';

import { useEffect } from 'react';
import { useNotifications } from '@/contexts/NotificationContext';

/**
 * 全局事件桥接器：
 * - 监听 gac-notification 自定义事件（任何业务代码可触发通知）
 * - 监听 gac-notification-clear 事件（清除通知）
 */
export default function NotificationBridge() {
  const { add, clearAll } = useNotifications();

  useEffect(() => {
    const onAdd = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail) add(detail);
    };
    const onClear = () => clearAll();
    window.addEventListener('gac-notification', onAdd as EventListener);
    window.addEventListener('gac-notification-clear', onClear);
    return () => {
      window.removeEventListener('gac-notification', onAdd as EventListener);
      window.removeEventListener('gac-notification-clear', onClear);
    };
  }, [add, clearAll]);

  return null;
}
