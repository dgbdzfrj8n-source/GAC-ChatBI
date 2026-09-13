'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useNotifications } from '@/contexts/NotificationContext';
import { NOTIFICATION_META, NotificationType } from '@/lib/notifications';

function fmtTime(iso: string): string {
  const t = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - t.getTime();
  const diffMin = Math.round(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr} 小时前`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 30) return `${diffDay} 天前`;
  return t.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function severityRing(severity: string): string {
  switch (severity) {
    case 'error':
      return 'before:bg-red-500';
    case 'warning':
      return 'before:bg-orange-500';
    case 'success':
      return 'before:bg-emerald-500';
    default:
      return 'before:bg-blue-500';
  }
}

export default function NotificationBell() {
  const { visibleItems, visibleUnreadCount, markRead, markAllRead, remove } = useNotifications();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<'all' | NotificationType>('all');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [open]);

  const filtered =
    filter === 'all' ? visibleItems : visibleItems.filter((n) => n.type === filter);

  // 统计各类型数量
  const typeStats = visibleItems.reduce<Record<string, number>>((acc, n) => {
    acc[n.type] = (acc[n.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="通知中心"
        title="通知中心"
        data-tour="notification-bell"
        className="relative w-9 h-9 flex items-center justify-center rounded-lg text-gac-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors dark:text-gac-gray-300"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {visibleUnreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-sm ring-2 ring-white dark:ring-gac-gray-900">
            {visibleUnreadCount > 99 ? '99+' : visibleUnreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-white dark:bg-gac-gray-900 rounded-xl shadow-2xl border border-gac-gray-200 dark:border-gac-gray-700 z-50 overflow-hidden flex flex-col" style={{ maxHeight: 'min(80vh, 640px)' }}>
          {/* Header */}
          <div className="px-4 py-3 border-b border-gac-gray-200 dark:border-gac-gray-700 flex items-center justify-between flex-shrink-0">
            <div>
              <h3 className="text-sm font-semibold text-gac-gray-900 dark:text-white flex items-center gap-2">
                🔔 通知中心
                {visibleUnreadCount > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 rounded font-mono">
                    {visibleUnreadCount} 未读
                  </span>
                )}
              </h3>
              <p className="text-[11px] text-gac-gray-500 mt-0.5">
                按时间倒序 · 仅显示当前角色可见
              </p>
            </div>
            {visibleUnreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
              >
                全部已读
              </button>
            )}
          </div>

          {/* 类型筛选 chips */}
          <div className="px-3 py-2 border-b border-gac-gray-100 dark:border-gac-gray-800 flex flex-wrap gap-1 flex-shrink-0 overflow-x-auto scrollbar-thin">
            <Chip
              active={filter === 'all'}
              onClick={() => setFilter('all')}
              label="全部"
              count={visibleItems.length}
            />
            {(Object.keys(NOTIFICATION_META) as NotificationType[]).map((t) => {
              const c = typeStats[t] || 0;
              if (c === 0) return null;
              const m = NOTIFICATION_META[t];
              return (
                <Chip
                  key={t}
                  active={filter === t}
                  onClick={() => setFilter(t)}
                  label={m.label}
                  count={c}
                  icon={m.icon}
                />
              );
            })}
          </div>

          {/* 列表 */}
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="py-16 text-center text-gac-gray-400">
                <div className="text-3xl mb-2">📭</div>
                <div className="text-xs">暂无通知</div>
              </div>
            ) : (
              <ul>
                {filtered.map((n) => {
                  const meta = NOTIFICATION_META[n.type];
                  const item = (
                    <div
                      onClick={() => markRead(n.id)}
                      className={`relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 ${severityRing(n.severity)} ${
                        n.read
                          ? 'bg-white dark:bg-gac-gray-900'
                          : 'bg-blue-50/40 dark:bg-blue-900/10'
                      } hover:bg-gac-gray-50 dark:hover:bg-gac-gray-800 px-4 py-3 cursor-pointer transition-colors`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${meta.badgeBg} ${meta.badgeText}`}>
                          {meta.icon} {meta.label}
                        </span>
                        {!n.read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0 mt-1.5" />
                        )}
                      </div>
                      <div className={`text-sm mt-1.5 leading-snug ${n.read ? 'text-gac-gray-700 dark:text-gac-gray-400' : 'text-gac-gray-900 dark:text-white font-medium'}`}>
                        {n.title}
                      </div>
                      <div className="text-xs text-gac-gray-500 mt-1 leading-relaxed">
                        {n.body}
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-[10px] text-gac-gray-400">{fmtTime(n.timestamp)}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(n.id);
                          }}
                          className="text-[10px] text-gac-gray-400 hover:text-red-500"
                          title="删除"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  );
                  return (
                    <li key={n.id} className="border-b border-gac-gray-100 dark:border-gac-gray-800 last:border-b-0">
                      {n.link ? (
                        <Link href={n.link} onClick={() => { markRead(n.id); setOpen(false); }}>
                          {item}
                        </Link>
                      ) : (
                        item
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-gac-gray-100 dark:border-gac-gray-800 bg-gac-gray-50/50 dark:bg-gac-gray-800/30 flex items-center justify-between flex-shrink-0">
            <span className="text-[11px] text-gac-gray-500">
              共 {visibleItems.length} 条 · 未读 {visibleUnreadCount}
            </span>
            <Link
              href="/help"
              onClick={() => setOpen(false)}
              className="text-[11px] text-blue-600 hover:underline"
            >
              通知设置 →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function Chip({
  active,
  onClick,
  label,
  count,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  icon?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full transition-colors whitespace-nowrap ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-gac-gray-100 dark:bg-gac-gray-800 text-gac-gray-700 dark:text-gac-gray-300 hover:bg-gac-gray-200 dark:hover:bg-gac-gray-700'
      }`}
    >
      {icon && <span>{icon}</span>}
      <span>{label}</span>
      <span className={`text-[10px] ${active ? 'text-blue-100' : 'text-gac-gray-500'}`}>{count}</span>
    </button>
  );
}
