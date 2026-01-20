/**
 * 存储迁移工具
 *
 * 从旧版单一 Store 迁移到新版拆分 Store
 */

// 存储版本号
const STORAGE_VERSION = 2;
const VERSION_KEY = 'storage-version';
const OLD_STORAGE_KEY = 'app-storage';

/** 旧版状态结构 */
interface OldAppState {
  token: string | null;
  user: { id: number; userCode: string; userName?: string; avatar?: string } | null;
  currentModelCode: string | null;
  currentModelId: string | null;
  themeMode: 'light' | 'dark' | 'system';
  accentColor: 'blue' | 'purple' | 'teal' | 'orange' | 'pink';
}

/**
 * 检查并执行迁移
 * 在应用启动时调用
 */
export function checkAndMigrate(): void {
  try {
    const currentVersion = localStorage.getItem(VERSION_KEY);

    // 如果版本号已是最新，无需迁移
    if (currentVersion === String(STORAGE_VERSION)) {
      return;
    }

    // 检查是否存在旧版存储
    const oldStorageRaw = localStorage.getItem(OLD_STORAGE_KEY);
    if (!oldStorageRaw) {
      // 没有旧数据，设置版本号并返回
      localStorage.setItem(VERSION_KEY, String(STORAGE_VERSION));
      return;
    }

    // 解析旧数据
    const oldStorage = JSON.parse(oldStorageRaw);
    const oldState: OldAppState = oldStorage.state;

    if (!oldState) {
      localStorage.setItem(VERSION_KEY, String(STORAGE_VERSION));
      return;
    }

    console.log('[Migration] 检测到旧版存储，开始迁移...');

    // 迁移到新 Store
    migrateAuthStore(oldState);
    migrateModelStore(oldState);
    migrateUIStore(oldState);

    // 设置新版本号
    localStorage.setItem(VERSION_KEY, String(STORAGE_VERSION));

    // 保留旧存储作为备份（带有标记）
    localStorage.setItem(`${OLD_STORAGE_KEY}-backup`, oldStorageRaw);

    // 删除旧存储
    localStorage.removeItem(OLD_STORAGE_KEY);

    console.log('[Migration] 迁移完成');
  } catch (error) {
    console.error('[Migration] 迁移失败:', error);
    // 迁移失败时保留旧数据，不影响用户使用
  }
}

/**
 * 迁移认证数据到新 Store
 */
function migrateAuthStore(oldState: OldAppState): void {
  if (oldState.token || oldState.user) {
    const authData = {
      state: {
        token: oldState.token,
        user: oldState.user,
      },
      version: 0,
    };
    localStorage.setItem('auth-storage', JSON.stringify(authData));
    console.log('[Migration] 认证数据已迁移');
  }
}

/**
 * 迁移模型数据到新 Store
 */
function migrateModelStore(oldState: OldAppState): void {
  if (oldState.currentModelCode || oldState.currentModelId) {
    const modelData = {
      state: {
        currentModelCode: oldState.currentModelCode,
        currentModelId: oldState.currentModelId,
      },
      version: 0,
    };
    localStorage.setItem('model-storage', JSON.stringify(modelData));
    console.log('[Migration] 模型数据已迁移');
  }
}

/**
 * 迁移 UI 数据到新 Store
 */
function migrateUIStore(oldState: OldAppState): void {
  if (oldState.themeMode || oldState.accentColor) {
    const uiData = {
      state: {
        themeMode: oldState.themeMode || 'system',
        accentColor: oldState.accentColor || 'blue',
      },
      version: 0,
    };
    localStorage.setItem('ui-storage', JSON.stringify(uiData));
    console.log('[Migration] UI 数据已迁移');
  }
}

/**
 * 回滚迁移（仅用于紧急情况）
 */
export function rollbackMigration(): boolean {
  try {
    const backup = localStorage.getItem(`${OLD_STORAGE_KEY}-backup`);
    if (!backup) {
      console.warn('[Migration] 没有找到备份数据');
      return false;
    }

    // 恢复旧存储
    localStorage.setItem(OLD_STORAGE_KEY, backup);

    // 清除新 Store 数据
    localStorage.removeItem('auth-storage');
    localStorage.removeItem('model-storage');
    localStorage.removeItem('ui-storage');

    // 重置版本号
    localStorage.removeItem(VERSION_KEY);

    console.log('[Migration] 回滚完成');
    return true;
  } catch (error) {
    console.error('[Migration] 回滚失败:', error);
    return false;
  }
}
