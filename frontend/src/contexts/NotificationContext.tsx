'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import {
  NotificationItem,
  NotificationType,
} from '@/lib/notifications';
import { generateSeedNotifications } from '@/lib/notification-seeds';
import { Role } from '@/lib/roles';

const STORAGE_KEY = 'gac-notifications';
const READ_KEY = 'gac-notifications-read';

interface NotificationContextValue {
  items: NotificationItem[];
  unreadCount: number;
  add: (n: Omit<NotificationItem, 'id' | 'timestamp' | 'read'>) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  remove: (id: string) => void;
  clearAll: () => void;
  reset: () => void;
  /** 按角色过滤后的可见通知 */
  visibleItems: NotificationItem[];
  /** 按角色过滤后的未读数 */
  visibleUnreadCount: number;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({
  children,
  role,
}: {
  children: ReactNode;
  role: Role;
}) {
  const [items, setItems] = useState<NotificationItem[]>([]);

  // 首次加载：从种子生成 + 应用已读状态
  useEffect(() => {
    const seeds = generateSeedNotifications();
    try {
      const readJson = localStorage.getItem(READ_KEY);
      const readSet = readJson ? new Set(JSON.parse(readJson) as string[]) : new Set<string>();
      setItems(seeds.map((s) => (readSet.has(s.id) ? { ...s, read: true } : s)));
    } catch {
      setItems(seeds);
    }
  }, []);

  const persistRead = useCallback((next: NotificationItem[]) => {
    try {
      const readIds = next.filter((n) => n.read).map((n) => n.id);
      localStorage.setItem(READ_KEY, JSON.stringify(readIds));
    } catch {
      // ignore
    }
  }, []);

  const add = useCallback(
    (n: Omit<NotificationItem, 'id' | 'timestamp' | 'read'>) => {
      const newItem: NotificationItem = {
        ...n,
        id: `live-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
        read: false,
      };
      setItems((prev) => {
        const next = [newItem, ...prev];
        persistRead(next);
        return next;
      });
    },
    [persistRead]
  );

  const markRead = useCallback(
    (id: string) => {
      setItems((prev) => {
        const next = prev.map((n) => (n.id === id ? { ...n, read: true } : n));
        persistRead(next);
        return next;
      });
    },
    [persistRead]
  );

  const markAllRead = useCallback(() => {
    setItems((prev) => {
      const next = prev.map((n) => ({ ...n, read: true }));
      persistRead(next);
      return next;
    });
  }, [persistRead]);

  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setItems([]);
    try {
      localStorage.removeItem(READ_KEY);
    } catch {
      // ignore
    }
  }, []);

  const reset = useCallback(() => {
    const seeds = generateSeedNotifications();
    setItems(seeds);
    try {
      localStorage.removeItem(READ_KEY);
    } catch {
      // ignore
    }
  }, []);

  // 按角色过滤可见通知
  const visibleItems = items.filter((n) => !n.audience || n.audience.length === 0 || n.audience.includes(role));
  const visibleUnreadCount = visibleItems.filter((n) => !n.read).length;
  const unreadCount = items.filter((n) => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{
        items,
        unreadCount,
        add,
        markRead,
        markAllRead,
        remove,
        clearAll,
        reset,
        visibleItems,
        visibleUnreadCount,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationProvider');
  return ctx;
}

/**
 * 全局事件桥接：允许非 React 上下文代码派发通知
 * 用法：window.dispatchEvent(new CustomEvent('gac-notification', { detail: {...} }))
 */
export function dispatchNotification(payload: Omit<NotificationItem, 'id' | 'timestamp' | 'read'>) {
  window.dispatchEvent(new CustomEvent('gac-notification', { detail: payload }));
}
