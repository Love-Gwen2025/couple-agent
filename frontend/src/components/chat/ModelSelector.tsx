/**
 * 模型选择器组件
 *
 * 功能：
 * 1. 显示可用模型下拉列表
 * 2. 支持模型切换（用 id 唯一标识）
 */
import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, Bot, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, useModelStore } from '../../store';
import { getModels } from '../../api';
import clsx from 'clsx';

export function ModelSelector() {
  // 认证状态
  const { token } = useAuthStore();

  // 模型状态（使用 currentModelId 作为唯一标识）
  const { models, currentModelId, setModels, setCurrentModelCode, setCurrentModelId } =
    useModelStore();
  const [isOpen, setIsOpen] = useState(false);

  const loadModels = useCallback(async () => {
    try {
      const data = await getModels();
      setModels(data);
      // 如果没有选中的模型，设置默认模型
      if (currentModelId === null && data.length > 0) {
        const defaultModel = data.find((m) => m.isDefault) || data[0];
        setCurrentModelCode(defaultModel.modelCode);
        // 系统默认模型 id=0 存为 '0'，用户模型存实际 id
        setCurrentModelId(String(defaultModel.id));
      }
    } catch (error) {
      console.error('加载模型列表失败:', error);
    }
  }, [currentModelId, setCurrentModelCode, setCurrentModelId, setModels]);

  useEffect(() => {
    if (token) void loadModels();
  }, [token, loadModels]);

  // 通过 id 匹配当前选中的模型
  const currentModel = models.find((m) => String(m.id) === currentModelId);

  if (models.length === 0) return null;

  return (
    <div className="relative z-50">
      <button
        className={clsx(
          "flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border/50 transition-all duration-200 text-sm font-medium",
          isOpen ? "bg-surface-highlight text-primary ring-2 ring-primary/10" : "bg-surface/50 hover:bg-surface-highlight text-muted hover:text-foreground"
        )}
        onClick={() => setIsOpen(!isOpen)}
      >
        <Bot className={clsx("w-4 h-4", isOpen ? "text-primary" : "text-muted")} />
        <span>{currentModel?.modelName || '选择模型'}</span>
        <ChevronDown
          className={clsx(
            'w-3.5 h-3.5 transition-transform duration-200 opacity-50',
            isOpen && 'rotate-180 opacity-100'
          )}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 5, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full right-0 mt-2 w-56 bg-surface/90 backdrop-blur-xl border border-border rounded-xl shadow-2xl z-20 overflow-hidden p-1.5"
            >
              <div className="px-2 py-1.5 text-xs font-semibold text-muted/50 uppercase tracking-wider">
                Available Models
              </div>
              {models.map((model) => {
                // 用 id 字符串做匹配
                const isSelected = String(model.id) === currentModelId;
                return (
                  <button
                    key={model.id}
                    className={clsx(
                      'w-full px-3 py-2.5 text-left text-sm rounded-lg transition-all flex items-center justify-between group',
                      isSelected
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-surface-highlight text-muted hover:text-foreground'
                    )}
                    onClick={() => {
                      setCurrentModelCode(model.modelCode);
                      // 统一用字符串存储（系统模型 '0'，用户模型实际 id）
                      setCurrentModelId(String(model.id));
                      setIsOpen(false);
                    }}
                  >
                    <span className="font-medium">{model.modelName}</span>
                    {isSelected && (
                      <Check className="w-4 h-4 text-primary" />
                    )}
                  </button>
                );
              })}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
