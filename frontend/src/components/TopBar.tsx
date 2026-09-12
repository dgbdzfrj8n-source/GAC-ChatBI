'use client';

import { usePathname } from 'next/navigation';
import { pageTitleMap } from '@/lib/menu';
import { useBrand, Brand } from '@/contexts/BrandContext';
import GacLogo from './GacLogo';

const BRANDS: Brand[] = ['全部', '广汽埃安', '广汽传祺', '昊铂'];

export default function TopBar() {
  const pathname = usePathname();
  const { brand, setBrand } = useBrand();

  const pageInfo = pageTitleMap[pathname] ?? {
    title: '广汽云 ChatBI',
    subtitle: '智能经营分析平台',
  };

  // 品牌对应的 emoji
  const brandEmoji: Record<Brand, string> = {
    '全部': '🏢',
    '广汽埃安': '⚡',
    '广汽传祺': '🏯',
    '昊铂': '💎',
  };

  return (
    <header className="topbar">
      {/* 左侧：页面标题 */}
      <div>
        <h1 className="text-lg font-semibold text-gac-gray-900 leading-tight">
          {pageInfo.title}
        </h1>
        <p className="text-xs text-gac-gray-500 mt-0.5">{pageInfo.subtitle}</p>
      </div>

      {/* 右侧：品牌切换 + 状态 + 用户 */}
      <div className="flex items-center space-x-3">
        {/* API 状态 */}
        <span className="hidden md:inline-flex text-xs px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full font-medium">
          <span className="status-dot status-online"></span>
          API 正常
        </span>

        {/* 品牌切换下拉 */}
        <div className="flex items-center gap-1.5 bg-gac-gray-100 rounded-lg px-2 py-1">
          <span className="text-sm">{brandEmoji[brand]}</span>
          <select
            value={brand}
            onChange={(e) => setBrand(e.target.value as Brand)}
            className="text-sm bg-transparent border-none focus:outline-none cursor-pointer text-gac-gray-700 font-medium"
          >
            {BRANDS.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>

        {/* 用户头像（用广汽 Logo 小号） */}
        <div className="flex items-center">
          <GacLogo size="sm" />
          <div className="ml-2 leading-tight hidden lg:block">
            <div className="text-sm font-medium text-gac-gray-900">AI 分析师</div>
            <div className="text-[11px] text-gac-gray-500">在线</div>
          </div>
        </div>
      </div>
    </header>
  );
}
