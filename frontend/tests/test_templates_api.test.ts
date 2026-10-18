/**
 * TC-FE-LT 测试用例
 * 对应 BUG-002 修复：listTemplates 改用 authFetch
 *
 * 参考：
 * - SDD §3.3
 * - SDD_TEST_CASES_TEMPLATES_BUGFIX.md §2.2
 * - 测试报告 TC-TPL-042
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock auth module（必须先 mock，listTemplates 才用 mock 版的 authFetch）
const authFetchMock = vi.fn();
vi.mock("../src/lib/auth", () => ({
  authFetch: (...args: any[]) => authFetchMock(...args),
}));

import { listTemplates } from "../src/lib/templates-api";

describe("listTemplates - BUG-002 鉴权修复", () => {
  beforeEach(() => {
    authFetchMock.mockReset();
    localStorage.setItem("gac_chatbi_token", "test_token_123");
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("TC-FE-LT-001: should call authFetch (not raw fetch) for /api/sop/templates", async () => {
    authFetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        system_presets: [],
        role_default_id: "preset_model_product",
        role_defaults_map: { product: "preset_model_product" },
        user_templates: [],
      }),
    });

    await listTemplates("product", "zhangsan");

    expect(authFetchMock).toHaveBeenCalledTimes(1);
    const url = authFetchMock.mock.calls[0][0];
    expect(url).toContain("/api/sop/templates");
    expect(url).toContain("role=product");
    expect(url).toContain("user=zhangsan");
  });

  it("TC-FE-LT-002: should return user_templates when authenticated", async () => {
    const mockData = {
      system_presets: [],
      role_default_id: "preset_model_product",
      role_defaults_map: { product: "preset_model_product" },
      user_templates: [
        { id: "user_123", name: "我的模板", scope: "user" },
      ],
    };
    authFetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await listTemplates("product", "zhangsan");

    expect(result.user_templates).toHaveLength(1);
    expect(result.user_templates[0].id).toBe("user_123");
  });

  it("TC-FE-LT-003: should throw on non-2xx response", async () => {
    authFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Unauthorized" }),
    });

    await expect(listTemplates("product", "zhangsan")).rejects.toThrow(
      "listTemplates failed: 401"
    );
  });

  it("TC-FE-LT-004 [BUG-002 核心]: should NOT use raw fetch (verifies fix)", async () => {
    // 这个测试的意义是：如果有人误把代码改回 fetch()，这个测试会失败
    // 因为 fetch 是全局函数，没被 mock
    const rawFetchSpy = vi.spyOn(global, "fetch");

    authFetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ system_presets: [], user_templates: [] }),
    });

    await listTemplates("product", "zhangsan");

    expect(rawFetchSpy).not.toHaveBeenCalled();
    expect(authFetchMock).toHaveBeenCalledTimes(1);
  });

  it("TC-FE-LT-005: should handle missing role/user params", async () => {
    authFetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ system_presets: [], user_templates: [] }),
    });

    await listTemplates();

    const url = authFetchMock.mock.calls[0][0];
    expect(url).toContain("/api/sop/templates");
    expect(url).not.toContain("role=");
    expect(url).not.toContain("user=");
  });
});
