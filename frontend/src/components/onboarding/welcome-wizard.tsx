"use client";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Loader2,
  Plug,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type StepStatus = "done" | "current" | "pending";

interface Step {
  id: string;
  title: string;
  description: string;
  status: StepStatus;
  cta?: { href: string; label: string; primary?: boolean };
}

interface Props {
  /** Tem credenciais Conta Azul cadastradas? */
  contaAzulConnected: boolean;
  /** Total de sincronizações já rodadas (qualquer status). */
  syncCount: number;
  /** Última sincronização teve sucesso? */
  syncSuccess?: boolean;
  /** Já fez ao menos uma pergunta para a IA? (via localStorage marker) */
  hasAskedAi?: boolean;
}

export function WelcomeWizard({
  contaAzulConnected,
  syncCount,
  syncSuccess,
  hasAskedAi,
}: Props) {
  // Determina status de cada step de forma estrita: o "current" é o primeiro
  // não-feito; tudo acima dele é "done", tudo abaixo é "pending".
  const stepsDone = [
    true, // 1. Conta criada — sempre done
    contaAzulConnected,
    syncCount > 0 && (syncSuccess ?? false),
    hasAskedAi ?? false,
  ];
  const currentIdx = stepsDone.findIndex((d) => !d);
  const allDone = currentIdx === -1;

  const toStatus = (i: number): StepStatus => {
    if (stepsDone[i]) return "done";
    if (i === currentIdx) return "current";
    return "pending";
  };

  const steps: Step[] = [
    {
      id: "signup",
      title: "Crie sua conta",
      description: "Sua organização foi criada e o trial de 7 dias está ativo.",
      status: toStatus(0),
    },
    {
      id: "contaazul",
      title: "Conecte sua Conta Azul",
      description:
        "Autorize o BI AZUL a ler seus dados via OAuth oficial — leva 3 cliques. Sua senha nunca é compartilhada.",
      status: toStatus(1),
      cta: contaAzulConnected
        ? undefined
        : { href: "/app/integrations", label: "Conectar agora", primary: true },
    },
    {
      id: "sync",
      title: "Aguarde a primeira sincronização",
      description:
        syncCount === 0
          ? "Assim que a Conta Azul estiver conectada, disparamos a primeira sincronização automática (1-3 min)."
          : "Sincronização em andamento — os dashboards vão aparecer assim que terminar.",
      status: toStatus(2),
      cta:
        contaAzulConnected && !stepsDone[2]
          ? { href: "/app/sync", label: "Ver sincronização", primary: true }
          : undefined,
    },
    {
      id: "ai",
      title: "Faça sua primeira pergunta",
      description:
        "Pergunte em linguagem natural ('quanto faturei semana passada?') e o Analista IA responde com dados reais.",
      status: toStatus(3),
      cta: stepsDone[2]
        ? { href: "/app/ai", label: "Abrir Analista IA", primary: true }
        : undefined,
    },
  ];

  return (
    <Card className="border-blue-500/30 bg-gradient-to-br from-blue-500/5 to-transparent">
      <CardContent className="p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">
              <Sparkles className="h-3 w-3" />
              Primeiros passos
            </span>
            <h2 className="mt-3 text-xl font-bold tracking-tight">
              {allDone
                ? "Tudo pronto! 🎉"
                : "Vamos colocar seus dashboards no ar"}
            </h2>
            <p className="mt-1 max-w-xl text-sm text-[color:var(--muted-foreground)]">
              {allDone
                ? "Você completou todas as etapas. Explore os dashboards e o Analista IA — qualquer dúvida, central de ajuda em /help."
                : "4 etapas rápidas. Você pode pular pra qualquer uma — vamos te guiar até os primeiros números aparecerem."}
            </p>
          </div>
          {!allDone && (
            <ProgressBadge
              done={stepsDone.filter(Boolean).length}
              total={stepsDone.length}
            />
          )}
        </div>

        <ol className="mt-8 space-y-3">
          {steps.map((step, i) => (
            <StepRow key={step.id} step={step} index={i + 1} />
          ))}
        </ol>

        {!allDone && (
          <p className="mt-6 text-xs text-[color:var(--muted-foreground)]">
            Não consegue avançar? Mande um e-mail para{" "}
            <a
              href="mailto:suporte@biazul.com"
              className="text-[color:var(--primary)] hover:underline"
            >
              suporte@biazul.com
            </a>{" "}
            — respondemos em 1 dia útil.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function StepRow({ step, index }: { step: Step; index: number }) {
  const isDone = step.status === "done";
  const isCurrent = step.status === "current";
  return (
    <li
      className={`flex items-start gap-4 rounded-lg border p-4 transition ${
        isDone
          ? "border-emerald-500/20 bg-emerald-500/5"
          : isCurrent
          ? "border-blue-500/30 bg-blue-500/5 ring-1 ring-blue-500/10"
          : "border-[color:var(--border)] bg-[color:var(--background)] opacity-70"
      }`}
    >
      <StepIcon status={step.status} index={index} />
      <div className="min-w-0 flex-1">
        <h3
          className={`text-sm font-semibold ${
            isDone ? "text-emerald-700 dark:text-emerald-400" : ""
          }`}
        >
          {step.title}
        </h3>
        <p className="mt-0.5 text-xs leading-relaxed text-[color:var(--muted-foreground)]">
          {step.description}
        </p>
        {step.cta && (
          <div className="mt-3">
            <Link href={step.cta.href}>
              <Button size="sm" variant={step.cta.primary ? "default" : "outline"}>
                {step.cta.label}
                <ArrowRight className="ml-1.5 h-3 w-3" />
              </Button>
            </Link>
          </div>
        )}
      </div>
    </li>
  );
}

function StepIcon({ status, index }: { status: StepStatus; index: number }) {
  if (status === "done") {
    return (
      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
        <CheckCircle2 className="h-4 w-4" />
      </span>
    );
  }
  if (status === "current") {
    return (
      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white">
        <span className="text-sm font-semibold">{index}</span>
      </span>
    );
  }
  return (
    <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[color:var(--border)] text-[color:var(--muted-foreground)]">
      <span className="text-sm font-semibold">{index}</span>
    </span>
  );
}

function ProgressBadge({ done, total }: { done: number; total: number }) {
  const pct = Math.round((done / total) * 100);
  return (
    <div className="text-right">
      <p className="text-xs font-medium text-[color:var(--muted-foreground)]">Progresso</p>
      <p className="text-sm font-mono font-semibold">{done} / {total}</p>
      <div className="mt-1 h-1.5 w-24 overflow-hidden rounded-full bg-[color:var(--muted)]">
        <div
          className="h-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
