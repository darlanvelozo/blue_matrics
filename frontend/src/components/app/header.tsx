"use client";
import { LogOut, Menu, User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { logout } from "@/lib/auth";
import type { User } from "@/lib/auth";

export function AppHeader({
  user,
  onMenuClick,
}: {
  user: User;
  onMenuClick?: () => void;
}) {
  const router = useRouter();
  function onLogout() {
    logout();
    router.push("/login");
  }
  const tenant = user.tenant;
  return (
    <header className="flex h-16 items-center justify-between border-b border-[color:var(--border)] bg-[color:var(--card)] px-4 sm:px-6">
      <div className="flex items-center gap-3 min-w-0">
        {/* Hamburger só no mobile */}
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-md p-2 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)] md:hidden"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-none">
            {tenant?.name ?? "Sua empresa"}
          </p>
          <p className="mt-1 truncate text-xs text-[color:var(--muted-foreground)]">
            {tenant?.status === "trial" && tenant.trial_ends_at
              ? `Trial até ${new Date(tenant.trial_ends_at).toLocaleDateString("pt-BR")}`
              : `Plano ${tenant?.status ?? "—"}`}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <div className="hidden items-center gap-2 rounded-lg border border-[color:var(--border)] px-3 py-1.5 text-sm md:flex">
          <UserIcon className="h-3.5 w-3.5 text-[color:var(--muted-foreground)]" />
          <span className="max-w-[180px] truncate text-[color:var(--muted-foreground)]">
            {user.email}
          </span>
        </div>
        <Button variant="ghost" size="icon" aria-label="Sair" onClick={onLogout}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
