"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Brain,
  CreditCard,
  LayoutDashboard,
  Plug,
  RefreshCw,
  Settings,
  ShoppingCart,
  Wallet,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

const items = [
  { href: "/app", label: "Visão geral", icon: LayoutDashboard },
  { href: "/app/dashboards/executivo", label: "Executivo", icon: BarChart3 },
  { href: "/app/dashboards/financeiro", label: "Financeiro", icon: Wallet },
  { href: "/app/dashboards/comercial", label: "Comercial", icon: ShoppingCart },
  { href: "/app/insights", label: "Insights", icon: Brain },
  { href: "/app/integrations", label: "Integrações", icon: Plug },
  { href: "/app/sync", label: "Sincronização", icon: RefreshCw },
  { href: "/app/billing", label: "Assinatura", icon: CreditCard },
  { href: "/app/settings", label: "Configurações", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-64 shrink-0 border-r border-[color:var(--border)] bg-[color:var(--card)] md:flex md:flex-col">
      <div className="flex h-16 items-center border-b border-[color:var(--border)] px-4">
        <Logo href="/app" />
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {items.map((it) => {
          const Icon = it.icon;
          const active = pathname === it.href;
          return (
            <Link
              key={it.href}
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
          );
        })}
      </nav>
      <div className="border-t border-[color:var(--border)] p-3 text-xs text-[color:var(--muted-foreground)]">
        <p>BlueMetrics v0.1</p>
      </div>
    </aside>
  );
}
