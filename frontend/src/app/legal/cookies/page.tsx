import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de Cookies — BI AZUL",
  description: "Quais cookies o BI AZUL usa e como você pode gerenciá-los.",
};

export default function CookiesPage() {
  return (
    <article>
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Última atualização: 24 de maio de 2026
      </p>
      <h1>Política de Cookies</h1>

      <p>
        Esta política explica como o BI AZUL utiliza cookies e tecnologias
        similares (localStorage, sessionStorage) no nosso site e
        plataforma.
      </p>

      <h2>1. O que são Cookies</h2>
      <p>
        Cookies são pequenos arquivos de texto armazenados no seu
        navegador quando você visita um site. Servem para lembrar
        preferências, manter você logado e permitir funcionalidades
        básicas. Sem alguns cookies, o site não funciona.
      </p>

      <h2>2. Cookies que Usamos</h2>

      <h3>2.1 Estritamente necessários (sempre ativos)</h3>
      <p>
        Esses cookies não podem ser desativados — sem eles, a plataforma
        não funciona.
      </p>
      <table>
        <thead>
          <tr><th>Nome</th><th>Função</th><th>Duração</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><code>biazul_access</code> (localStorage)</td>
            <td>Token JWT de sessão autenticada</td>
            <td>1 hora (renova automaticamente)</td>
          </tr>
          <tr>
            <td><code>biazul_refresh</code> (localStorage)</td>
            <td>Token de refresh para manter login</td>
            <td>7 dias</td>
          </tr>
          <tr>
            <td><code>biazul_cookie_consent</code> (localStorage)</td>
            <td>Lembra que você fechou o banner de cookies</td>
            <td>1 ano</td>
          </tr>
          <tr>
            <td><code>csrftoken</code></td>
            <td>Proteção contra CSRF (Django)</td>
            <td>1 ano</td>
          </tr>
        </tbody>
      </table>

      <h3>2.2 Funcionais (opcional)</h3>
      <p>
        Cookies que melhoram a experiência mas não são obrigatórios.
        Você pode desativar limpando seu navegador.
      </p>
      <table>
        <thead>
          <tr><th>Nome</th><th>Função</th><th>Duração</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><code>theme</code></td>
            <td>Preferência de tema (claro/escuro)</td>
            <td>1 ano</td>
          </tr>
        </tbody>
      </table>

      <h3>2.3 Analytics (opcional, agregado)</h3>
      <p>
        Atualmente não utilizamos serviços de analytics externos como
        Google Analytics ou Meta Pixel. Caso passemos a utilizar,
        atualizaremos esta política e solicitaremos seu consentimento.
      </p>

      <h3>2.4 De terceiros</h3>
      <p>
        Durante o processo de pagamento, você é redirecionado ao Stripe
        Checkout, que utiliza cookies próprios para processar a
        transação com segurança. Consulte a{" "}
        <a
          href="https://stripe.com/br/cookies-policy/legal"
          target="_blank"
          rel="noreferrer"
        >
          política de cookies do Stripe
        </a>
        .
      </p>

      <h2>3. Como Gerenciar</h2>
      <p>
        Você pode bloquear ou apagar cookies a qualquer momento pelas
        configurações do seu navegador:
      </p>
      <ul>
        <li>
          <a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noreferrer">
            Google Chrome
          </a>
        </li>
        <li>
          <a href="https://support.mozilla.org/pt-BR/kb/cookies-protege-informacoes-armazenadas" target="_blank" rel="noreferrer">
            Mozilla Firefox
          </a>
        </li>
        <li>
          <a href="https://support.apple.com/pt-br/guide/safari/sfri11471" target="_blank" rel="noreferrer">
            Safari
          </a>
        </li>
        <li>
          <a href="https://support.microsoft.com/pt-br/microsoft-edge/excluir-cookies-no-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09" target="_blank" rel="noreferrer">
            Microsoft Edge
          </a>
        </li>
      </ul>
      <p>
        ⚠️ Bloquear cookies essenciais impedirá o uso da Plataforma — você
        não conseguirá se manter logado.
      </p>

      <h2>4. Atualizações</h2>
      <p>
        Esta política pode ser atualizada. A data no topo indica a versão
        atual. Alterações materiais serão comunicadas.
      </p>

      <h2>5. Contato</h2>
      <p>
        Dúvidas sobre cookies?{" "}
        <a href="mailto:dpo@biazul.com">dpo@biazul.com</a>
      </p>
    </article>
  );
}
