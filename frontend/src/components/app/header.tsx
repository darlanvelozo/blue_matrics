"use client";
import { LogOut, User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { logout } from "@/lib/auth";
import type { User } from "@/lib/auth";

export function AppHeader({ user }: { user: User }) {
  const router = useRouter();
  function onLogout() {
    logout();
    router.push("/login");
  }
  const tenant = user.tenant;
  return (
    <header className="flex h-16 items-center justify-between border-b border-[color:var(--border)] bg-[color:var(--card)] px-6">
      <div>
        <p className="text-sm font-semibold leading-none">{tenant?.name ?? "Sua empresa"}</p>
        <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
          {tenant?.status === "trial" && tenant.trial_ends_at
            ? `Trial até ${new Date(tenant.trial_ends_at).toLocaleDateString("pt-BR")}`
            : `Plano ${tenant?.status ?? "—"}`}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <div className="hidden items-center gap-2 rounded-lg border border-[color:var(--border)] px-3 py-1.5 text-sm md:flex">
          <UserIcon className="h-3.5 w-3.5 text-[color:var(--muted-foreground)]" />
          <span className="text-[color:var(--muted-foreground)]">{user.email}</span>
        </div>
        <Button variant="ghost" size="icon" aria-label="Sair" onClick={onLogout}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
