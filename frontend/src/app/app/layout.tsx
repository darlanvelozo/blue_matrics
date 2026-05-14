"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/app/header";
import { AppSidebar } from "@/components/app/sidebar";
import { ApiError } from "@/lib/api";
import { getMe } from "@/lib/auth";
import type { User } from "@/lib/auth";

export default function AuthedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
        } else {
          setError("Falha ao carregar dados da conta.");
        }
      });
  }, [router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 text-center">
        <p className="text-sm text-[color:var(--destructive)]">{error}</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="space-y-2 text-center text-sm text-[color:var(--muted-foreground)]">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-[color:var(--border)] border-t-[color:var(--primary)]" />
          Carregando…
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <AppHeader user={user} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
