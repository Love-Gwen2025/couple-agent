/**
 * 模型设置页面组件
 *
 * 功能：
 * 1. 表格列表展示用户自定义模型配置
 * 2. 支持启用/停用、编辑操作
 * 3. 针对不同提供商显示差异化配置表单
 */
import { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Edit2, Trash2, Loader2, CheckCircle, XCircle, TestTube, Power, PowerOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useNavigationStore } from '../../store';
import {
    getUserModels,
    createUserModel,
    updateUserModel,
    deleteUserModel,
    setDefaultUserModel,
    testUserModel,
} from '../../api';
import type { UserModel, UserModelPayload, UserModelTestPayload } from '../../types';

/** 提供商配置 */
const PROVIDERS = [
    { value: 'deepseek', label: 'DeepSeek', defaultBaseUrl: 'https://api.deepseek.com' },
    { value: 'openai', label: 'OpenAI', defaultBaseUrl: 'https://api.openai.com/v1' },
    { value: 'gemini', label: 'Google Gemini', defaultBaseUrl: '' },
    { value: 'custom', label: 'Custom', defaultBaseUrl: '' },
];

/** 常用模型预设 */
const MODEL_PRESETS: Record<string, string[]> = {
    deepseek: ['deepseek-chat', 'deepseek-reasoner'],
    openai: ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo', 'o1-mini', 'o1-preview'],
    gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro'],
    custom: [],
};

/**
 * 各提供商支持的参数配置
 * - baseUrl: 是否显示 Base URL 字段
 * - timeout: 是否显示 Timeout 字段
 * - topP: 是否显示 Top P 字段
 * - maxTokens: 是否显示 Max Tokens 字段
 * - topK: 是否显示 Top K 字段 (Gemini 专用)
 */
const PROVIDER_PARAMS: Record<string, {
    baseUrl: boolean;
    baseUrlRequired: boolean;
    timeout: boolean;
    topP: boolean;
    maxTokens: boolean;
    topK: boolean;
}> = {
    deepseek: { baseUrl: true, baseUrlRequired: false, timeout: true, topP: true, maxTokens: true, topK: false },
    openai: { baseUrl: true, baseUrlRequired: false, timeout: true, topP: true, maxTokens: true, topK: false },
    gemini: { baseUrl: false, baseUrlRequired: false, timeout: false, topP: true, maxTokens: false, topK: true },
    custom: { baseUrl: true, baseUrlRequired: true, timeout: true, topP: false, maxTokens: false, topK: false },
};

export function ModelSettingsPage() {
    // 导航状态
    const { setCurrentPage } = useNavigationStore();
    const [models, setModels] = useState<UserModel[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [editingModel, setEditingModel] = useState<UserModel | null>(null);

    // 加载模型列表
    useEffect(() => {
        loadModels();
    }, []);

    async function loadModels() {
        setLoading(true);
        const data = await getUserModels();
        setModels(data);
        setLoading(false);
    }

    // 切换模型状态 (启用/停用)
    async function handleToggleStatus(model: UserModel) {
        try {
            const newStatus = model.status === 1 ? 0 : 1;
            await updateUserModel(model.id, { provider: model.provider, modelName: model.modelName, modelCode: model.modelCode });
            // 临时更新 UI (后续API支持status字段更新后可改进)
            setModels(models.map((m) => m.id === model.id ? { ...m, status: newStatus } : m));
        } catch (e) {
            alert('操作失败: ' + (e as Error).message);
        }
    }

    // 设为默认
    async function handleSetDefault(id: string) {
        try {
            await setDefaultUserModel(id);
            setModels(models.map((m) => ({ ...m, isDefault: m.id === id })));
        } catch (e) {
            alert('设置失败: ' + (e as Error).message);
        }
    }

    // 删除
    async function handleDelete(id: string) {
        if (!confirm('确定要删除这个配置吗？')) return;
        try {
            await deleteUserModel(id);
            setModels(models.filter((m) => m.id !== id));
        } catch (e) {
            alert('删除失败: ' + (e as Error).message);
        }
    }

    // 保存 (新增或修改)
    async function handleSave(data: UserModelPayload) {
        if (editingModel) {
            await updateUserModel(editingModel.id, data);
        } else {
            await createUserModel(data);
        }
        setShowAddModal(false);
        setEditingModel(null);
        loadModels();
    }

    return (
        <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
            {/* Header */}
            <header className="flex items-center gap-4 px-8 py-6 border-b border-border/10 bg-surface/50 backdrop-blur-md z-10">
                <button
                    onClick={() => setCurrentPage('chat')}
                    className="p-2.5 rounded-2xl hover:bg-surface-highlight/20 transition-all text-muted hover:text-foreground active:scale-90"
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <h1 className="text-2xl font-black tracking-tight text-foreground uppercase italic pb-1">AI Models</h1>
                    <p className="text-xs text-muted tracking-widest uppercase">Configure LLM Connections & Parameters</p>
                </div>
                <button
                    onClick={() => {
                        setEditingModel(null);
                        setShowAddModal(true);
                    }}
                    className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-lg shadow-purple-500/20 hover:shadow-purple-500/40 active:scale-95 transition-all text-sm uppercase tracking-wide"
                >
                    <Plus className="w-4 h-4" />
                    Connect Model
                </button>
            </header>

            {/* Content */}
            <main className="flex-1 p-8 overflow-y-auto custom-scrollbar">
                {loading ? (
                    <div className="h-full flex items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
                    </div>
                ) : (
                    <div className="glass-premium dual-stroke shadow-premium rounded-[32px] overflow-hidden bg-surface/20">
                        <table className="w-full text-left">
                            <thead className="bg-surface/40 border-b border-border/10">
                                <tr>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Model Name</th>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Provider</th>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Model Code</th>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Status</th>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Default</th>
                                    <th className="px-6 py-4 text-[10px] font-black text-muted text-right uppercase tracking-widest">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border/5">
                                {models.map((model) => (
                                    <ModelRow
                                        key={model.id}
                                        model={model}
                                        onEdit={() => {
                                            setEditingModel(model);
                                            setShowAddModal(true);
                                        }}
                                        onToggleStatus={() => handleToggleStatus(model)}
                                        onSetDefault={() => handleSetDefault(model.id)}
                                        onDelete={() => handleDelete(model.id)}
                                    />
                                ))}
                                {models.length === 0 && (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-12 text-center text-muted font-medium">
                                            No models connected. Add one to get started.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>

            {/* Add/Edit Modal */}
            <AnimatePresence>
                {showAddModal && (
                    <ModelFormModal
                        model={editingModel}
                        onClose={() => {
                            setShowAddModal(false);
                            setEditingModel(null);
                        }}
                        onSave={handleSave}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

/** 模型行组件 */
function ModelRow({
    model,
    onEdit,
    onToggleStatus,
    onSetDefault,
    onDelete,
}: {
    model: UserModel;
    onEdit: () => void;
    onToggleStatus: () => void;
    onSetDefault: () => void;
    onDelete: () => void;
}) {
    const providerLabel = PROVIDERS.find((p) => p.value === model.provider)?.label || model.provider;

    return (
        <tr className="border-b border-border/5 last:border-0 hover:bg-surface-highlight/5 transition-colors group">
            {/* Model Name */}
            <td className="px-6 py-5">
                <span className="font-bold text-foreground tracking-tight">{model.modelName}</span>
            </td>
            {/* Provider */}
            <td className="px-6 py-5">
                <span className="px-3 py-1 text-[10px] font-black rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase tracking-widest">
                    {providerLabel}
                </span>
            </td>
            {/* Model Code */}
            <td className="px-6 py-5">
                <code className="text-[11px] text-muted bg-surface/40 px-2 py-1 rounded-md border border-border/10">{model.modelCode}</code>
            </td>
            {/* Status */}
            <td className="px-6 py-5 text-center">
                <span
                    className={clsx(
                        'px-3 py-1 text-[10px] font-black rounded-full uppercase tracking-widest',
                        model.status === 1
                            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                            : 'bg-surface-highlight/10 text-muted border border-border/10'
                    )}
                >
                    {model.status === 1 ? 'ONLINE' : 'OFFLINE'}
                </span>
            </td>
            {/* Default */}
            <td className="px-6 py-5 text-center">
                {model.isDefault ? (
                    <span className="px-3 py-1 text-[10px] font-black rounded-full bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 uppercase tracking-widest">
                        ★ PRIMARY
                    </span>
                ) : (
                    <button
                        onClick={onSetDefault}
                        className="px-3 py-1 text-[10px] font-black text-muted hover:text-foreground transition-all uppercase tracking-widest active:scale-95"
                    >
                        SET PRIMARY
                    </button>
                )}
            </td>
            {/* Actions */}
            <td className="px-6 py-5">
                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* Enable/Disable 按钮 */}
                    <button
                        onClick={onToggleStatus}
                        className={clsx(
                            'p-2.5 rounded-xl transition-all active:scale-90',
                            model.status === 1
                                ? 'text-green-400 hover:bg-green-500/10'
                                : 'text-muted hover:bg-surface-highlight/10'
                        )}
                        title={model.status === 1 ? 'Deactivate' : 'Activate'}
                    >
                        {model.status === 1 ? (
                            <Power className="w-4 h-4" />
                        ) : (
                            <PowerOff className="w-4 h-4" />
                        )}
                    </button>
                    {/* Edit 按钮 */}
                    <button
                        onClick={onEdit}
                        className="p-2.5 rounded-xl text-muted hover:text-foreground hover:bg-surface-highlight/10 transition-all active:scale-90"
                        title="Edit Configuration"
                    >
                        <Edit2 className="w-4 h-4" />
                    </button>
                    {/* Delete 按钮 */}
                    <button
                        onClick={onDelete}
                        className="p-2.5 rounded-xl text-muted hover:text-red-400 hover:bg-red-500/10 transition-all active:scale-90"
                        title="Purge Link"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </td>
        </tr>
    );
}

/** 模型表单模态框 - 差异化表单 */
function ModelFormModal({
    model,
    onClose,
    onSave,
}: {
    model: UserModel | null;
    onClose: () => void;
    onSave: (data: UserModelPayload) => Promise<void>;
}) {
    const isEdit = !!model;
    const [loading, setLoading] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

    // 表单状态
    const [provider, setProvider] = useState(model?.provider || 'deepseek');
    const [modelName, setModelName] = useState(model?.modelName || '');
    const [modelCode, setModelCode] = useState(model?.modelCode || '');
    const [apiKey, setApiKey] = useState('');
    const [baseUrl, setBaseUrl] = useState(model?.baseUrl || '');
    const [temperature, setTemperature] = useState(model?.temperature || 0.7);
    const [timeout, setTimeout] = useState(model?.timeout || 30);
    // 高级参数
    const [topP, setTopP] = useState<number | undefined>(model?.topP);
    const [maxTokens, setMaxTokens] = useState<number | undefined>(model?.maxTokens);
    const [topK, setTopK] = useState<number | undefined>(model?.topK);

    // 获取当前提供商的参数配置
    const params = PROVIDER_PARAMS[provider] || PROVIDER_PARAMS.custom;

    // 提供商改变时更新默认 baseUrl
    useEffect(() => {
        if (!isEdit) {
            const providerInfo = PROVIDERS.find((p) => p.value === provider);
            setBaseUrl(providerInfo?.defaultBaseUrl || '');
            // 重置高级参数
            setTopP(undefined);
            setMaxTokens(undefined);
            setTopK(undefined);
        }
    }, [provider, isEdit]);

    // 测试连接
    async function handleTest() {
        if (!apiKey) {
            alert('请先填写 API Key');
            return;
        }
        setTesting(true);
        setTestResult(null);
        try {
            const payload: UserModelTestPayload = {
                provider,
                modelCode: modelCode || MODEL_PRESETS[provider]?.[0] || 'gpt-4',
                apiKey,
                baseUrl: baseUrl || undefined,
            };
            const result = await testUserModel(payload);
            setTestResult(result);
        } catch (e) {
            setTestResult({ success: false, message: (e as Error).message });
        } finally {
            setTesting(false);
        }
    }

    // 保存
    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!modelName || !modelCode || (!isEdit && !apiKey)) {
            alert('请填写必填项');
            return;
        }
        if (params.baseUrlRequired && !baseUrl) {
            alert('Custom 提供商必须填写 Base URL');
            return;
        }

        setLoading(true);
        try {
            await onSave({
                modelName,
                provider,
                modelCode,
                apiKey: apiKey || (undefined as unknown as string),
                baseUrl: baseUrl || undefined,
                temperature,
                timeout: params.timeout ? timeout : undefined,
                topP: params.topP ? topP : undefined,
                maxTokens: params.maxTokens ? maxTokens : undefined,
                topK: params.topK ? topK : undefined,
            });
        } catch (e) {
            alert('保存失败: ' + (e as Error).message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        >
            <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="w-full max-w-xl rounded-2xl border p-6 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
                style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--background))' }}
            >
                {/* 标题 */}
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold">{isEdit ? '编辑模型' : '新建模型'}</h2>
                    <button
                        type="button"
                        onClick={onClose}
                        className="p-2 rounded-xl hover:bg-surface-highlight/20 transition-all text-muted hover:text-foreground"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* 表单 */}
                <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-auto custom-scrollbar">
                    {/* 提供商 */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted">AI Provider</label>
                        <select
                            value={provider}
                            onChange={(e) => setProvider(e.target.value)}
                            className="w-full px-4 py-2 rounded-xl border text-foreground focus:outline-none focus:border-primary appearance-none transition-all"
                            style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                        >
                            {PROVIDERS.map((p) => (
                                <option key={p.value} value={p.value} className="bg-surface text-foreground">
                                    {p.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 模型名称 */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted">Display Designation *</label>
                        <input
                            type="text"
                            value={modelName}
                            onChange={(e) => setModelName(e.target.value)}
                            placeholder="e.g. My GPT-4"
                            className="w-full px-4 py-2 rounded-xl border text-foreground placeholder:text-muted/50 focus:outline-none focus:border-primary transition-all"
                            required
                            style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                        />
                    </div>

                    {/* 模型编码 */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted">Protocol Identifier *</label>
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={modelCode}
                                onChange={(e) => setModelCode(e.target.value)}
                                placeholder="e.g. gpt-4o"
                                className="flex-1 px-4 py-2 rounded-xl border text-foreground text-sm placeholder:text-muted/50 focus:outline-none focus:border-primary transition-all"
                                style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                required
                            />
                            {MODEL_PRESETS[provider]?.length > 0 && (
                                <select
                                    value=""
                                    onChange={(e) => e.target.value && setModelCode(e.target.value)}
                                    className="px-4 py-3.5 rounded-2xl bg-surface-highlight/60 border border-border/10 text-muted hover:text-foreground text-xs appearance-none transition-all"
                                >
                                    <option value="" className="bg-surface text-foreground">PRESETS</option>
                                    {MODEL_PRESETS[provider].map((m) => (
                                        <option key={m} value={m} className="bg-surface text-foreground">
                                            {m}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>
                    </div>

                    {/* API Key */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-muted">
                            Access Tokens {isEdit ? '(encrypted)' : '*'}
                        </label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder={isEdit ? '••••••••••••••••' : 'Enter Secret Key'}
                            className="w-full px-4 py-2 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all placeholder:text-muted/50"
                        />
                    </div>

                    {/* Base URL */}
                    {(params.baseUrl || params.baseUrlRequired) && (
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted">
                                Gateway URL {params.baseUrlRequired && '*'}
                            </label>
                            <input
                                type="text"
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                placeholder="e.g. https://api.openai.com/v1"
                                className="w-full px-4 py-2 rounded-xl border text-foreground text-xs focus:outline-none focus:border-primary transition-all placeholder:text-muted/50"
                                style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                            />
                        </div>
                    )}

                    {/* 高级参数折叠区域 */}
                    <div className="pt-4 border-t border-border/10">
                        {/* We could add a collapse toggle here, but for now let's show them spread out or compact */}
                        <div className="text-[10px] font-black text-muted uppercase tracking-widest mb-4">Hyperparameters</div>

                        <div className="grid grid-cols-2 gap-4">
                            {/* Temperature */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted">Temperature</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="2"
                                    value={temperature}
                                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                    className="w-full px-4 py-2.5 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all"
                                    style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                />
                            </div>

                            {params.timeout && (
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">Timeout (s)</label>
                                    <input
                                        type="number"
                                        value={timeout}
                                        onChange={(e) => setTimeout(parseInt(e.target.value))}
                                    style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                        className="w-full px-4 py-2.5 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all"
                                    />
                                </div>
                            )}

                            {params.maxTokens && (
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">Max Tokens</label>
                                    <input
                                        type="number"
                                        value={maxTokens || ''}
                                        onChange={(e) => setMaxTokens(e.target.value ? parseInt(e.target.value) : undefined)}
                                    style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                        placeholder="Default"
                                        className="w-full px-4 py-2.5 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all placeholder:text-muted/50"
                                    />
                                </div>
                            )}

                            {params.topP && (
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">Top P</label>
                                    <input
                                        type="number"
                                        step="0.05"
                                        value={topP || ''}
                                    style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                        onChange={(e) => setTopP(e.target.value ? parseFloat(e.target.value) : undefined)}
                                        placeholder="Default"
                                        className="w-full px-4 py-2.5 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all placeholder:text-muted/50"
                                    />
                                </div>
                            )}

                            {params.topK && (
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">Top K</label>
                                    <input
                                        type="number"
                                    style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                        value={topK || ''}
                                        onChange={(e) => setTopK(e.target.value ? parseInt(e.target.value) : undefined)}
                                        placeholder="Default"
                                        className="w-full px-4 py-2.5 rounded-xl border text-foreground focus:outline-none focus:border-primary transition-all placeholder:text-muted/50"
                                    />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-2">
                        <button
                            type="button"
                            onClick={handleTest}
                            disabled={testing || !apiKey}
                            className="px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
                            style={{ backgroundColor: 'rgb(var(--surface-container-high))' }}
                        >
                            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                            测试连接
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-4 py-2 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                            保存
                        </button>
                    </div>

                    {/* Test Result */}
                    <AnimatePresence>
                        {testResult && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className={clsx(
                                    "overflow-hidden rounded-xl border border-dashed text-xs p-4",
                                    testResult.success
                                        ? "bg-green-500/10 border-green-500/30 text-green-500"
                                        : "bg-red-500/10 border-red-500/30 text-red-500"
                                )}
                            >
                                <div className="flex items-start gap-2">
                                    {testResult.success ? <CheckCircle className="w-4 h-4 flex-shrink-0" /> : <XCircle className="w-4 h-4 flex-shrink-0" />}
                                    <div className="break-all">{testResult.message}</div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </form>
            </motion.div>
        </motion.div>
    );
}
