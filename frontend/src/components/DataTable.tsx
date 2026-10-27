import { useState } from "react";
import {
  ColumnDef, flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, SortingState, useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import { EmptyState, LoadingBlock } from "./ui";

interface Props<T> {
  data: T[];
  columns: ColumnDef<T, any>[]; // eslint-disable-line @typescript-eslint/no-explicit-any
  loading?: boolean;
  emptyTitle?: string;
  emptyText?: string;
  /** Server-side pagination: total rows and the current page (1-based). */
  server?: { total: number; page: number; pageSize: number; onPage: (page: number) => void };
  pageSize?: number;
  renderExpanded?: (row: T) => React.ReactNode;
  isExpanded?: (row: T) => boolean;
  onRowClick?: (row: T) => void;
}

export default function DataTable<T>({
  data, columns, loading, emptyTitle = "Nothing here yet", emptyText, server, pageSize = 25, renderExpanded, isExpanded, onRowClick,
}: Props<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    ...(server ? {} : { getPaginationRowModel: getPaginationRowModel() }),
    initialState: { pagination: { pageSize } },
  });

  const page = server ? server.page : table.getState().pagination.pageIndex + 1;
  const pageCount = server ? Math.max(1, Math.ceil(server.total / server.pageSize)) : Math.max(1, table.getPageCount());
  const total = server ? server.total : data.length;
  const go = (p: number) => (server ? server.onPage(p) : table.setPageIndex(p - 1));

  if (loading && data.length === 0) return <LoadingBlock />;
  if (!loading && data.length === 0) return <EmptyState title={emptyTitle}>{emptyText}</EmptyState>;

  return (
    <div className={loading ? "opacity-60 transition" : "transition"}>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                {hg.headers.map((h) => {
                  const sorted = h.column.getIsSorted();
                  return (
                    <th key={h.id} className="whitespace-nowrap px-3 py-2 font-medium">
                      {h.isPlaceholder ? null : h.column.getCanSort() ? (
                        <button className="inline-flex items-center gap-1 hover:text-navy" onClick={h.column.getToggleSortingHandler()}>
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {sorted === "asc" ? <ArrowUp size={12} /> : sorted === "desc" ? <ArrowDown size={12} /> : null}
                        </button>
                      ) : (
                        flexRender(h.column.columnDef.header, h.getContext())
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <FragmentRow key={row.id}>
                <tr
                  className={`border-b border-slate-100 align-top ${onRowClick ? "cursor-pointer hover:bg-slate-50" : ""}`}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
                {renderExpanded && isExpanded?.(row.original) && (
                  <tr className="border-b border-slate-100 bg-slate-50/60">
                    <td colSpan={row.getVisibleCells().length} className="px-3 py-4">
                      {renderExpanded(row.original)}
                    </td>
                  </tr>
                )}
              </FragmentRow>
            ))}
          </tbody>
        </table>
      </div>
      {pageCount > 1 || total > 10 ? (
        <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
          <span>
            {total} row{total === 1 ? "" : "s"} · page {page} of {pageCount}
          </span>
          <div className="flex gap-1">
            <button className="rounded border px-2 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => go(page - 1)} aria-label="Previous page">
              <ChevronLeft size={14} />
            </button>
            <button className="rounded border px-2 py-1 disabled:opacity-40" disabled={page >= pageCount} onClick={() => go(page + 1)} aria-label="Next page">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function FragmentRow({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
