"use client";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PaginationMeta } from "@/lib/explorer";

export function Pagination({
  meta,
  onChange,
}: {
  meta: PaginationMeta;
  onChange: (page: number) => void;
}) {
  if (meta.total_pages <= 1) return null;
  const start = (meta.page - 1) * meta.page_size + 1;
  const end = Math.min(meta.page * meta.page_size, meta.total);
  return (
    <div className="flex items-center justify-between gap-2 text-xs text-[color:var(--muted-foreground)]">
      <p>
        {start}–{end} de {meta.total}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(meta.page - 1)}
          disabled={meta.page <= 1}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>
        <span className="px-2">
          Página <strong className="text-[color:var(--foreground)]">{meta.page}</strong> de{" "}
          {meta.total_pages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(meta.page + 1)}
          disabled={meta.page >= meta.total_pages}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
