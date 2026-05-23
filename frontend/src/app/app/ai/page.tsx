"use client";
import { useMutation } from "@tanstack/react-query";
import { AlertCircle, Copy, Loader2, RefreshCw, Send, Sparkles, User, Wand2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { BlueprintRender } from "@/components/ai/blueprint-render";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import {
  askAi,
  type AnalysisBlueprint,
  type AskResponse,
  type ChatMessage,
} from "@/lib/ai";

const SUGGESTIONS: string[] = [
  "Como está meu fluxo de caixa nos últimos 30 dias?",
  "Quais foram minhas 10 maiores despesas no último trimestre?",
  "Top 5 fornecedores nos últimos 90 dias",
  "Quanto tenho a pagar nos próximos 30 dias?",
  "Qual minha inadimplência atual?",
  "Me dê um panorama geral do negócio nos últimos 12 meses",
];

export default function AiPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [blueprint, setBlueprint] = useState<AnalysisBlueprint | null>(null);
  const [lastResp, setLastResp] = useState<AskResponse | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: (question: string) => askAi({ question, history: messages }),
    onSuccess: (resp, question) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        { role: "assistant", content: resp.answer },
      ]);
      setBlueprint(resp.blueprint);
      setLastResp(resp);
      setDraft("");
    },
  });

  const usedLlm = lastResp?.used_llm ?? false;
  const llmError = lastResp?.llm_error;
  const suggestions = lastResp?.suggestions ?? SUGGESTIONS;

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const submit = (text: string) => {
    const q = text.trim();
    if (!q || ask.isPending) return;
    ask.mutate(q);
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Wand2 className="h-6 w-6 text-[color:var(--primary)]" />
          Analista IA
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Pergunte sobre seus dados financeiros. A resposta vem em texto + tabelas + gráficos.
          {messages.length > 0 && usedLlm && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-700">
              <Wand2 className="h-2.5 w-2.5" /> IA real ({lastResp?.provider})
            </span>
          )}
          {messages.length > 0 && !usedLlm && (
            <span className="ml-2 inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              modo demo
            </span>
          )}
        </p>
      </header>

      {llmError === "quota_exceeded" && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">IA temporariamente em modo demo</p>
            <p className="mt-0.5 text-xs">
              Conta OpenAI sem créditos. Adicione saldo em{" "}
              <a
                href="https://platform.openai.com/account/billing"
                target="_blank"
                rel="noreferrer"
                className="font-medium underline"
              >
                platform.openai.com
              </a>{" "}
              e tente novamente.
            </p>
          </div>
        </div>
      )}
      {llmError === "rate_limited" && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Limite de requisições atingido</p>
            <p className="mt-0.5 text-xs">
              Espere alguns segundos e tente de novo.
            </p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        {/* Painel principal: dashboard dinâmico */}
        <div className="space-y-4">
          {blueprint ? (
            <BlueprintRender blueprint={blueprint} />
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--primary)]/10 text-[color:var(--primary)]">
                  <Sparkles className="h-5 w-5" />
                </span>
                <h2 className="text-lg font-semibold">Faça uma pergunta para começar</h2>
                <p className="max-w-md text-sm text-[color:var(--muted-foreground)]">
                  Pergunte em linguagem natural e a IA monta um dashboard com KPIs,
                  tabelas e gráficos relevantes para a sua pergunta.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.slice(0, 3).map((s) => (
                    <button
                      key={s}
                      onClick={() => submit(s)}
                      className="rounded-full border border-[color:var(--border)] px-3 py-1.5 text-xs hover:bg-[color:var(--muted)]"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Painel lateral: chat */}
        <aside className="flex flex-col h-[calc(100vh-200px)] min-h-[500px]">
          <Card className="flex h-full flex-col overflow-hidden">
            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <div className="space-y-2 text-xs">
                  <p className="font-medium text-[color:var(--muted-foreground)]">
                    Sugestões:
                  </p>
                  <ul className="space-y-1">
                    {SUGGESTIONS.map((s) => (
                      <li key={s}>
                        <button
                          onClick={() => submit(s)}
                          className="text-left text-[color:var(--primary)] hover:underline"
                        >
                          › {s}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {messages.map((m, i) => (
                <Bubble key={i} message={m} />
              ))}
              {/* Tools usadas pela última resposta — transparência */}
              {messages.length > 0 && !ask.isPending && lastResp?.agent?.tools_called && lastResp.agent.tools_called.length > 0 && (
                <div className="space-y-1 pt-1">
                  <p className="text-[9px] font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
                    Ferramentas consultadas
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {lastResp.agent.tools_called.map((t, i) => (
                      <span
                        key={i}
                        title={`Args: ${JSON.stringify(t.args)}`}
                        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono ${
                          t.ok
                            ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700"
                            : "border-red-500/30 bg-red-500/5 text-red-700"
                        }`}
                      >
                        {t.ok ? "✓" : "✗"} {t.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {/* Sugestões contextuais após resposta */}
              {messages.length > 0 && !ask.isPending && lastResp && (
                <div className="space-y-1.5 pt-1">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
                    Perguntas relacionadas
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {suggestions.map((s) => (
                      <button
                        key={s}
                        onClick={() => submit(s)}
                        className="rounded-full border border-[color:var(--border)] bg-[color:var(--background)] px-2.5 py-1 text-[11px] transition hover:border-[color:var(--primary)]/40 hover:bg-[color:var(--muted)]"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {ask.isPending && (
                <Bubble
                  message={{ role: "assistant", content: "Analisando…" }}
                  pending
                />
              )}
              {ask.error instanceof ApiError && (
                <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-700">
                  {ask.error.message}
                </div>
              )}
            </div>

            <form
              className="flex gap-2 border-t border-[color:var(--border)] p-3"
              onSubmit={(e) => {
                e.preventDefault();
                submit(draft);
              }}
            >
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Pergunte algo sobre seus dados…"
                disabled={ask.isPending}
                className="flex-1 rounded-md border border-[color:var(--border)] bg-[color:var(--background)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[color:var(--ring)]"
              />
              <Button type="submit" disabled={ask.isPending || !draft.trim()}>
                {ask.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function Bubble({ message, pending }: { message: ChatMessage; pending?: boolean }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      <span
        className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
          isUser
            ? "bg-[color:var(--primary)]/10 text-[color:var(--primary)]"
            : "bg-purple-500/10 text-purple-600"
        }`}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Wand2 className="h-3.5 w-3.5" />}
      </span>
      <div
        className={`min-w-0 flex-1 rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-[color:var(--primary)]/10 text-[color:var(--foreground)]"
            : "bg-[color:var(--muted)] text-[color:var(--foreground)]"
        }`}
      >
        {pending ? (
          <span className="inline-flex items-center gap-2 text-[color:var(--muted-foreground)]">
            <Loader2 className="h-3 w-3 animate-spin" /> {message.content}
          </span>
        ) : isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed
                          [&_p]:my-1.5 [&_ul]:my-1.5 [&_ul]:pl-4 [&_ul]:list-disc
                          [&_strong]:font-semibold [&_strong]:text-[color:var(--foreground)]
                          [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm
                          [&_code]:rounded [&_code]:bg-[color:var(--background)]
                          [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[11px]">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {!isUser && (
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(message.content)}
                className="mt-2 inline-flex items-center gap-1 text-[10px] text-[color:var(--muted-foreground)] hover:text-[color:var(--primary)]"
                title="Copiar resposta"
              >
                <Copy className="h-3 w-3" /> Copiar
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
