/**
 * 主题配置文件
 * 
 * 定义应用支持的主题颜色方案
 */

/** 明暗模式类型 */
export type ThemeMode = 'light' | 'dark' | 'system';

/** 强调色主题类型 */
export type AccentColor = 'blue' | 'purple' | 'teal' | 'orange' | 'pink';

/**
 * 主题颜色配置接口
 */
interface ThemeColors {
  /** 主色（亮色模式） */
  light: {
    primary: string;
    secondary: string;
    gradient: string;
    gradientHover: string;
  };
  /** 主色（暗色模式） */
  dark: {
    primary: string;
    secondary: string;
    gradient: string;
    gradientHover: string;
  };
}

/**
 * 主题颜色配置
 * 每个主题包含亮色和暗色两套配色方案
 */
export const ACCENT_COLORS: Record<AccentColor, ThemeColors> = {
  /** 蓝色主题 - Google 蓝 */
  blue: {
    light: {
      primary: '#1a73e8',
      secondary: '#34a853',
      gradient: 'linear-gradient(135deg, #4285f4 0%, #1a73e8 100%)',
      gradientHover: 'linear-gradient(135deg, #1a73e8 0%, #4285f4 100%)',
    },
    dark: {
      primary: '#8ab4f8',
      secondary: '#81c995',
      gradient: 'linear-gradient(135deg, #8ab4f8 0%, #669df6 100%)',
      gradientHover: 'linear-gradient(135deg, #669df6 0%, #8ab4f8 100%)',
    },
  },
  /** 紫色主题 */
  purple: {
    light: {
      primary: '#9334e6',
      secondary: '#7c3aed',
      gradient: 'linear-gradient(135deg, #a855f7 0%, #9334e6 100%)',
      gradientHover: 'linear-gradient(135deg, #9334e6 0%, #a855f7 100%)',
    },
    dark: {
      primary: '#c58af9',
      secondary: '#a78bfa',
      gradient: 'linear-gradient(135deg, #c58af9 0%, #a855f7 100%)',
      gradientHover: 'linear-gradient(135deg, #a855f7 0%, #c58af9 100%)',
    },
  },
  /** 青绿主题 */
  teal: {
    light: {
      primary: '#009688',
      secondary: '#00897b',
      gradient: 'linear-gradient(135deg, #26a69a 0%, #009688 100%)',
      gradientHover: 'linear-gradient(135deg, #009688 0%, #26a69a 100%)',
    },
    dark: {
      primary: '#4db6ac',
      secondary: '#80cbc4',
      gradient: 'linear-gradient(135deg, #4db6ac 0%, #26a69a 100%)',
      gradientHover: 'linear-gradient(135deg, #26a69a 0%, #4db6ac 100%)',
    },
  },
  /** 橙色主题 */
  orange: {
    light: {
      primary: '#f57c00',
      secondary: '#ff9800',
      gradient: 'linear-gradient(135deg, #ffa726 0%, #f57c00 100%)',
      gradientHover: 'linear-gradient(135deg, #f57c00 0%, #ffa726 100%)',
    },
    dark: {
      primary: '#ffb74d',
      secondary: '#ffcc80',
      gradient: 'linear-gradient(135deg, #ffb74d 0%, #ffa726 100%)',
      gradientHover: 'linear-gradient(135deg, #ffa726 0%, #ffb74d 100%)',
    },
  },
  /** 粉色主题 */
  pink: {
    light: {
      primary: '#e91e63',
      secondary: '#f06292',
      gradient: 'linear-gradient(135deg, #f06292 0%, #e91e63 100%)',
      gradientHover: 'linear-gradient(135deg, #e91e63 0%, #f06292 100%)',
    },
    dark: {
      primary: '#f48fb1',
      secondary: '#f8bbd0',
      gradient: 'linear-gradient(135deg, #f48fb1 0%, #f06292 100%)',
      gradientHover: 'linear-gradient(135deg, #f06292 0%, #f48fb1 100%)',
    },
  },
};

/**
 * 主题模式选项配置
 */
export const THEME_MODE_OPTIONS: { value: ThemeMode; label: string; icon: string }[] = [
  { value: 'light', label: '亮色', icon: '☀️' },
  { value: 'dark', label: '暗色', icon: '🌙' },
  { value: 'system', label: '跟随系统', icon: '💻' },
];

/**
 * 强调色选项配置
 */
export const ACCENT_COLOR_OPTIONS: { value: AccentColor; label: string; color: string }[] = [
  { value: 'blue', label: '蓝色', color: '#1a73e8' },
  { value: 'purple', label: '紫色', color: '#9334e6' },
  { value: 'teal', label: '青绿', color: '#009688' },
  { value: 'orange', label: '橙色', color: '#f57c00' },
  { value: 'pink', label: '粉色', color: '#e91e63' },
];

/** 主题皮肤类型 (与 uiStore 中的 ThemeSkin 保持一致) */
export type ThemeSkin = 'default' | 'rosepine' | 'rosepine-dawn';

/**
 * 主题皮肤选项配置
 * 借鉴 Open WebUI 的主题系统
 */
export const THEME_SKIN_OPTIONS: { value: ThemeSkin; label: string; preview: string; description: string }[] = [
  { value: 'default', label: '默认', preview: '#171717', description: '经典深灰主题' },
  { value: 'rosepine', label: 'Rose Pine', preview: '#191724', description: '优雅的深色主题' },
  { value: 'rosepine-dawn', label: 'Rose Pine Dawn', preview: '#faf4ed', description: '温暖的浅色主题' },
];
