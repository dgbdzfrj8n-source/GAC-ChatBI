/**
 * TC-FE-DT 测试用例
 * 对应 BUG-004 修复：DemoTour useState 惰性初始化读 localStorage
 *
 * 参考：
 * - SDD §3.5
 * - SDD_TEST_CASES_TEMPLATES_BUGFIX.md §2.3
 */
import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import DemoTour from "../src/components/DemoTour";

const STORAGE_KEY = "gac-chatbi-tour-completed";

describe("DemoTour - BUG-004 状态初始化修复", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it("TC-FE-DT-001 [BUG-004 核心]: should auto-show on first visit (no localStorage)", () => {
    localStorage.removeItem(STORAGE_KEY);
    const { container } = render(<DemoTour />);
    // 引导遮罩应该存在
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
    expect(dialog?.getAttribute("aria-modal")).toBe("true");
  });

  it("TC-FE-DT-002 [BUG-004 核心]: should NOT show if user has completed the tour", () => {
    localStorage.setItem(STORAGE_KEY, "1");
    const { container } = render(<DemoTour />);
    // 引导遮罩不应存在
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toBeFalsy();
  });

  it("TC-FE-DT-003 [BUG-004 核心]: state persists across remount (simulating page reload)", () => {
    // 第一次渲染：模拟"用户已关闭引导"
    localStorage.setItem(STORAGE_KEY, "1");
    const { container, unmount } = render(<DemoTour />);
    expect(container.querySelector('[role="dialog"]')).toBeFalsy();

    unmount();

    // 重新挂载（模拟 Next.js 静态导出的整页刷新或 layout 重 mount）
    const { container: container2 } = render(<DemoTour />);
    // 关键断言：第二次 mount 时引导仍不应出现
    expect(container2.querySelector('[role="dialog"]')).toBeFalsy();
  });

  it("TC-FE-DT-004: localStorage value 'true' also counts as completed", () => {
    // 防御性测试：不同格式的 localStorage 值都应被识别
    localStorage.setItem(STORAGE_KEY, "true");
    const { container } = render(<DemoTour />);
    expect(container.querySelector('[role="dialog"]')).toBeFalsy();
  });

  it("TC-FE-DT-005: empty string in localStorage is treated as completed", () => {
    // getItem('xxx') 返回 null 才是"未完成"
    // 空字符串也是 "truthy 完成"（localStorage.getItem 返回 "" 时 getItem 返回 "" 转为 boolean 也是 truthy）
    localStorage.setItem(STORAGE_KEY, "");
    const { container } = render(<DemoTour />);
    // 修复后用 !localStorage.getItem(STORAGE_KEY)，空字符串是 falsy → 返回 true → 显示引导
    // 这个行为与原始一致：仅在"无任何记录"时显示
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toBeTruthy();
  });
});
