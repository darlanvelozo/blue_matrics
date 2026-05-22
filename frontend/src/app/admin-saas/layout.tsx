"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Building2, LayoutDashboard, LogOut, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiError } from "@/lib/api";
import { getMe, logout, type User } from "@/lib/auth";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/admin-saas", label: "Visão geral", icon: LayoutDashboard, exact: true },
  { href: "/admin-saas/tenants", label: "Tenants", icon: Building2, exact: false },
];

export default function AdminSaasLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    getMe()
      .then((u) => {
        if (!u.is_staff) {
          setDenied(true);
        } else {
          setUser(u);
        }
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
        } else {
          setDenied(true);
        }
      });
  }, [router]);

  if (denied) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
        <Shield className="h-10 w-10 text-red-500" />
        <h1 className="text-xl font-bold">Acesso restrito</h1>
        <p className="max-w-sm text-sm text-[color:var(--muted-foreground)]">
          Esta área é restrita a administradores da plataforma BlueMetrics.
        </p>
        <Link href="/app">
          <Button variant="outline">Voltar ao app</Button>
        </Link>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[color:var(--border)] border-t-[color:var(--primary)]" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-red-500/30 bg-red-500/10">
        <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-6 text-xs">
          <span className="inline-flex items-center gap-2 font-semibold text-red-700 dark:text-red-300">
            <Shield className="h-3.5 w-3.5" />
            Admin SaaS — área restrita
          </span>
          <span className="text-red-700/70 dark:text-red-300/70">{user.email}</span>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-[color:var(--border)] bg-[color:var(--card)] md:flex md:flex-col">
          <div className="flex h-16 items-center border-b border-[color:var(--border)] px-4">
            <Link href="/admin-saas" className="flex items-center gap-2 font-semibold tracking-tight">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-red-500 text-white">
                <Shield className="h-3.5 w-3.5" />
              </span>
              Admin SaaS
            </Link>
          </div>
          <nav className="flex-1 space-y-0.5 p-3">
            {ITEMS.map((it) => {
              const Icon = it.icon;
              const active = it.exact ? pathname === it.href : pathname.startsWith(it.href);
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
          <div className="border-t border-[color:var(--border)] p-3">
            <Link href="/app">
              <Button variant="ghost" size="sm" className="w-full justify-start">
                Voltar pro app
              </Button>
            </Link>
          </div>
        </aside>

        <div className="flex flex-1 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-[color:var(--border)] bg-[color:var(--card)] px-6">
            <div>
              <p className="text-sm font-semibold leading-none">Operação SaaS</p>
              <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                Métricas, tenants e auditoria
              </p>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button
                variant="ghost"
                size="icon"
                aria-label="Sair"
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </header>
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
