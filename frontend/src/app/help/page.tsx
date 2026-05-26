import Link from "next/link";
import {
  ChevronLeft,
  CreditCard,
  HelpCircle,
  Mail,
  MessageCircle,
  Plug,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Logo } from "@/components/logo";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Central de ajuda — BI AZUL",
  description:
    "Tudo o que você precisa saber para começar a usar o BI AZUL — onboarding, integração Conta Azul, planos, IA e suporte.",
};

interface QA {
  q: string;
  a: React.ReactNode;
}

const SECTIONS: { id: string; title: string; icon: typeof Plug; qas: QA[] }[] = [
  {
    id: "comecando",
    title: "Começando",
    icon: Sparkles,
    qas: [
      {
        q: "Quanto tempo leva pra ver os primeiros números?",
        a: (
          <>
            Em geral, 2-5 minutos. Depois do cadastro, você conecta sua Conta
            Azul via OAuth (3 cliques), aguarda a primeira sincronização
            (1-3 min para empresas com até 5 mil lançamentos) e os
            dashboards já aparecem populados.
          </>
        ),
      },
      {
        q: "O trial de 7 dias tem limitação?",
        a: (
          <>
            Não — você tem acesso completo a todos os dashboards, Analista IA,
            insights, sincronização e exportações. Sem cartão na inscrição.
            Termina o trial sem precisar fazer nada se decidir não continuar.
          </>
        ),
      },
      {
        q: "Posso testar sem ter Conta Azul?",
        a: (
          <>
            Sim, mas as análises ficam vazias. O BI AZUL funciona como uma
            camada em cima dos dados que vêm da Conta Azul — sem o ERP
            conectado, não há de onde puxar números. Se você usa outro ERP,
            mande um e-mail pra{" "}
            <a href="mailto:contato@biazul.com" className="text-[color:var(--primary)] hover:underline">
              contato@biazul.com
            </a>
            .
          </>
        ),
      },
    ],
  },
  {
    id: "conta-azul",
    title: "Integração Conta Azul",
    icon: Plug,
    qas: [
      {
        q: "Como funciona a integração?",
        a: (
          <>
            Via OAuth 2.0 oficial. Você é redirecionado pra Conta Azul,
            autoriza o BI AZUL a ler seus dados, e a sincronização começa
            automaticamente. Nunca compartilhamos sua senha — usamos só
            tokens de acesso que você pode revogar a qualquer momento no
            painel da Conta Azul.
          </>
        ),
      },
      {
        q: "Que dados são sincronizados?",
        a: (
          <ul className="list-disc pl-5">
            <li>Clientes, fornecedores, produtos, serviços</li>
            <li>Lançamentos financeiros (contas a pagar/receber)</li>
            <li>Vendas, pedidos e notas fiscais</li>
            <li>Categorias, centros de custo</li>
          </ul>
        ),
      },
      {
        q: "Quando os dados são atualizados?",
        a: (
          <>
            Sincronização automática a cada 60 minutos por padrão. Você
            também pode disparar manualmente no menu{" "}
            <strong>Sincronização</strong> a qualquer momento.
          </>
        ),
      },
      {
        q: "Posso desconectar a Conta Azul?",
        a: (
          <>
            Sim, em <strong>Configurações &gt; Integrações</strong>. A conexão
            também pode ser revogada direto no painel da Conta Azul.
            Os dados já sincronizados continuam no BI AZUL até você cancelar
            a assinatura.
          </>
        ),
      },
    ],
  },
  {
    id: "ia",
    title: "Analista IA",
    icon: MessageCircle,
    qas: [
      {
        q: "Como o Analista IA funciona?",
        a: (
          <>
            Você pergunta em linguagem natural ("quais os 5 maiores clientes
            inadimplentes?") e o agente decide quais ferramentas chamar para
            buscar a resposta nos seus dados. São 22 ferramentas
            especializadas (KPIs, RFV, ABC, previsões etc.) — o agente
            combina quantas precisar.
          </>
        ),
      },
      {
        q: "Meus dados são usados para treinar o modelo?",
        a: (
          <>
            Não. Usamos a API da OpenAI com a flag de não-treinamento ativada.
            Além disso, enviamos apenas resumos agregados — nunca o CPF/CNPJ
            de seus clientes vai pra fora do nosso servidor.
          </>
        ),
      },
      {
        q: "Tem limite de perguntas?",
        a: (
          <>
            30 perguntas a cada 5 minutos por usuário — proteção contra
            scripts automatizados. Uso humano normal nunca atinge esse
            limite. Se precisar de mais, entre em contato.
          </>
        ),
      },
    ],
  },
  {
    id: "planos",
    title: "Planos e Pagamento",
    icon: CreditCard,
    qas: [
      {
        q: "Quais são os planos disponíveis?",
        a: (
          <ul className="list-disc pl-5">
            <li><strong>Mensal</strong> — R$ 299,90/mês</li>
            <li><strong>Semestral</strong> — R$ 1.649,45 a cada 6 meses (8% off)</li>
            <li><strong>Anual</strong> — R$ 2.999/ano (17% off)</li>
          </ul>
        ),
      },
      {
        q: "Posso trocar de plano depois?",
        a: (
          <>
            Sim, em <strong>Planos &amp; Assinatura</strong>. Ao mudar para um
            ciclo maior (anual, por exemplo), o saldo do ciclo atual é
            convertido em crédito proporcional.
          </>
        ),
      },
      {
        q: "Quais formas de pagamento aceitam?",
        a: (
          <>
            Cartão de crédito (Visa, Mastercard, Elo, Amex) e boleto bancário,
            ambos processados pela Stripe. Não armazenamos dados de cartão.
          </>
        ),
      },
      {
        q: "Como cancelo?",
        a: (
          <>
            Em 3 cliques no painel — sem fidelidade, sem multa. Detalhes na{" "}
            <Link href="/legal/cancelamento" className="text-[color:var(--primary)] hover:underline">
              Política de Cancelamento
            </Link>
            .
          </>
        ),
      },
      {
        q: "Tem reembolso?",
        a: (
          <>
            Para Semestral e Anual, sim — 7 dias corridos após a compra
            (direito de arrependimento, CDC art. 49). Mensal não tem
            reembolso proporcional, mas a renovação é cancelada
            imediatamente.
          </>
        ),
      },
    ],
  },
  {
    id: "seguranca",
    title: "Segurança e Privacidade",
    icon: ShieldCheck,
    qas: [
      {
        q: "Onde meus dados ficam armazenados?",
        a: (
          <>
            Em servidor brasileiro (Hostinger Cloud, São Paulo), criptografado
            em repouso. Backups diários com retenção de 7 dias.
          </>
        ),
      },
      {
        q: "Quem tem acesso aos meus dados?",
        a: (
          <>
            Apenas você e os usuários que você adicionar à sua organização.
            Internamente, acesso restrito a administradores do sistema
            apenas para fins de suporte, e sempre auditado.
          </>
        ),
      },
      {
        q: "Vocês estão em conformidade com a LGPD?",
        a: (
          <>
            Sim. Detalhes na{" "}
            <Link href="/legal/privacidade" className="text-[color:var(--primary)] hover:underline">
              Política de Privacidade
            </Link>
            . Você pode exportar ou solicitar exclusão dos seus dados a
            qualquer momento.
          </>
        ),
      },
    ],
  },
];

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-[color:var(--background)]">
      <header className="border-b border-[color:var(--border)]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <Link href="/" aria-label="BI AZUL — voltar pra home">
            <Logo />
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
          >
            <ChevronLeft className="h-4 w-4" /> Voltar para o site
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="text-center">
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[color:var(--primary)]/10 text-[color:var(--primary)]">
            <HelpCircle className="h-6 w-6" />
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight">Central de ajuda</h1>
          <p className="mt-2 max-w-xl mx-auto text-sm text-[color:var(--muted-foreground)]">
            Tudo o que você precisa saber para começar a usar o BI AZUL —
            do cadastro à integração com Conta Azul, IA e pagamentos.
          </p>
        </div>

        <nav className="mt-10 flex flex-wrap justify-center gap-2 text-xs">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--background)] px-3 py-1.5 font-medium text-[color:var(--muted-foreground)] hover:border-[color:var(--primary)]/40 hover:text-[color:var(--foreground)]"
            >
              {s.title}
            </a>
          ))}
        </nav>

        <div className="mt-12 space-y-12">
          {SECTIONS.map((s) => (
            <section key={s.id} id={s.id} className="scroll-mt-20">
              <div className="flex items-center gap-2 border-b border-[color:var(--border)] pb-2">
                <s.icon className="h-5 w-5 text-blue-500" />
                <h2 className="text-xl font-bold tracking-tight">{s.title}</h2>
              </div>
              <div className="mt-6 space-y-6">
                {s.qas.map((qa) => (
                  <details
                    key={qa.q}
                    className="group rounded-lg border border-[color:var(--border)] bg-[color:var(--background)] p-4 open:bg-[color:var(--muted)]/40"
                  >
                    <summary className="cursor-pointer list-none text-sm font-medium">
                      <span className="mr-2 text-[color:var(--muted-foreground)] group-open:rotate-90 inline-block transition-transform">
                        ›
                      </span>
                      {qa.q}
                    </summary>
                    <div className="mt-3 pl-4 text-sm leading-relaxed text-[color:var(--muted-foreground)]">
                      {qa.a}
                    </div>
                  </details>
                ))}
              </div>
            </section>
          ))}
        </div>

        <section className="mt-16 rounded-xl border border-[color:var(--border)] bg-[color:var(--muted)]/30 p-6 text-center">
          <Mail className="mx-auto h-6 w-6 text-blue-500" />
          <h2 className="mt-3 text-lg font-semibold">Não encontrou sua resposta?</h2>
          <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            Mande um e-mail — respondemos em até 1 dia útil.
          </p>
          <a
            href="mailto:suporte@biazul.com"
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-[color:var(--primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            <Mail className="h-4 w-4" /> suporte@biazul.com
          </a>
        </section>
      </div>
    </div>
  );
}
