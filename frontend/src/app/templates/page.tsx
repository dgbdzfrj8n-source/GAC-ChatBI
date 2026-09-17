"use client";

import { useEffect, useState } from "react";
import { Plus, Edit2, Trash2, X, Loader2, FileText, Lock, User, Star } from "lucide-react";

interface Template {
  id: string;
  name: string;
  description: string;
  scope: "system" | "user";
  owner_role?: string | null;
  owner_user?: string | null;
  dimensions: string[];
  created_at?: string;
  updated_at?: string;
}

interface TemplateListResponse {
  system_presets: Template[];
  role_default_id: string | null;
  role_defaults_map: Record<string, string>;
  user_templates: Template[];
}

const DIMENSION_LABELS: Record<string, string> = {
  brand_name: "品牌",
  region_name: "区域",
  model_name: "车型",
  energy_type: "能源类型",
  price_segment: "价格段",
  monthly: "时间",
};

const ALL_DIMENSIONS = [
  { key: "brand_name",    desc: "广丰 / 广本 / 自主" },
  { key: "region_name",   desc: "华南 / 华北 / 华东 / 华中" },
  { key: "model_name",    desc: "轿车 / SUV / MPV" },
  { key: "energy_type",   desc: "纯电 / 混动 / 燃油" },
  { key: "price_segment", desc: "高价车 / 中价车 / 低价车" },
  { key: "monthly",       desc: "周内波动 / 月初 vs 月末" },
];

const ROLE_LABELS: Record<string, string> = {
  executive: "高管",
  analyst:   "分析师",
  product:   "产品经理",
  visitor:   "访客",
};

export default function TemplatesPage() {
  const [data, setData] = useState<TemplateListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentRole, setCurrentRole] = useState<string>("executive");
  const [currentUser, setCurrentUser] = useState<string>("admin");
  const [editing, setEditing] = useState<Template | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);

  // 加载数据
  const loadTemplates = async () => {
    setLoading(true);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(
        `${API_URL}/api/sop/templates?role=${currentRole}&user=${currentUser}`
      );
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Failed to load templates:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRole, currentUser]);

  // 删除模板
  const handleDelete = async (id: string) => {
    if (!confirm("确定删除这个模板吗？")) return;
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/sop/templates/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_id: id, owner_user: currentUser }),
      });
      if (res.ok) {
        await loadTemplates();
      } else {
        const err = await res.json();
        alert(err.detail || "删除失败");
      }
    } catch (e: any) {
      alert(`删除失败: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <FileText className="w-8 h-8 text-purple-600" />
            归因维度模板中心
          </h1>
          <p className="text-sm text-gray-500 mt-2">
            预置 + 角色默认 + 用户自定义 · 三类模板统一管理，让 SOP 归因"千人千面"
          </p>
        </div>

        {/* 角色切换器 */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex items-center gap-4">
          <span className="text-sm text-gray-500">当前角色：</span>
          <div className="flex gap-2">
            {Object.entries(ROLE_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setCurrentRole(key)}
                className={`px-4 py-1.5 text-sm rounded-lg transition-colors ${
                  currentRole === key
                    ? "bg-purple-600 text-white shadow-sm"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            新建我的模板
          </button>
        </div>

        {/* 角色默认提示 */}
        {data && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-center gap-3">
            <Star className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="text-sm">
              <span className="font-medium text-amber-900">
                {ROLE_LABELS[currentRole]}角色默认模板：
              </span>
              {data.system_presets.find((t) => t.id === data.role_default_id)?.name ||
                "（未绑定）"}
              <span className="ml-3 text-xs text-amber-700">
                点击 SOP「深度归因」时，会自动预选该模板的维度
              </span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
            <span className="ml-2 text-sm text-gray-500">加载模板...</span>
          </div>
        ) : (
          <>
            {/* 系统预设 */}
            <section className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Lock className="w-4 h-4 text-gray-400" />
                系统预设模板（{data?.system_presets.length || 0}）
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data?.system_presets.map((t) => (
                  <TemplateCard
                    key={t.id}
                    template={t}
                    isDefault={t.id === data.role_default_id}
                    onEdit={() => setEditing(t)}
                    onDelete={() => handleDelete(t.id)}
                  />
                ))}
              </div>
            </section>

            {/* 用户自定义 */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-emerald-500" />
                我的模板（{data?.user_templates.length || 0}）
              </h2>
              {data?.user_templates.length === 0 ? (
                <div className="bg-white border-2 border-dashed border-gray-200 rounded-xl p-10 text-center">
                  <p className="text-sm text-gray-400 mb-3">
                    还没有自定义模板。点击右上角"新建我的模板"开始
                  </p>
                  <button
                    onClick={() => setCreating(true)}
                    className="text-sm text-purple-600 hover:underline"
                  >
                    + 立即创建
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {data?.user_templates.map((t) => (
                    <TemplateCard
                      key={t.id}
                      template={t}
                      isDefault={false}
                      onEdit={() => setEditing(t)}
                      onDelete={() => handleDelete(t.id)}
                    />
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {/* 编辑/创建弹窗 */}
        {(editing || creating) && (
          <TemplateEditor
            template={editing || undefined}
            onClose={() => {
              setEditing(null);
              setCreating(false);
            }}
            onSaved={async () => {
              setSaving(false);
              setEditing(null);
              setCreating(false);
              await loadTemplates();
            }}
            ownerUser={currentUser}
            ownerRole={currentRole}
            saving={saving}
            setSaving={setSaving}
          />
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// 模板卡片
// ────────────────────────────────────────────────────────────────────
function TemplateCard({
  template,
  isDefault,
  onEdit,
  onDelete,
}: {
  template: Template;
  isDefault: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const isSystem = template.scope === "system";
  return (
    <div
      className={`bg-white rounded-xl border p-5 hover:shadow-md transition-all ${
        isDefault ? "border-amber-300 ring-2 ring-amber-100" : "border-gray-200"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{template.name}</h3>
          {isDefault && (
            <span className="flex items-center gap-0.5 px-2 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded-full font-medium">
              <Star className="w-3 h-3" />
              当前角色默认
            </span>
          )}
        </div>
        {!isSystem && (
          <div className="flex gap-1 flex-shrink-0">
            <button
              onClick={onEdit}
              className="p-1.5 hover:bg-gray-100 rounded transition-colors"
              title="编辑"
            >
              <Edit2 className="w-3.5 h-3.5 text-gray-500" />
            </button>
            <button
              onClick={onDelete}
              className="p-1.5 hover:bg-red-50 rounded transition-colors"
              title="删除"
            >
              <Trash2 className="w-3.5 h-3.5 text-red-500" />
            </button>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-3 line-clamp-2 min-h-[2.5rem]">
        {template.description || "（无描述）"}
      </p>
      <div className="flex flex-wrap gap-1">
        {template.dimensions.map((d) => (
          <span
            key={d}
            className="inline-block px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded"
          >
            {DIMENSION_LABELS[d] || d}
          </span>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
        <span>{isSystem ? "🔒 系统预设" : "✏️ 用户自定义"}</span>
        {template.updated_at && <span>{template.updated_at}</span>}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// 模板编辑器
// ────────────────────────────────────────────────────────────────────
function TemplateEditor({
  template,
  onClose,
  onSaved,
  ownerUser,
  ownerRole,
  saving,
  setSaving,
}: {
  template?: Template;
  onClose: () => void;
  onSaved: () => Promise<void>;
  ownerUser: string;
  ownerRole: string;
  saving: boolean;
  setSaving: (b: boolean) => void;
}) {
  const isEdit = !!template;
  const [name, setName] = useState(template?.name || "");
  const [description, setDescription] = useState(template?.description || "");
  const [dimensions, setDimensions] = useState<string[]>(template?.dimensions || []);

  const toggle = (key: string) => {
    if (dimensions.includes(key)) {
      setDimensions(dimensions.filter((d) => d !== key));
    } else if (dimensions.length < 4) {
      setDimensions([...dimensions, key]);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      alert("请输入模板名称");
      return;
    }
    if (dimensions.length === 0) {
      alert("请至少选 1 个维度");
      return;
    }
    setSaving(true);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = isEdit ? "/api/sop/templates/update" : "/api/sop/templates/create";
      const body = isEdit
        ? {
            template_id: template!.id,
            name,
            description,
            dimensions,
            owner_user: ownerUser,
          }
        : {
            name,
            description,
            dimensions,
            owner_role: ownerRole,
            owner_user: ownerUser,
          };
      const res = await fetch(`${API_URL}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        await onSaved();
      } else {
        const err = await res.json();
        alert(err.detail || "保存失败");
      }
    } catch (e: any) {
      alert(`保存失败: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-purple-50 to-indigo-50">
          <h3 className="text-base font-semibold text-gray-900">
            {isEdit ? "编辑模板" : "新建模板"}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-white/60 rounded">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 block">
              模板名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500"
              placeholder="例如：高管周报视图"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 block">
              描述（可选）
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500"
              placeholder="这个模板的适用场景"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 mb-2 block">
              选择归因维度 <span className="text-gray-400">（最多 4 个，已选 {dimensions.length}/4）</span>
            </label>
            <div className="space-y-1.5">
              {ALL_DIMENSIONS.map((dim) => {
                const checked = dimensions.includes(dim.key);
                const disabled = !checked && dimensions.length >= 4;
                return (
                  <label
                    key={dim.key}
                    className={`flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer transition-all ${
                      checked
                        ? "border-purple-300 bg-purple-50"
                        : disabled
                          ? "opacity-50 cursor-not-allowed"
                          : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggle(dim.key)}
                      className="w-4 h-4 text-purple-600"
                    />
                    <span className="text-sm font-medium text-gray-900">
                      {DIMENSION_LABELS[dim.key]}
                    </span>
                    <span className="text-xs text-gray-400">· {dim.desc}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="flex-1 py-2 text-sm border border-gray-300 rounded-lg hover:bg-white disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || dimensions.length === 0}
            className="flex-1 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-1"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {saving ? "保存中..." : isEdit ? "保存修改" : "创建模板"}
          </button>
        </div>
      </div>
    </div>
  );
}
