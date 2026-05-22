"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Target, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  GOAL_KIND_LABELS,
  GOAL_PERIOD_LABELS,
  type Goal,
  type GoalKind,
  type GoalPeriod,
  createGoal,
  deleteGoal,
  listGoals,
} from "@/lib/goals";
import { formatCurrencyBRL } from "@/lib/utils";

export default function GoalsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["goals"], queryFn: listGoals });
  const goals = data?.goals ?? [];

  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Target className="h-6 w-6 text-blue-500" />
            Metas
          </h1>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Defina objetivos numéricos e acompanhe o progresso em tempo real.
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus className="mr-1 h-4 w-4" />
          {showForm ? "Cancelar" : "Nova meta"}
        </Button>
      </header>

      {showForm && (
        <NewGoalForm
          onSaved={() => {
            setShowForm(false);
            qc.invalidateQueries({ queryKey: ["goals"] });
          }}
        />
      )}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : goals.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Target className="mx-auto mb-4 h-12 w-12 text-[color:var(--muted-foreground)]/40" />
            <p className="text-sm text-[color:var(--muted-foreground)]">
              Você ainda não definiu nenhuma meta. Clique em
              <span className="font-medium"> Nova meta </span> para começar.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {goals.map((g) => (
            <GoalCard
              key={g.id}
              goal={g}
              onDelete={() => {
                qc.invalidateQueries({ queryKey: ["goals"] });
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GoalCard({ goal, onDelete }: { goal: Goal; onDelete: () => void }) {
  const del = useMutation({
    mutationFn: () => deleteGoal(goal.id),
    onSuccess: onDelete,
  });

  const progress = goal.progress;
  const pct = progress?.progress_pct ?? 0;
  const achieved = progress?.achieved ?? false;
  const barWidth = Math.min(pct, 100);
  const isCurrency = goal.kind !== "num_sales";

  const fmtValue = (v: number) =>
    isCurrency ? formatCurrencyBRL(v) : v.toLocaleString("pt-BR", { maximumFractionDigits: 0 });

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{goal.name}</CardTitle>
          <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
            {GOAL_KIND_LABELS[goal.kind]} · {GOAL_PERIOD_LABELS[goal.period]}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (confirm(`Excluir a meta "${goal.name}"?`)) del.mutate();
          }}
          className="rounded-md p-1.5 text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)] hover:text-red-500"
          aria-label="Excluir meta"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </CardHeader>
      <CardContent>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-xl font-bold">
            {progress ? fmtValue(progress.current) : "—"}
          </span>
          <span className="text-xs text-[color:var(--muted-foreground)]">
            de {fmtValue(goal.target_value)}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[color:var(--muted)]">
          <div
            className={`h-full rounded-full transition-all ${
              achieved ? "bg-emerald-500" : "bg-blue-500"
            }`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between text-xs">
          <span className={achieved ? "font-semibold text-emerald-600" : "text-[color:var(--muted-foreground)]"}>
            {pct.toFixed(1).replace(".", ",")}%
            {achieved && " · atingida"}
          </span>
          {progress && (
            <span className="text-[color:var(--muted-foreground)]">
              {progress.period_start} → {progress.period_end}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function NewGoalForm({ onSaved }: { onSaved: () => void }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<GoalKind>("revenue");
  const [period, setPeriod] = useState<GoalPeriod>("month");
  const [target, setTarget] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () =>
      createGoal({ name, kind, period, target_value: Number.parseFloat(target) }),
    onSuccess: () => {
      setName("");
      setTarget("");
      setErr(null);
      onSaved();
    },
    onError: (e: Error) => setErr(e.message || "Falha ao criar meta."),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setErr("Informe um nome.");
      return;
    }
    if (!target || Number.parseFloat(target) <= 0) {
      setErr("Informe um valor-alvo maior que zero.");
      return;
    }
    save.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Nova meta</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Label htmlFor="goal-name">Nome</Label>
            <Input
              id="goal-name"
              placeholder="Ex.: Faturar R$ 50k em abril"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
            />
          </div>
          <div>
            <Label htmlFor="goal-kind">Indicador</Label>
            <Select
              id="goal-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value as GoalKind)}
              options={(Object.keys(GOAL_KIND_LABELS) as GoalKind[]).map((k) => ({
                value: k,
                label: GOAL_KIND_LABELS[k],
              }))}
            />
          </div>
          <div>
            <Label htmlFor="goal-period">Periodicidade</Label>
            <Select
              id="goal-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value as GoalPeriod)}
              options={(Object.keys(GOAL_PERIOD_LABELS) as GoalPeriod[]).map((p) => ({
                value: p,
                label: GOAL_PERIOD_LABELS[p],
              }))}
            />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="goal-target">
              Valor-alvo {kind === "num_sales" ? "(nº de vendas)" : "(R$)"}
            </Label>
            <Input
              id="goal-target"
              type="number"
              step="0.01"
              min="0"
              placeholder={kind === "num_sales" ? "100" : "50000"}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
          {err && (
            <p className="md:col-span-2 text-sm text-[color:var(--destructive)]">{err}</p>
          )}
          <div className="md:col-span-2 flex justify-end">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Salvando…" : "Criar meta"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
