"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Copy,
  Loader2,
  MessageSquarePlus,
  MoreHorizontal,
  Pencil,
  Send,
  Sparkles,
  Trash2,
  User,
  Wand2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { BlueprintRender } from "@/components/ai/blueprint-render";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import {
  askAi,
  deleteChatSession,
  getChatSession,
  listChatSessions,
  renameChatSession,
  type AnalysisBlueprint,
  type ChatSessionMessage,
  type ChatSessionSummary,
} from "@/lib/ai";
import { cn } from "@/lib/utils";

const SUGGESTIONS: string[] = [
  "Como está meu fluxo de caixa nos últimos 30 dias?",
  "Quais foram minhas 10 maiores despesas no último trimestre?",
  "Top 5 fornecedores nos últimos 90 dias",
  "Quanto tenho a pagar nos próximos 30 dias?",
  "Qual minha inadimplência atual?",
  "Me dê um panorama geral do negócio nos últimos 12 meses",
];

interface UiMessage {
  role: "user" | "assistant";
  content: string;
  blueprint?: AnalysisBlueprint | null;
}

export default function AiPage() {
  const qc = useQueryClient();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [blueprint, setBlueprint] = useState<AnalysisBlueprint | null>(null);
  const [llmInfo, setLlmInfo] = useState<{
    used_llm: boolean;
    provider: string;
    error: string | null;
    suggestions: string[];
    tools: { name: string; ok: boolean; args: Record<string, unknown> }[];
  } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Lista de conversas
  const sessions = useQuery({
    queryKey: ["ai-chats"],
    queryFn: listChatSessions,
  });

  // Carregar conversa selecionada
  const sessionDetail = useQuery({
    queryKey: ["ai-chat", sessionId],
    queryFn: () => getChatSession(sessionId!),
    enabled: sessionId !== null,
  });

  // Quando troca de sessão, popula mensagens
  useEffect(() => {
    if (sessionId === null) {
      setMessages([]);
      setBlueprint(null);
      setLlmInfo(null);
      return;
    }
    if (sessionDetail.data) {
      const msgs: UiMessage[] = sessionDetail.data.messages.map((m: ChatSessionMessage) => ({
        role: m.role,
        content: m.content,
        blueprint: m.blueprint,
      }));
      setMessages(msgs);
      // Última blueprint do assistant
      const lastAssist = [...sessionDetail.data.messages]
        .reverse()
        .find((m) => m.role === "assistant" && m.blueprint);
      setBlueprint(lastAssist?.blueprint || null);
      // Info da última resposta (pra mostrar tools, etc)
      const last = sessionDetail.data.messages[sessionDetail.data.messages.length - 1];
      if (last && last.role === "assistant") {
        setLlmInfo({
          used_llm: last.used_llm,
          provider: last.llm_provider || "",
          error: last.llm_error || null,
          suggestions: [],
          tools: (last.tools_called || []) as { name: string; ok: boolean; args: Record<string, unknown> }[],
        });
      }
    }
  }, [sessionId, sessionDetail.data]);

  const ask = useMutation({
    mutationFn: (question: string) =>
      askAi({ question, session_id: sessionId ?? undefined }),
    onMutate: (question) => {
      // Otimista: já mostra a mensagem do usuário
      setMessages((prev) => [...prev, { role: "user", content: question }]);
    },
    onSuccess: (resp) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: resp.answer, blueprint: resp.blueprint },
      ]);
      setBlueprint(resp.blueprint);
      setLlmInfo({
        used_llm: resp.used_llm,
        provider: resp.provider,
        error: resp.llm_error || null,
        suggestions: resp.suggestions || [],
        tools: resp.agent?.tools_called || [],
      });
      setDraft("");
      // Se foi criada uma sessão nova (sessionId era null), aderir a ela
      if (sessionId === null) {
        setSessionId(resp.session_id);
      }
      // Refresca a lista lateral (movimenta sessão atual pro topo, atualiza message_count)
      qc.invalidateQueries({ queryKey: ["ai-chats"] });
      try {
        window.localStorage.setItem("biazul_has_asked_ai", "1");
      } catch {
        /* ignora */
      }
    },
    onError: () => {
      // Reverte a mensagem otimista
      setMessages((prev) => prev.slice(0, -1));
    },
  });

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

  const newChat = () => {
    setSessionId(null);
    setMessages([]);
    setBlueprint(null);
    setLlmInfo(null);
    setDraft("");
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Wand2 className="h-6 w-6 text-[color:var(--primary)]" />
          Analista IA
        </h1>
        <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
          Pergunte sobre seus dados financeiros. As conversas ficam salvas no
          painel lateral.
          {llmInfo?.used_llm && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-700">
              <Wand2 className="h-2.5 w-2.5" /> IA real
            </span>
          )}
        </p>
      </header>

      {llmInfo?.error === "quota_exceeded" && (
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

      <div className="grid gap-6 lg:grid-cols-[230px_1fr_400px]">
        {/* Sidebar de conversas */}
        <ChatSidebar
          sessions={sessions.data?.sessions ?? []}
          activeId={sessionId}
          loading={sessions.isLoading}
          onSelect={setSessionId}
          onNew={newChat}
          onDeleted={(id) => {
            if (id === sessionId) newChat();
            qc.invalidateQueries({ queryKey: ["ai-chats"] });
          }}
          onRenamed={() => qc.invalidateQueries({ queryKey: ["ai-chats"] })}
        />

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
                  tabelas e gráficos relevantes.
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
              {messages.length === 0 && !sessionDetail.isFetching && (
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
              {sessionDetail.isFetching && messages.length === 0 && (
                <div className="flex justify-center py-8 text-xs text-[color:var(--muted-foreground)]">
                  <Loader2 className="h-4 w-4 animate-spin" /> Carregando conversa…
                </div>
              )}
              {messages.map((m, i) => (
                <Bubble key={i} message={m} />
              ))}
              {messages.length > 0 && !ask.isPending && llmInfo?.tools && llmInfo.tools.length > 0 && (
                <div className="space-y-1 pt-1">
                  <p className="text-[9px] font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
                    Ferramentas consultadas
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {llmInfo.tools.map((t, i) => (
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
              {messages.length > 0 && !ask.isPending && llmInfo && llmInfo.suggestions.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-[color:var(--muted-foreground)]">
                    Perguntas relacionadas
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {llmInfo.suggestions.map((s) => (
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

// ============================================================
function ChatSidebar({
  sessions,
  activeId,
  loading,
  onSelect,
  onNew,
  onDeleted,
  onRenamed,
}: {
  sessions: ChatSessionSummary[];
  activeId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
  onNew: () => void;
  onDeleted: (id: number) => void;
  onRenamed: () => void;
}) {
  return (
    <aside className="flex flex-col h-[calc(100vh-200px)] min-h-[500px]">
      <Card className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-[color:var(--border)] p-3">
          <Button onClick={onNew} className="w-full" size="sm">
            <MessageSquarePlus className="mr-2 h-3.5 w-3.5" />
            Nova conversa
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {loading ? (
            <div className="flex justify-center py-6 text-xs text-[color:var(--muted-foreground)]">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-[color:var(--muted-foreground)]">
              Nenhuma conversa ainda.
              <br />
              Faça uma pergunta para começar.
            </p>
          ) : (
            <ul className="space-y-1">
              {sessions.map((s) => (
                <SessionRow
                  key={s.id}
                  session={s}
                  active={s.id === activeId}
                  onSelect={() => onSelect(s.id)}
                  onDeleted={() => onDeleted(s.id)}
                  onRenamed={onRenamed}
                />
              ))}
            </ul>
          )}
        </div>
      </Card>
    </aside>
  );
}

function SessionRow({
  session,
  active,
  onSelect,
  onDeleted,
  onRenamed,
}: {
  session: ChatSessionSummary;
  active: boolean;
  onSelect: () => void;
  onDeleted: () => void;
  onRenamed: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(session.title);
  const qc = useQueryClient();

  const rename = useMutation({
    mutationFn: () => renameChatSession(session.id, draftTitle.trim() || "Sem título"),
    onSuccess: () => {
      setEditing(false);
      onRenamed();
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteChatSession(session.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-chats"] });
      onDeleted();
    },
  });

  const when = useMemo(() => {
    const d = new Date(session.updated_at);
    const today = new Date();
    const sameDay = d.toDateString() === today.toDateString();
    return sameDay
      ? d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  }, [session.updated_at]);

  if (editing) {
    return (
      <li className="flex items-center gap-1 rounded-md border border-[color:var(--primary)] bg-[color:var(--background)] p-1">
        <input
          autoFocus
          value={draftTitle}
          onChange={(e) => setDraftTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") rename.mutate();
            if (e.key === "Escape") setEditing(false);
          }}
          className="flex-1 bg-transparent px-1 py-0.5 text-xs focus:outline-none"
          maxLength={120}
        />
        <button
          onClick={() => rename.mutate()}
          className="text-[10px] font-medium text-[color:var(--primary)]"
          disabled={rename.isPending}
        >
          OK
        </button>
      </li>
    );
  }

  return (
    <li className="relative group">
      <button
        onClick={onSelect}
        className={cn(
          "block w-full rounded-md px-2.5 py-2 text-left text-xs transition",
          active
            ? "bg-[color:var(--primary)]/10 text-[color:var(--foreground)]"
            : "hover:bg-[color:var(--muted)] text-[color:var(--foreground)]",
        )}
      >
        <span className="block truncate pr-6 font-medium">{session.title}</span>
        <span className="mt-0.5 block text-[10px] text-[color:var(--muted-foreground)]">
          {when} · {session.message_count} {session.message_count === 1 ? "msg" : "msgs"}
        </span>
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen(!menuOpen);
        }}
        className="absolute right-1 top-2 hidden h-5 w-5 items-center justify-center rounded text-[color:var(--muted-foreground)] hover:bg-[color:var(--background)] hover:text-[color:var(--foreground)] group-hover:inline-flex"
      >
        <MoreHorizontal className="h-3.5 w-3.5" />
      </button>
      {menuOpen && (
        <div className="absolute right-1 top-9 z-10 w-32 rounded-md border border-[color:var(--border)] bg-[color:var(--background)] py-1 shadow-lg">
          <button
            onClick={() => {
              setMenuOpen(false);
              setEditing(true);
              setDraftTitle(session.title);
            }}
            className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-xs hover:bg-[color:var(--muted)]"
          >
            <Pencil className="h-3 w-3" /> Renomear
          </button>
          <button
            onClick={() => {
              setMenuOpen(false);
              if (confirm("Excluir esta conversa?")) remove.mutate();
            }}
            className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-xs text-red-600 hover:bg-red-500/10"
          >
            <Trash2 className="h-3 w-3" /> Excluir
          </button>
        </div>
      )}
    </li>
  );
}

// ============================================================
function Bubble({ message, pending }: { message: UiMessage; pending?: boolean }) {
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
