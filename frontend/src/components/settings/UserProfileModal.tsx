/**
 * 用户资料设置弹窗组件
 *
 * 包含基础信息、隐私设置、个性外观三个标签页
 */
import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, User, Lock, Camera, Check, Loader2, Edit2,
    Palette,
    Sun, Moon, Monitor
} from 'lucide-react';
import clsx from 'clsx';
import { useAuthStore, useUIStore } from '../../store';
import { uploadAvatar, updateProfile, changePassword } from '../../api/auth';
import { THEME_MODE_OPTIONS } from '../../config/themes';

interface UserProfileModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type TabType = 'basic' | 'privacy' | 'appearance';

export function UserProfileModal({ isOpen, onClose }: UserProfileModalProps) {
    // 认证状态
    const { user, setUser } = useAuthStore();

    // UI 状态
    const { themeMode, setThemeMode } = useUIStore();
    const [activeTab, setActiveTab] = useState<TabType>('basic');
    const [isEditing, setIsEditing] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // 基础信息编辑表单
    const [editForm, setEditForm] = useState({
        userName: user?.userName || '',
        userPhone: '',
        address: '',
    });

    // 密码修改表单
    const [passwordForm, setPasswordForm] = useState({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
    });
    const [isChangingPassword, setIsChangingPassword] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);

    // 处理头像上传
    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        setError(null);
        try {
            const avatarUrl = await uploadAvatar(file);
            if (user) {
                setUser({ ...user, avatar: avatarUrl });
            }
            setSuccess('头像上传成功');
            setTimeout(() => setSuccess(null), 2000);
        } catch {
            setError('头像上传失败');
        } finally {
            setIsLoading(false);
        }
    };

    // 保存基础信息
    const handleSaveProfile = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const updatedUser = await updateProfile({
                userName: editForm.userName || undefined,
                userPhone: editForm.userPhone || undefined,
                address: editForm.address || undefined,
            });
            setUser({ ...user, ...updatedUser });
            setIsEditing(false);
            setSuccess('保存成功');
            setTimeout(() => setSuccess(null), 2000);
        } catch {
            setError('保存失败');
        } finally {
            setIsLoading(false);
        }
    };

    // 修改密码
    const handleChangePassword = async () => {
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            setError('两次输入的新密码不一致');
            return;
        }
        if (passwordForm.newPassword.length < 6) {
            setError('新密码至少需要6位');
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            await changePassword(passwordForm.oldPassword, passwordForm.newPassword);
            setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' });
            setIsChangingPassword(false);
            setSuccess('密码修改成功');
            setTimeout(() => setSuccess(null), 2000);
        } catch {
            setError('旧密码不正确');
        } finally {
            setIsLoading(false);
        }
    };

    const tabs = [
        { id: 'basic' as const, label: '基础信息', icon: User },
        { id: 'privacy' as const, label: '隐私设置', icon: Lock },
        { id: 'appearance' as const, label: '个性外观', icon: Palette },
    ];

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* 遮罩层 */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 z-50"
                    />

                    {/* 弹窗主体 */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.3 }}
                        className="fixed inset-0 flex items-center justify-center z-50 p-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="w-full max-w-2xl shadow-2xl rounded-[32px] overflow-hidden border border-border" style={{ backgroundColor: 'rgb(var(--background))' }}>
                            {/* 标题栏 */}
                            <div className="flex items-center justify-between px-8 py-6 border-b border-border" style={{ backgroundColor: 'rgb(var(--surface-container))' }}>
                                <h2 className="text-xl font-bold tracking-tight text-foreground italic">USER SETTINGS</h2>
                                <button
                                    onClick={onClose}
                                    className="p-2.5 rounded-2xl hover:bg-surface-highlight/50 transition-all active:scale-90"
                                >
                                    <X className="w-5 h-5 text-muted" />
                                </button>
                            </div>

                            <div className="flex min-h-[450px]">
                                {/* 左侧导航 */}
                                <div className="w-56 border-r border-border p-4 space-y-2" style={{ backgroundColor: 'rgb(var(--surface-container))' }}>
                                    {tabs.map((tab) => (
                                        <button
                                            key={tab.id}
                                            onClick={() => {
                                                setActiveTab(tab.id);
                                                setError(null);
                                                setIsEditing(false);
                                                setIsChangingPassword(false);
                                            }}
                                            className={clsx(
                                                'w-full flex items-center gap-3 px-5 py-3.5 rounded-2xl text-sm font-semibold transition-all active:scale-95',
                                                activeTab === tab.id
                                                    ? 'bg-gray-100 dark:bg-gray-800 text-foreground border border-gray-200 dark:border-gray-700'
                                                    : 'text-muted hover:text-foreground hover:bg-surface-highlight/50'
                                            )}
                                        >
                                            <tab.icon className={clsx("w-4 h-4", activeTab === tab.id ? "text-foreground" : "text-muted")} />
                                            {tab.label}
                                        </button>
                                    ))}
                                </div>

                                {/* 右侧内容 */}
                                <div className="flex-1 p-8" style={{ backgroundColor: 'rgb(var(--background))' }}>
                                    {/* 消息提示 */}
                                    {(error || success) && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className={clsx(
                                                'mb-6 px-4 py-3 rounded-2xl text-sm font-medium',
                                                error ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'
                                            )}
                                        >
                                            {error || success}
                                        </motion.div>
                                    )}

                                    {/* 基础信息面板 */}
                                    {activeTab === 'basic' && (
                                        <div className="space-y-8">
                                            {/* 头像 */}
                                            <div className="flex items-center gap-8">
                                                <div className="relative group">
                                                    <div
                                                        onClick={handleAvatarClick}
                                                        className="relative w-24 h-24 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-white text-3xl font-extrabold cursor-pointer border-4 border-surface/50 shadow-2xl overflow-hidden active:scale-95 transition-transform"
                                                    >
                                                        {user?.avatar ? (
                                                            <img src={user.avatar} alt="avatar" className="w-full h-full object-cover" />
                                                        ) : (
                                                            user?.userName?.charAt(0).toUpperCase() || 'U'
                                                        )}
                                                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                                            <Camera className="w-8 h-8 text-white" />
                                                        </div>
                                                    </div>
                                                    <input
                                                        ref={fileInputRef}
                                                        type="file"
                                                        accept="image/jpeg,image/png,image/gif,image/webp"
                                                        onChange={handleAvatarChange}
                                                        className="hidden"
                                                    />
                                                </div>
                                                <div className="space-y-1">
                                                    <div className="text-sm font-bold text-foreground/80 uppercase tracking-widest">Profile Image</div>
                                                    <div className="text-xs text-muted">JPG, PNG, GIF, WebP (Max 5MB)</div>
                                                </div>
                                            </div>

                                            {/* 用户信息 */}
                                            {!isEditing ? (
                                                <div className="space-y-6">
                                                    <div className="flex flex-col gap-2 py-4 border-b border-border/10">
                                                        <span className="text-[10px] font-black text-muted uppercase tracking-widest">Username</span>
                                                        <span className="text-lg font-bold text-foreground">{user?.userName || '-'}</span>
                                                    </div>
                                                    <div className="flex flex-col gap-2 py-4 border-b border-border/10">
                                                        <span className="text-[10px] font-black text-muted uppercase tracking-widest">Registry ID</span>
                                                        <span className="text-lg font-bold text-foreground tracking-tight">{user?.userCode || '-'}</span>
                                                    </div>
                                                    <button
                                                        onClick={() => {
                                                            setIsEditing(true);
                                                            setEditForm({
                                                                userName: user?.userName || '',
                                                                userPhone: '',
                                                                address: '',
                                                            });
                                                        }}
                                                        className="mt-6 px-8 py-3 rounded-2xl text-sm font-bold bg-surface-highlight/20 text-foreground hover:bg-surface-highlight/30 transition-all active:scale-95 flex items-center gap-2"
                                                    >
                                                        <Edit2 className="w-4 h-4 text-foreground" />
                                                        EDIT PROFILE
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="space-y-6">
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">Username</label>
                                                        <input
                                                            type="text"
                                                            value={editForm.userName}
                                                            onChange={(e) => setEditForm({ ...editForm, userName: e.target.value })}
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground font-medium focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all placeholder:text-muted/50"
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">Phone Reference</label>
                                                        <input
                                                            type="text"
                                                            value={editForm.userPhone}
                                                            onChange={(e) => setEditForm({ ...editForm, userPhone: e.target.value })}
                                                            placeholder="Optional"
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground font-medium focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all placeholder:text-muted/50"
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">Geo Location</label>
                                                        <input
                                                            type="text"
                                                            value={editForm.address}
                                                            onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                                                            placeholder="Optional"
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground font-medium focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all placeholder:text-muted/50"
                                                        />
                                                    </div>
                                                    <div className="flex gap-4 mt-10">
                                                        <button
                                                            onClick={() => setIsEditing(false)}
                                                            className="flex-1 px-8 py-3.5 rounded-2xl text-sm font-bold text-muted hover:text-foreground hover:bg-surface-highlight/20 transition-all"
                                                        >
                                                            CANCEL
                                                        </button>
                                                        <button
                                                            onClick={handleSaveProfile}
                                                            disabled={isLoading}
                                                            className="flex-1 px-8 py-3.5 rounded-2xl text-sm font-bold bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                                        >
                                                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                                            SAVE CHANGES
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* 隐私设置面板 */}
                                    {activeTab === 'privacy' && (
                                        <div className="space-y-8">
                                            <div className="flex justify-between items-center py-6 border-b border-border/10">
                                                <div className="space-y-2">
                                                    <div className="text-[10px] font-black text-muted uppercase tracking-widest">Security Protocol</div>
                                                    <div className="text-lg font-bold text-foreground tracking-widest">••••••••</div>
                                                </div>
                                                {!isChangingPassword && (
                                                    <button
                                                        onClick={() => setIsChangingPassword(true)}
                                                        className="px-6 py-3 rounded-2xl text-sm font-bold bg-surface-highlight/20 text-foreground hover:bg-surface-highlight/30 transition-all active:scale-95"
                                                    >
                                                        CHANGE KEY
                                                    </button>
                                                )}
                                            </div>

                                            {isChangingPassword && (
                                                <motion.div
                                                    initial={{ opacity: 0, height: 0 }}
                                                    animate={{ opacity: 1, height: 'auto' }}
                                                    className="space-y-6 pt-4"
                                                >
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">Current Key</label>
                                                        <input
                                                            type="password"
                                                            value={passwordForm.oldPassword}
                                                            onChange={(e) => setPasswordForm({ ...passwordForm, oldPassword: e.target.value })}
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all"
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">New Interface Key</label>
                                                        <input
                                                            type="password"
                                                            value={passwordForm.newPassword}
                                                            onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                                                            placeholder="Min 6 characters"
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all placeholder:text-muted/50"
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[10px] font-black text-muted uppercase tracking-widest ml-1">Confirm New Key</label>
                                                        <input
                                                            type="password"
                                                            value={passwordForm.confirmPassword}
                                                            onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                                                            className="w-full px-5 py-3.5 rounded-2xl bg-surface/40 border border-border/10 text-foreground focus:outline-none focus:border-gray-400 dark:focus:border-gray-500 focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-700 transition-all"
                                                        />
                                                    </div>
                                                    <div className="flex gap-4 mt-10">
                                                        <button
                                                            onClick={() => {
                                                                setIsChangingPassword(false);
                                                                setPasswordForm({ oldPassword: '', newPassword: '', confirmPassword: '' });
                                                                setError(null);
                                                            }}
                                                            className="flex-1 px-8 py-3.5 rounded-2xl text-sm font-bold text-muted hover:text-foreground hover:bg-surface-highlight/20 transition-all"
                                                        >
                                                            CANCEL
                                                        </button>
                                                        <button
                                                            onClick={handleChangePassword}
                                                            disabled={isLoading}
                                                            className="flex-1 px-8 py-3.5 rounded-2xl text-sm font-bold bg-red-600 hover:bg-red-700 text-white active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                                        >
                                                            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                                            UPDATE KEY
                                                        </button>
                                                    </div>
                                                </motion.div>
                                            )}
                                        </div>
                                    )}

                                    {/* 个性外观 (主题设置) */}
                                    {activeTab === 'appearance' && (
                                        <div className="space-y-10 py-4">
                                            <div className="space-y-4">
                                                <div className="space-y-1">
                                                    <div className="text-[10px] font-black text-muted uppercase tracking-[0.3em]">Luminance level calibration</div>
                                                    <div className="text-xs text-muted/80 font-bold uppercase">Select your preferred appearance</div>
                                                </div>
                                                <div className="grid grid-cols-3 gap-4 p-2 bg-surface/40 border border-border/5 rounded-[32px] shadow-inner">
                                                    {THEME_MODE_OPTIONS.map((option) => (
                                                        <motion.button
                                                            key={option.value}
                                                            whileTap={{ scale: 0.95 }}
                                                            onClick={() => setThemeMode(option.value)}
                                                            className={clsx(
                                                                'flex flex-col items-center justify-center gap-3 py-6 rounded-[24px] text-[10px] font-black transition-all uppercase tracking-widest',
                                                                themeMode === option.value
                                                                    ? 'bg-gray-100 dark:bg-gray-800 text-foreground border border-gray-200 dark:border-gray-700'
                                                                    : 'text-muted hover:text-foreground hover:bg-surface-highlight/20'
                                                            )}
                                                        >
                                                            <div className={clsx(
                                                                'p-3 rounded-2xl transition-all group-hover:scale-110',
                                                                themeMode === option.value ? 'bg-gray-200 dark:bg-gray-700 text-foreground' : 'bg-surface-highlight/20 text-muted'
                                                            )}>
                                                                {option.value === 'light' && <Sun className="w-5 h-5" />}
                                                                {option.value === 'dark' && <Moon className="w-5 h-5" />}
                                                                {option.value === 'system' && <Monitor className="w-5 h-5" />}
                                                            </div>
                                                            <span>{option.label === 'Auto' ? 'System' : option.label}</span>
                                                        </motion.button>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="p-6 rounded-[32px] bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
                                                <div className="flex gap-4 items-center">
                                                    <div className="p-3 bg-gray-200 dark:bg-gray-700 rounded-2xl text-foreground">
                                                        <Palette className="w-5 h-5" />
                                                    </div>
                                                    <div className="flex-1 space-y-1">
                                                        <div className="text-[11px] font-black text-foreground uppercase tracking-widest tracking-widest">Experimental Sub-Themes</div>
                                                        <div className="text-[10px] text-muted font-bold uppercase">Dynamic accent color calibration in next kernel update</div>
                                                    </div>
                                                    <div className="text-[9px] font-black text-muted border border-border/10 px-2 py-1 rounded-lg uppercase tracking-widest italic">V4.2.0-STABLE</div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
