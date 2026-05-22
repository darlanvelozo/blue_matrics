"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Brain,
  CreditCard,
  LayoutDashboard,
  Package,
  Plug,
  Receipt,
  RefreshCw,
  Settings,
  ShoppingCart,
  Target,
  Users,
  Wallet,
  X,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

const items = [
  { href: "/app", label: "Visão geral", icon: LayoutDashboard, section: null },
  { href: "/app/dashboards/executivo", label: "Executivo", icon: BarChart3, section: "Dashboards" },
  { href: "/app/dashboards/financeiro", label: "Financeiro", icon: Wallet, section: "Dashboards" },
  { href: "/app/dashboards/comercial", label: "Comercial", icon: ShoppingCart, section: "Dashboards" },
  { href: "/app/insights", label: "Insights", icon: Brain, section: "Dashboards" },
  { href: "/app/goals", label: "Metas", icon: Target, section: "Dashboards" },
  { href: "/app/sales", label: "Vendas", icon: Receipt, section: "Dados" },
  { href: "/app/customers", label: "Clientes", icon: Users, section: "Dados" },
  { href: "/app/products", label: "Produtos", icon: Package, section: "Dados" },
  { href: "/app/integrations", label: "Integrações", icon: Plug, section: "Sistema" },
  { href: "/app/sync", label: "Sincronização", icon: RefreshCw, section: "Sistema" },
  { href: "/app/billing", label: "Assinatura", icon: CreditCard, section: "Sistema" },
  { href: "/app/settings", label: "Configurações", icon: Settings, section: "Sistema" },
];

export function AppSidebar({
  mobileOpen = false,
  onCloseMobile,
}: {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}) {
  const pathname = usePathname();

  // Fecha o drawer ao navegar (mobile)
  useEffect(() => {
    onCloseMobile?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Trava scroll do body quando drawer aberto
  useEffect(() => {
    if (!mobileOpen) return;
    const orig = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = orig;
    };
  }, [mobileOpen]);

  return (
    <>
      {/* Overlay mobile */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onCloseMobile}
          aria-label="Fechar menu"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 shrink-0 transform border-r border-[color:var(--border)] bg-[color:var(--card)] transition-transform duration-200",
          "md:relative md:z-auto md:flex md:translate-x-0 md:flex-col",
          mobileOpen ? "translate-x-0 flex flex-col" : "-translate-x-full hidden md:flex",
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-[color:var(--border)] px-4">
          <Logo href="/app" />
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-md p-1 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)] md:hidden"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {items.map((it, idx) => {
            const Icon = it.icon;
            const active = pathname === it.href;
            const prevSection = idx > 0 ? items[idx - 1].section : null;
            const showSectionHeader = it.section && it.section !== prevSection;
            return (
              <div key={it.href}>
                {showSectionHeader && (
                  <p className="mb-1 mt-3 px-3 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--muted-foreground)]/70">
                    {it.section}
                  </p>
                )}
                <Link
                  href={it.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-[color:var(--accent)] text-[color:var(--accent-foreground)]"
                      : "text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)] hover:text-[color:var(--accent-foreground)]",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {it.label}
                </Link>
              </div>
            );
          })}
        </nav>
        <div className="border-t border-[color:var(--border)] p-3 text-xs text-[color:var(--muted-foreground)]">
          <p>BlueMetrics v0.11</p>
        </div>
      </aside>
    </>
  );
}
