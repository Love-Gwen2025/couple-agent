/**
 * 通用分页组件
 * 
 * 支持页码显示、上下翻页、跳转等功能
 */
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface PaginationProps {
    /** 当前页码 (从1开始) */
    current: number;
    /** 每页大小 */
    size: number;
    /** 总记录数 */
    total: number;
    /** 总页数 */
    pages: number;
    /** 页码变化回调 */
    onChange: (page: number) => void;
    /** 是否显示总数 */
    showTotal?: boolean;
    /** 是否显示快速跳转 */
    showQuickJumper?: boolean;
}

export function Pagination({
    current,
    size: _size,  // 保留用于接口完整性
    total,
    pages,
    onChange,
    showTotal = true,
    showQuickJumper = false,
}: PaginationProps) {
    // 如果只有一页或没有数据，不显示分页
    if (pages <= 1) return null;

    // 生成页码列表
    const getPageNumbers = (): (number | 'ellipsis')[] => {
        const pageNumbers: (number | 'ellipsis')[] = [];
        const maxVisiblePages = 5; // 最多显示的页码数

        if (pages <= maxVisiblePages + 2) {
            // 页数较少，全部显示
            for (let i = 1; i <= pages; i++) {
                pageNumbers.push(i);
            }
        } else {
            // 页数较多，显示省略号
            pageNumbers.push(1);

            if (current > 3) {
                pageNumbers.push('ellipsis');
            }

            // 当前页附近的页码
            const start = Math.max(2, current - 1);
            const end = Math.min(pages - 1, current + 1);

            for (let i = start; i <= end; i++) {
                pageNumbers.push(i);
            }

            if (current < pages - 2) {
                pageNumbers.push('ellipsis');
            }

            pageNumbers.push(pages);
        }

        return pageNumbers;
    };

    // 处理跳转
    const handleJump = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            const value = parseInt((e.target as HTMLInputElement).value, 10);
            if (!isNaN(value) && value >= 1 && value <= pages) {
                onChange(value);
                (e.target as HTMLInputElement).value = '';
            }
        }
    };

    const pageNumbers = getPageNumbers();

    return (
        <div className="flex items-center justify-between gap-4 px-4 py-3">
            {/* 左侧：总数显示 */}
            {showTotal && (
                <div className="text-sm text-muted">
                    共 <span className="font-medium text-foreground">{total}</span> 条记录
                </div>
            )}

            {/* 右侧：分页控件 */}
            <div className="flex items-center gap-1">
                {/* 首页 */}
                <button
                    onClick={() => onChange(1)}
                    disabled={current === 1}
                    className="p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high"
                    title="首页"
                >
                    <ChevronsLeft className="w-4 h-4" />
                </button>

                {/* 上一页 */}
                <button
                    onClick={() => onChange(current - 1)}
                    disabled={current === 1}
                    className="p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high"
                    title="上一页"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>

                {/* 页码 */}
                {pageNumbers.map((pageNum, index) =>
                    pageNum === 'ellipsis' ? (
                        <span key={`ellipsis-${index}`} className="px-2 text-muted">
                            ...
                        </span>
                    ) : (
                        <button
                            key={pageNum}
                            onClick={() => onChange(pageNum)}
                            className={`min-w-[32px] h-8 px-2 rounded-lg text-sm font-medium transition-colors ${pageNum === current
                                ? 'bg-primary text-primary-foreground'
                                : 'hover:bg-surface-container-high'
                                }`}
                        >
                            {pageNum}
                        </button>
                    )
                )}

                {/* 下一页 */}
                <button
                    onClick={() => onChange(current + 1)}
                    disabled={current === pages}
                    className="p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high"
                    title="下一页"
                >
                    <ChevronRight className="w-4 h-4" />
                </button>

                {/* 末页 */}
                <button
                    onClick={() => onChange(pages)}
                    disabled={current === pages}
                    className="p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high"
                    title="末页"
                >
                    <ChevronsRight className="w-4 h-4" />
                </button>

                {/* 快速跳转 */}
                {showQuickJumper && (
                    <div className="flex items-center gap-1 ml-2 text-sm">
                        <span className="text-muted">跳至</span>
                        <input
                            type="number"
                            min={1}
                            max={pages}
                            onKeyDown={handleJump}
                            className="w-12 h-8 px-2 rounded-lg border text-center text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                            style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--surface))' }}
                        />
                        <span className="text-muted">页</span>
                    </div>
                )}
            </div>
        </div>
    );
}
