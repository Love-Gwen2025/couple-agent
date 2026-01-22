/**
 * 主题设置面板组件
 *
 * 提供明暗模式切换和彩色主题选择功能
 * 面板定位在触发按钮上方，使用不透明背景
 */
import { Sun, Moon, Monitor, X } from 'lucide-react';
import { useUIStore } from '../../store';
import {
    THEME_MODE_OPTIONS,
    type ThemeMode,
} from '../../config/themes';
import clsx from 'clsx';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/** 锚点位置信息 */
interface AnchorRect {
    top: number;
    left: number;
    width: number;
    height: number;
}

/** 组件属性 */
interface ThemePanelProps {
    /** 是否显示面板 */
    isOpen: boolean;
    /** 关闭面板回调 */
    onClose: () => void;
    /** 触发按钮的位置信息 */
    anchorRect?: AnchorRect | null;
}

/**
 * 获取主题模式图标组件
 */
function getThemeModeIcon(mode: ThemeMode) {
    switch (mode) {
        case 'light':
            return <Sun className="w-4 h-4" />;
        case 'dark':
            return <Moon className="w-4 h-4" />;
        case 'system':
            return <Monitor className="w-4 h-4" />;
    }
}

/**
 * 主题设置面板组件
 * 定位在触发按钮上方，不透明背景
 */
export function ThemePanel({ isOpen, onClose, anchorRect }: ThemePanelProps) {
    const { themeMode, setThemeMode } = useUIStore();
    const panelRef = useRef<HTMLDivElement>(null);
    const [panelStyle, setPanelStyle] = useState<React.CSSProperties>({});

    // 根据锚点位置计算面板位置
    useEffect(() => {
        if (!isOpen || !anchorRect) {
            // 没有锚点位置时，使用默认左下角定位
            setPanelStyle({
                position: 'fixed',
                bottom: '16px',
                left: '16px',
            });
            return;
        }

        // 面板宽度
        const panelWidth = 280;
        // 面板高度（预估值，实际会根据内容变化）
        const panelHeight = 160;
        // 间距
        const gap = 12;

        // 计算面板位置：在按钮上方，左对齐
        let left = anchorRect.left;
        let bottom = window.innerHeight - anchorRect.top + gap;

        // 确保面板不超出屏幕右边界
        if (left + panelWidth > window.innerWidth - 16) {
            left = window.innerWidth - panelWidth - 16;
        }

        // 确保面板不超出屏幕左边界
        if (left < 16) {
            left = 16;
        }

        // 如果上方空间不足，显示在按钮下方
        if (anchorRect.top - panelHeight - gap < 16) {
            bottom = window.innerHeight - anchorRect.top - anchorRect.height - panelHeight - gap;
        }

        setPanelStyle({
            position: 'fixed',
            bottom: `${bottom}px`,
            left: `${left}px`,
        });
    }, [isOpen, anchorRect]);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 遮罩层 - 透明，只用于点击关闭 */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="fixed inset-0 z-40"
                        onClick={onClose}
                    />

                    {/* 设置面板 - 不透明背景 */}
                    <motion.div
                        ref={panelRef}
                        initial={{ opacity: 0, y: 12, scale: 0.96 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 12, scale: 0.96 }}
                        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
                        style={panelStyle}
                        className="w-72 glass-premium dual-stroke shadow-premium z-50 overflow-hidden rounded-[28px] bg-surface/95"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="theme-panel-title"
                    >
                        {/* 标题栏 */}
                        <div className="flex items-center justify-between px-5 py-4 border-b border-border/10 bg-surface/40">
                            <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] italic" id="theme-panel-title">Visual Kernel</h3>
                            <button
                                onClick={onClose}
                                className="p-1.5 rounded-xl hover:bg-white/10 transition-all active:scale-90"
                                aria-label="关闭主题设置"
                            >
                                <X className="w-3.5 h-3.5 text-gray-500" />
                            </button>
                        </div>

                        <div className="p-5 space-y-6">
                            {/* 明暗模式切换 */}
                            <div>
                                <label className="block text-[10px] font-black text-gray-500 uppercase tracking-widest mb-3 ml-1">
                                    Luminance level
                                </label>
                                <div className="flex gap-2 p-1.5 rounded-2xl bg-surface/40 border border-border/10 shadow-inner">
                                    {THEME_MODE_OPTIONS.map((option) => (
                                        <motion.button
                                            key={option.value}
                                            whileTap={{ scale: 0.95 }}
                                            onClick={() => setThemeMode(option.value)}
                                            className={clsx(
                                                'flex-1 flex flex-col items-center justify-center gap-1.5 py-3 rounded-xl text-[10px] font-bold transition-all uppercase tracking-tighter',
                                                themeMode === option.value
                                                    ? 'bg-gray-100 dark:bg-gray-800 text-foreground border border-gray-200 dark:border-gray-700'
                                                    : 'text-muted hover:text-foreground'
                                            )}
                                            role="switch"
                                            aria-checked={themeMode === option.value}
                                            aria-label={`切换到${option.label === 'Auto' ? '跟随系统' : option.label}模式`}
                                        >
                                            <div className={clsx(
                                                'p-1.5 rounded-lg transition-colors',
                                                themeMode === option.value ? 'bg-gray-200 dark:bg-gray-700 text-foreground' : 'text-gray-600'
                                            )}>
                                                {getThemeModeIcon(option.value)}
                                            </div>
                                            <span>{option.label === 'Auto' ? 'System' : option.label}</span>
                                        </motion.button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
