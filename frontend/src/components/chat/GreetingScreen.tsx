/**
 * 欢迎界面组件
 *
 * 显示欢迎信息和建议卡片，帮助用户快速开始对话
 */
import { Compass, Lightbulb, Code, Pencil, Sparkles, type LucideIcon } from 'lucide-react';
import { motion } from 'framer-motion';

/** 建议卡片属性 */
interface SuggestionCardProps {
  /** 图标组件 */
  icon: LucideIcon;
  /** 建议文本 */
  text: string;
  /** 点击回调 */
  onClick: () => void;
  /** 动画延迟（索引） */
  delay?: number;
  /** 图标颜色类名 */
  colorClass?: string;
}

/**
 * 建议卡片组件
 *
 * 显示单个建议，支持点击触发对话
 */
function SuggestionCard({
  icon: Icon,
  text,
  onClick,
  delay = 0,
  colorClass = 'text-indigo-500',
}: SuggestionCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.05, duration: 0.4 }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="flex flex-col justify-between p-4 h-40 text-left group relative overflow-hidden bg-surface-container rounded-2xl border border-border/60 hover:border-border hover:shadow-lg transition-all duration-300"
      aria-label={text}
    >
      {/* 悬停渐变背景 */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent to-surface-highlight/30 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      {/* 建议文本 */}
      <span className="text-foreground/80 font-medium text-[15px] leading-relaxed relative z-10 group-hover:text-foreground transition-colors">
        {text}
      </span>

      {/* 图标 */}
      <div className="self-end relative z-10 mt-auto">
        <div className="p-2 rounded-xl bg-surface-highlight/50 group-hover:bg-surface-highlight transition-colors duration-300">
          <Icon className={`w-5 h-5 ${colorClass}`} />
        </div>
      </div>
    </motion.button>
  );
}

/** 默认建议列表 */
const DEFAULT_SUGGESTIONS = [
  {
    icon: Compass,
    text: 'Plan a trip to explore hidden gems in Kyoto',
    colorClass: 'text-teal-500',
  },
  {
    icon: Lightbulb,
    text: 'Brainstorm catchy taglines for a coffee brand',
    colorClass: 'text-amber-500',
  },
  {
    icon: Code,
    text: 'Explain how React useEffect works with examples',
    colorClass: 'text-indigo-500',
  },
  {
    icon: Pencil,
    text: 'Write a polite email declining a job offer',
    colorClass: 'text-rose-500',
  },
];

/** 欢迎界面属性 */
export interface GreetingScreenProps {
  /** 用户名 */
  userName: string;
  /** 点击建议回调 */
  onSuggestionClick: (text: string) => void;
  /** 自定义建议列表（可选） */
  suggestions?: typeof DEFAULT_SUGGESTIONS;
}

/**
 * 欢迎界面组件
 *
 * 在没有选中会话或会话为空时显示
 */
export function GreetingScreen({
  userName,
  onSuggestionClick,
  suggestions = DEFAULT_SUGGESTIONS,
}: GreetingScreenProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-5xl mx-auto w-full min-h-[60vh]">
      {/* 欢迎标题区域 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="mb-16 text-center w-full relative z-10"
      >
        {/* Logo 图标 */}
        <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-border flex items-center justify-center mx-auto mb-6 shadow-sm">
          <Sparkles className="w-8 h-8 text-primary" />
        </div>

        {/* 欢迎文字 */}
        <h1 className="text-4xl md:text-5xl font-semibold mb-3 tracking-tight text-foreground">
          Welcome back, {userName}
        </h1>
        <p className="text-xl text-muted font-light">How can I help you today?</p>
      </motion.div>

      {/* 建议卡片网格 */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full relative z-10"
        role="list"
        aria-label="对话建议"
      >
        {suggestions.map((suggestion, index) => (
          <SuggestionCard
            key={suggestion.text}
            icon={suggestion.icon}
            text={suggestion.text}
            onClick={() => onSuggestionClick(suggestion.text)}
            delay={index + 1}
            colorClass={suggestion.colorClass}
          />
        ))}
      </div>
    </div>
  );
}
