import Link from "next/link";
import { ArrowRight, BarChart3, Brain, CheckCircle2, Plug, ShieldCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";

export default function LandingPage() {
  return (
    <div className="flex flex-col">
      <SiteHeader />
      <main className="flex flex-col">
        <Hero />
        <SocialProof />
        <Benefits />
        <DashboardPreview />
        <HowItWorks />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <SiteFooter />
    </div>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-[color:var(--border)] glass">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Logo />
        <nav className="hidden items-center gap-8 text-sm md:flex">
          <a href="#beneficios" className="text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] transition-colors">Benefícios</a>
          <a href="#dashboards" className="text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] transition-colors">Dashboards</a>
          <a href="#planos" className="text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] transition-colors">Planos</a>
          <a href="#faq" className="text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)] transition-colors">FAQ</a>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="ghost" size="sm">
            <Link href="/login">Entrar</Link>
          </Button>
          <Button size="sm">
            <Link href="/register">Teste grátis</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-[color:var(--border)]">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.15),transparent_60%)]" />
      <div className="mx-auto flex max-w-6xl flex-col items-center px-4 py-24 text-center md:py-32">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[color:var(--border)] bg-[color:var(--card)] px-4 py-1.5 text-xs font-medium text-[color:var(--muted-foreground)]">
          <Sparkles className="h-3.5 w-3.5 text-blue-500" />
          BI as a Service para empresas que usam Conta Azul
        </div>
        <h1 className="max-w-3xl text-balance text-4xl font-bold leading-[1.1] tracking-tight md:text-6xl">
          Os números do seu negócio,
          <br />
          <span className="gradient-text">em tempo real</span>
        </h1>
        <p className="mt-6 max-w-2xl text-balance text-lg text-[color:var(--muted-foreground)] md:text-xl">
          Conecte sua Conta Azul e tenha dashboards inteligentes, alertas automáticos
          e insights gerados por IA — sem precisar entender de Power BI.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row">
          <Link href="/register">
            <Button size="lg" className="inline-flex items-center gap-2">
              Começar teste grátis de 7 dias
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="#dashboards">
            <Button size="lg" variant="outline">Ver demonstração</Button>
          </Link>
        </div>
        <p className="mt-4 text-xs text-[color:var(--muted-foreground)]">
          Sem cartão de crédito. Cancele quando quiser.
        </p>
      </div>
    </section>
  );
}

function SocialProof() {
  return (
    <section className="border-b border-[color:var(--border)] py-10">
      <div className="mx-auto max-w-6xl px-4 text-center">
        <p className="text-xs uppercase tracking-widest text-[color:var(--muted-foreground)]">
          Confiado por gestores de PMEs em todo o Brasil
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-12 gap-y-4 opacity-60">
          {["Padarias", "Clínicas", "Comércio", "Serviços", "E-commerce", "Indústrias"].map((s) => (
            <span key={s} className="text-sm font-medium text-[color:var(--muted-foreground)]">
              {s}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Benefits() {
  const items = [
    {
      icon: Plug,
      title: "Conexão em 30 segundos",
      body: "Faça login na sua Conta Azul, autorize a integração e os dados começam a sincronizar automaticamente.",
    },
    {
      icon: BarChart3,
      title: "Dashboards prontos",
      body: "Faturamento, fluxo de caixa, top clientes, vendas por vendedor, DRE visual — tudo em poucos cliques.",
    },
    {
      icon: Brain,
      title: "Insights por IA",
      body: "Receba alertas automáticos quando algo mudar: queda de faturamento, despesa fora do padrão, cliente inativo.",
    },
    {
      icon: ShieldCheck,
      title: "Seguro e conforme à LGPD",
      body: "Tokens criptografados, criptografia em repouso e isolamento por empresa. Dados nunca compartilhados.",
    },
  ];
  return (
    <section id="beneficios" className="border-b border-[color:var(--border)] py-20">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHeader
          eyebrow="Por que BlueMetrics"
          title="Você cuida do negócio. A gente cuida dos números."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {items.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="border-[color:var(--border)] transition-shadow hover:shadow-md">
              <CardContent className="p-6">
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 font-semibold">{title}</h3>
                <p className="text-sm text-[color:var(--muted-foreground)]">{body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function DashboardPreview() {
  return (
    <section id="dashboards" className="border-b border-[color:var(--border)] py-20">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHeader
          eyebrow="Dashboards"
          title="Tudo que importa em uma única tela"
        />
        <div className="mt-12 overflow-hidden rounded-2xl border border-[color:var(--border)] bg-[color:var(--card)] shadow-xl">
          <div className="flex items-center gap-2 border-b border-[color:var(--border)] px-4 py-3">
            <span className="h-3 w-3 rounded-full bg-red-400" />
            <span className="h-3 w-3 rounded-full bg-yellow-400" />
            <span className="h-3 w-3 rounded-full bg-green-400" />
            <span className="ml-3 text-xs text-[color:var(--muted-foreground)]">app.bluemetrics.com.br/app/dashboards/executivo</span>
          </div>
          <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard title="Faturamento" value="R$ 184.320" delta="+12,4%" positive />
            <KpiCard title="Lucro líquido" value="R$ 41.870" delta="+5,1%" positive />
            <KpiCard title="Inadimplência" value="3,2%" delta="-0,4 pp" positive />
            <KpiCard title="Ticket médio" value="R$ 312" delta="+8,9%" positive />
          </div>
          <div className="grid gap-4 px-6 pb-6 lg:grid-cols-3">
            <FakeChart title="Faturamento últimos 12 meses" h={180} />
            <FakeChart title="Top 5 clientes" h={180} />
            <FakeChart title="Fluxo de caixa" h={180} />
          </div>
        </div>
      </div>
    </section>
  );
}

function KpiCard({ title, value, delta, positive }: { title: string; value: string; delta: string; positive: boolean }) {
  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--background)] p-4">
      <p className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{title}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight">{value}</p>
      <p className={positive ? "mt-1 text-xs font-medium text-green-500" : "mt-1 text-xs font-medium text-red-500"}>
        {delta} vs mês anterior
      </p>
    </div>
  );
}

function FakeChart({ title, h }: { title: string; h: number }) {
  // gera barras decorativas
  const bars = Array.from({ length: 12 }, (_, i) => 30 + ((i * 23) % 70));
  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--background)] p-4">
      <p className="mb-3 text-sm font-medium">{title}</p>
      <div className="flex items-end gap-1" style={{ height: h }}>
        {bars.map((b, i) => (
          <div
            key={i}
            className="flex-1 rounded-t bg-gradient-to-t from-blue-500/40 to-blue-500"
            style={{ height: `${b}%` }}
          />
        ))}
      </div>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    { n: 1, title: "Crie sua conta", body: "Trial grátis de 7 dias, sem cartão." },
    { n: 2, title: "Conecte a Conta Azul", body: "OAuth seguro, 30 segundos." },
    { n: 3, title: "Pronto", body: "Dashboards e insights chegam na hora." },
  ];
  return (
    <section className="border-b border-[color:var(--border)] py-20">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHeader eyebrow="Como funciona" title="Do cadastro ao primeiro insight em 3 passos" />
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {steps.map((s) => (
            <Card key={s.n}>
              <CardContent className="p-6">
                <div className="mb-4 inline-flex h-9 w-9 items-center justify-center rounded-full bg-blue-500 text-sm font-bold text-white">
                  {s.n}
                </div>
                <h3 className="mb-2 font-semibold">{s.title}</h3>
                <p className="text-sm text-[color:var(--muted-foreground)]">{s.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const plans = [
    {
      name: "Starter",
      price: "R$ 99",
      desc: "Para times pequenos que estão começando.",
      features: ["1 usuário", "Dashboards essenciais", "Sync diário", "Suporte por e-mail"],
    },
    {
      name: "Growth",
      price: "R$ 249",
      desc: "Para empresas em crescimento que querem insights.",
      features: ["Até 5 usuários", "Todos os dashboards", "Sync de hora em hora", "Insights por IA", "Exportação PDF/Excel"],
      highlight: true,
    },
    {
      name: "Business",
      price: "R$ 499",
      desc: "Para operações que dependem de dados em tempo real.",
      features: ["Usuários ilimitados", "Sync em tempo real", "Insights premium + assistente IA", "API & Webhooks", "Suporte prioritário"],
    },
  ];
  return (
    <section id="planos" className="border-b border-[color:var(--border)] py-20">
      <div className="mx-auto max-w-6xl px-4">
        <SectionHeader
          eyebrow="Planos"
          title="Preço simples. Trial grátis de 7 dias em qualquer plano."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {plans.map((p) => (
            <Card
              key={p.name}
              className={
                p.highlight
                  ? "relative border-blue-500/40 shadow-lg ring-1 ring-blue-500/20"
                  : ""
              }
            >
              {p.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-blue-500 px-3 py-1 text-xs font-semibold text-white shadow">
                  Mais popular
                </span>
              )}
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold">{p.name}</h3>
                <p className="mt-1 text-sm text-[color:var(--muted-foreground)]">{p.desc}</p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-4xl font-bold tracking-tight">{p.price}</span>
                  <span className="text-sm text-[color:var(--muted-foreground)]">/mês</span>
                </div>
                <ul className="mt-6 space-y-2 text-sm">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Button className="mt-8 w-full" variant={p.highlight ? "default" : "outline"}>
                  <Link href="/register">Começar grátis</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq() {
  const items = [
    {
      q: "Vocês têm acesso à minha senha da Conta Azul?",
      a: "Não. A conexão é via OAuth2 oficial — você autoriza dentro da Conta Azul e nunca compartilha credenciais conosco.",
    },
    {
      q: "Os dados ficam onde?",
      a: "Em servidores hospedados no Brasil, criptografados em repouso. Em conformidade com a LGPD.",
    },
    {
      q: "Posso cancelar quando quiser?",
      a: "Sim. Cancele em 1 clique no painel. Sem multa, sem fidelidade.",
    },
    {
      q: "E se minha Conta Azul não tiver módulo de estoque?",
      a: "Sem problema — sincronizamos apenas o que sua conta tiver disponível. Os demais dashboards continuam funcionando normalmente.",
    },
  ];
  return (
    <section id="faq" className="border-b border-[color:var(--border)] py-20">
      <div className="mx-auto max-w-3xl px-4">
        <SectionHeader eyebrow="Perguntas frequentes" title="Tudo que você precisa saber" />
        <div className="mt-12 divide-y divide-[color:var(--border)] rounded-2xl border border-[color:var(--border)] bg-[color:var(--card)]">
          {items.map((it) => (
            <details key={it.q} className="group p-6">
              <summary className="flex cursor-pointer items-center justify-between text-base font-medium">
                {it.q}
                <span className="ml-4 text-[color:var(--muted-foreground)] transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-sm text-[color:var(--muted-foreground)]">{it.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="border-b border-[color:var(--border)] py-24">
      <div className="mx-auto max-w-4xl px-4 text-center">
        <h2 className="text-balance text-3xl font-bold tracking-tight md:text-5xl">
          Conecte sua Conta Azul e visualize <span className="gradient-text">os números do seu negócio</span> em minutos.
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-[color:var(--muted-foreground)]">
          Comece com o teste gratuito de 7 dias. Sem cartão de crédito, sem compromisso.
        </p>
        <Button size="lg" className="mt-8">
          <Link href="/register" className="inline-flex items-center gap-2">
            Começar agora <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-[color:var(--muted-foreground)] md:flex-row">
        <div className="flex items-center gap-4">
          <Logo />
        </div>
        <p>© {new Date().getFullYear()} BlueMetrics. Todos os direitos reservados.</p>
      </div>
    </footer>
  );
}

function SectionHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-blue-500">{eyebrow}</p>
      <h2 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
    </div>
  );
}
