import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de Privacidade — BI AZUL",
  description:
    "Como o BI AZUL coleta, usa e protege seus dados pessoais em conformidade com a LGPD.",
};

export default function PrivacidadePage() {
  return (
    <article>
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Última atualização: 24 de maio de 2026
      </p>
      <h1>Política de Privacidade</h1>

      <p>
        Esta Política descreve como o <strong>BI AZUL</strong> coleta, usa,
        compartilha, armazena e protege dados pessoais, em conformidade
        com a Lei Geral de Proteção de Dados Pessoais (Lei 13.709/2018 —
        LGPD).
      </p>

      <h2>1. Controlador dos Dados</h2>
      <p>
        O controlador dos dados é [Razão Social a preencher], CNPJ
        [a preencher], com sede em [endereço a preencher].
      </p>
      <p>
        <strong>Encarregado pelo Tratamento de Dados (DPO):</strong>{" "}
        <a href="mailto:dpo@biazul.com">dpo@biazul.com</a>
      </p>

      <h2>2. Dados que Coletamos</h2>

      <h3>2.1 Dados de cadastro (fornecidos por você)</h3>
      <ul>
        <li>Nome completo e e-mail;</li>
        <li>Nome da empresa;</li>
        <li>Senha (armazenada com hash criptográfico — nunca em texto plano);</li>
        <li>Dados de pagamento (processados diretamente pelo Stripe — não armazenamos número de cartão).</li>
      </ul>

      <h3>2.2 Dados empresariais sincronizados via Conta Azul</h3>
      <p>
        Mediante sua autorização explícita via OAuth, recebemos da API
        oficial da Conta Azul os seguintes dados da sua empresa:
      </p>
      <ul>
        <li>Cadastro de clientes, fornecedores, produtos e serviços;</li>
        <li>Lançamentos financeiros (contas a pagar/receber, recebimentos);</li>
        <li>Vendas, pedidos e notas fiscais;</li>
        <li>Categorias, centros de custo e estrutura contábil.</li>
      </ul>
      <p>
        <strong>Esses dados pertencem à sua empresa e podem incluir dados
        pessoais de terceiros</strong> (ex: nome e CPF de clientes). Você é
        o controlador desses dados perante seus próprios titulares; o
        BI AZUL atua como <strong>operador</strong> (art. 5º, VII LGPD).
      </p>

      <h3>2.3 Dados técnicos (coletados automaticamente)</h3>
      <ul>
        <li>Endereço IP, tipo de navegador e sistema operacional;</li>
        <li>Páginas acessadas, horários e duração da sessão;</li>
        <li>Eventos de uso (cliques, perguntas feitas à IA);</li>
        <li>Logs de auditoria (login, sincronização, alterações de plano).</li>
      </ul>

      <h2>3. Base Legal e Finalidades (LGPD, art. 7º)</h2>
      <table>
        <thead>
          <tr>
            <th>Finalidade</th>
            <th>Base legal</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Prestação do serviço contratado</td>
            <td>Execução de contrato (art. 7º, V)</td>
          </tr>
          <tr>
            <td>Cobrança e emissão de notas fiscais</td>
            <td>Obrigação legal (art. 7º, II)</td>
          </tr>
          <tr>
            <td>Comunicação transacional (welcome, recibos, alertas)</td>
            <td>Execução de contrato</td>
          </tr>
          <tr>
            <td>Comunicação de marketing (newsletter, novidades)</td>
            <td>Consentimento (art. 7º, I) — opt-in</td>
          </tr>
          <tr>
            <td>Análise de uso para melhoria do produto</td>
            <td>Legítimo interesse (art. 7º, IX)</td>
          </tr>
          <tr>
            <td>Prevenção de fraude e segurança</td>
            <td>Legítimo interesse + obrigação legal</td>
          </tr>
        </tbody>
      </table>

      <h2>4. Compartilhamento com Terceiros</h2>
      <p>
        Compartilhamos dados <strong>exclusivamente</strong> com os
        operadores abaixo, todos sujeitos a contratos de processamento
        de dados (DPA) compatíveis com a LGPD:
      </p>
      <ul>
        <li>
          <strong>Stripe Payments do Brasil</strong> (
          <a href="https://stripe.com/br/privacy" target="_blank" rel="noreferrer">
            política de privacidade
          </a>
          ) — processamento de pagamentos. Recebe: nome, e-mail, valor, dados de cartão.
        </li>
        <li>
          <strong>Conta Azul</strong> (
          <a href="https://contaazul.com/politica-de-privacidade" target="_blank" rel="noreferrer">
            política de privacidade
          </a>
          ) — fonte dos dados empresariais (não compartilhamos, apenas recebemos).
        </li>
        <li>
          <strong>OpenAI</strong> (
          <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noreferrer">
            política de privacidade
          </a>
          ) — modelos de linguagem usados pelo Analista IA.
          Enviamos APENAS resumos agregados e KPIs anônimos (sem CPF/CNPJ de seus clientes).
          Não usamos dados para treinamento de modelos.
        </li>
        <li>
          <strong>Hostinger Cloud (VPS)</strong> — infraestrutura de hospedagem.
        </li>
        <li>
          <strong>Sentry</strong> — monitoramento de erros (apenas metadados técnicos, sem PII).
        </li>
        <li>
          Eventualmente, prestadores de e-mail transacional (Resend, Amazon SES) — apenas para envio de notificações operacionais.
        </li>
      </ul>
      <p>
        <strong>Não vendemos dados pessoais a terceiros</strong>, sob
        nenhuma hipótese.
      </p>

      <h2>5. Transferência Internacional</h2>
      <p>
        Alguns dos operadores listados (Stripe, OpenAI) processam dados em
        servidores fora do Brasil (predominantemente EUA e UE). Essas
        transferências ocorrem sob as garantias previstas no art. 33 da
        LGPD, com base em cláusulas contratuais padrão e adequação dos
        países de destino.
      </p>

      <h2>6. Segurança</h2>
      <ul>
        <li>Tráfego sempre via HTTPS/TLS;</li>
        <li>Senhas armazenadas com hash <code>PBKDF2</code>;</li>
        <li>Tokens OAuth da Conta Azul criptografados em repouso (Fernet);</li>
        <li>Banco de dados com acesso restrito por firewall;</li>
        <li>Backup diário com retenção de 7 dias;</li>
        <li>Logs de auditoria para ações sensíveis (LGPD art. 38);</li>
        <li>Princípio do menor privilégio aplicado a todos os acessos internos.</li>
      </ul>

      <h2>7. Retenção</h2>
      <ul>
        <li>
          <strong>Dados de conta ativa</strong>: enquanto sua assinatura
          estiver vigente.
        </li>
        <li>
          <strong>Após cancelamento</strong>: dados ficam disponíveis por
          30 dias para reativação. Depois, são <strong>excluídos
          permanentemente</strong>, exceto:
          <ul>
            <li>
              Faturas e dados fiscais — retidos por 5 anos por obrigação legal;
            </li>
            <li>Logs de auditoria — retidos por 5 anos.</li>
          </ul>
        </li>
        <li>
          Você pode pedir exclusão antecipada via{" "}
          <a href="mailto:dpo@biazul.com">dpo@biazul.com</a> (exceto dados
          retidos por obrigação legal).
        </li>
      </ul>

      <h2>8. Seus Direitos (LGPD art. 18)</h2>
      <p>Você tem direito a:</p>
      <ul>
        <li><strong>Confirmação e acesso</strong> aos dados que temos sobre você;</li>
        <li><strong>Correção</strong> de dados incompletos, inexatos ou desatualizados;</li>
        <li><strong>Anonimização, bloqueio ou eliminação</strong> de dados desnecessários;</li>
        <li><strong>Portabilidade</strong> (já disponível no painel: <em>Configurações &gt; Exportar meus dados</em>);</li>
        <li><strong>Eliminação</strong> dos dados tratados com base em consentimento;</li>
        <li><strong>Revogação do consentimento</strong> a qualquer momento;</li>
        <li><strong>Informação</strong> sobre o compartilhamento dos seus dados;</li>
        <li><strong>Oposição</strong> ao tratamento.</li>
      </ul>
      <p>
        Para exercer qualquer um destes direitos, envie um e-mail para{" "}
        <a href="mailto:dpo@biazul.com">dpo@biazul.com</a>. Responderemos em
        até 15 dias úteis.
      </p>

      <h2>9. Cookies</h2>
      <p>
        Utilizamos cookies essenciais ao funcionamento (sessão, autenticação)
        e cookies opcionais (analytics agregado). Detalhes em nossa{" "}
        <a href="/legal/cookies">Política de Cookies</a>.
      </p>

      <h2>10. Crianças e Adolescentes</h2>
      <p>
        A Plataforma é destinada exclusivamente a empresas e profissionais
        maiores de 18 anos. Não coletamos dados de menores intencionalmente.
        Caso tomemos conhecimento de coleta acidental, os dados serão
        excluídos imediatamente.
      </p>

      <h2>11. Alterações desta Política</h2>
      <p>
        Esta Política pode ser atualizada periodicamente. Alterações
        materiais serão notificadas com 15 dias de antecedência por e-mail
        e/ou banner na Plataforma.
      </p>

      <h2>12. Reclamação à ANPD</h2>
      <p>
        Caso entenda que o tratamento de seus dados viola a LGPD, você
        pode apresentar reclamação à Autoridade Nacional de Proteção de
        Dados (ANPD) por meio do site{" "}
        <a
          href="https://www.gov.br/anpd"
          target="_blank"
          rel="noreferrer"
        >
          gov.br/anpd
        </a>
        .
      </p>

      <hr />
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Este documento é um modelo padrão LGPD-compliant para SaaS B2B
        brasileiro. Para uso definitivo, revise com advogado(a) e preencha
        razão social, CNPJ e endereço. Mantenha o e-mail{" "}
        <code>dpo@biazul.com</code> ativo e monitorado.
      </p>
    </article>
  );
}
