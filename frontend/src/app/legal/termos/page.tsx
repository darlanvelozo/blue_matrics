import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Termos de Uso — BI AZUL",
  description: "Termos e condições de uso da plataforma BI AZUL.",
};

export default function TermosPage() {
  return (
    <article>
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Última atualização: 24 de maio de 2026
      </p>
      <h1>Termos de Uso</h1>

      <p>
        Estes Termos de Uso ("Termos") regem o acesso e a utilização da
        plataforma BI AZUL ("Plataforma", "Serviço") disponibilizada por
        [Razão Social a preencher], inscrita no CNPJ sob o nº [a preencher],
        com sede em [endereço a preencher] ("BI AZUL", "nós").
      </p>

      <p>
        Ao criar uma conta, acessar ou utilizar a Plataforma, você ("Usuário",
        "Cliente") declara ter lido, compreendido e aceito integralmente estes
        Termos e a nossa{" "}
        <a href="/legal/privacidade">Política de Privacidade</a>. Se você não
        concorda com qualquer destas condições, não utilize a Plataforma.
      </p>

      <h2>1. Descrição do Serviço</h2>
      <p>
        O BI AZUL é uma plataforma de inteligência de negócios voltada a
        pequenas e médias empresas brasileiras, que se integra ao ERP{" "}
        <strong>Conta Azul</strong> via API oficial para sincronizar dados
        financeiros, comerciais e de estoque do Cliente, oferecendo:
      </p>
      <ul>
        <li>Dashboards e indicadores (KPIs) operacionais e estratégicos;</li>
        <li>
          Análises preditivas e descritivas geradas por inteligência
          artificial;
        </li>
        <li>Assistente conversacional (chat) com IA para consulta dos dados;</li>
        <li>Insights automáticos, alertas e relatórios exportáveis.</li>
      </ul>

      <h2>2. Cadastro e Conta</h2>
      <p>
        Para utilizar o Serviço, o Usuário deve criar uma conta fornecendo
        informações verdadeiras, completas e atualizadas (e-mail, nome,
        nome empresarial). O Usuário é o único responsável pela
        confidencialidade de suas credenciais de acesso.
      </p>
      <p>
        O Usuário compromete-se a notificar imediatamente o BI AZUL sobre
        qualquer uso não autorizado de sua conta. O BI AZUL não se
        responsabiliza por perdas decorrentes do uso indevido de credenciais
        que não tenham sido reportadas.
      </p>

      <h2>3. Planos, Preços e Pagamento</h2>
      <p>
        A Plataforma é oferecida nos seguintes planos de assinatura, com
        cobrança via cartão de crédito ou boleto bancário processada pelo
        provedor Stripe Payments do Brasil:
      </p>
      <ul>
        <li>
          <strong>Mensal</strong> — R$ 299,90 cobrados mensalmente;
        </li>
        <li>
          <strong>Semestral</strong> — R$ 1.649,45 cobrados a cada 6 meses
          (equivalente a R$ 274,91/mês — economia de 8%);
        </li>
        <li>
          <strong>Anual</strong> — R$ 2.999,00 cobrados anualmente (equivalente
          a R$ 249,92/mês — economia de 17%).
        </li>
      </ul>
      <p>
        Todos os valores são em Reais (BRL) e contemplam tributos aplicáveis,
        salvo indicação em contrário. Os preços podem ser reajustados a
        qualquer momento, mediante aviso prévio de 30 dias enviado ao
        e-mail cadastrado; o reajuste passa a valer no início do próximo
        ciclo de cobrança.
      </p>
      <p>
        A renovação é <strong>automática</strong> ao fim de cada ciclo, com
        cobrança no mesmo método de pagamento, exceto se a assinatura for
        cancelada antes do término do período em curso.
      </p>

      <h2>4. Trial Gratuito</h2>
      <p>
        Novas contas têm acesso a um período de avaliação gratuita de{" "}
        <strong>7 (sete) dias</strong>, com todas as funcionalidades
        liberadas. Não há cobrança durante o trial. Para continuar usando o
        Serviço após esse período, o Cliente deve escolher um dos planos
        pagos. Cada empresa tem direito a apenas um trial.
      </p>

      <h2>5. Cancelamento e Reembolso</h2>
      <p>
        A política completa de cancelamento e reembolso está descrita em{" "}
        <a href="/legal/cancelamento">/legal/cancelamento</a>. Em resumo:
      </p>
      <ul>
        <li>
          O cancelamento pode ser feito a qualquer momento dentro da própria
          Plataforma (Painel &gt; Planos &amp; Assinatura);
        </li>
        <li>
          O cancelamento encerra a renovação automática, mas o acesso
          continua disponível até o fim do ciclo já pago;
        </li>
        <li>
          Para compras de planos Semestral e Anual realizadas há até 7 dias
          corridos, o Cliente tem direito ao reembolso integral nos termos
          do Código de Defesa do Consumidor (art. 49 — direito de
          arrependimento).
        </li>
      </ul>

      <h2>6. Uso Aceitável</h2>
      <p>O Usuário compromete-se a NÃO utilizar a Plataforma para:</p>
      <ul>
        <li>Atividades ilegais, fraudulentas ou que violem direitos de terceiros;</li>
        <li>
          Tentar acessar áreas restritas, contas de outros usuários ou dados
          aos quais não tem autorização;
        </li>
        <li>
          Realizar engenharia reversa, decompilação ou cópia não autorizada
          de qualquer parte do Serviço;
        </li>
        <li>
          Sobrecarregar a infraestrutura intencionalmente (testes de
          estresse, varreduras automatizadas, abuso da API);
        </li>
        <li>
          Revender, sublicenciar ou transferir o acesso à Plataforma a
          terceiros sem autorização prévia por escrito.
        </li>
      </ul>
      <p>
        O BI AZUL reserva-se o direito de suspender contas que violem estas
        condições, com prévia notificação quando viável.
      </p>

      <h2>7. Integração com Conta Azul</h2>
      <p>
        A integração com a Conta Azul é feita exclusivamente via OAuth 2.0
        oficial. O BI AZUL <strong>não tem acesso à senha</strong> do Cliente
        e atua sob o escopo de permissões autorizado pelo Cliente.
        O Cliente pode revogar essa autorização a qualquer momento pelo
        próprio painel da Conta Azul ou pelo nosso painel.
      </p>
      <p>
        O BI AZUL não se responsabiliza por indisponibilidades, alterações
        ou descontinuações da API da Conta Azul que afetem a sincronização
        de dados.
      </p>

      <h2>8. Propriedade Intelectual</h2>
      <p>
        Todo o conteúdo, código-fonte, marca, layout, design e funcionalidades
        da Plataforma são de propriedade exclusiva do BI AZUL, protegidos
        pelas leis brasileiras de propriedade intelectual.
      </p>
      <p>
        <strong>Os dados do Cliente</strong> permanecem de propriedade do
        Cliente. O BI AZUL recebe uma licença não exclusiva para processá-los
        e armazená-los exclusivamente com o fim de prestar o Serviço.
        Detalhes em nossa{" "}
        <a href="/legal/privacidade">Política de Privacidade</a>.
      </p>

      <h2>9. Limitação de Responsabilidade</h2>
      <p>
        A Plataforma é fornecida "no estado em que se encontra". Embora
        nos esforcemos para manter alta disponibilidade e precisão dos
        dados, o BI AZUL NÃO garante:
      </p>
      <ul>
        <li>
          Disponibilidade ininterrupta (eventuais janelas de manutenção
          ou indisponibilidade de fornecedores podem ocorrer);
        </li>
        <li>
          Que os insights gerados por IA sejam livres de erros — eles devem
          ser interpretados como apoio à decisão, não como aconselhamento
          financeiro, contábil ou jurídico;
        </li>
        <li>
          Resultados financeiros específicos a partir do uso da Plataforma.
        </li>
      </ul>
      <p>
        Em qualquer hipótese, a responsabilidade total do BI AZUL fica
        limitada ao valor pago pelo Cliente nos últimos 12 (doze) meses,
        respeitadas as exceções legais aplicáveis.
      </p>

      <h2>10. Suspensão e Encerramento</h2>
      <p>
        O BI AZUL pode suspender ou encerrar o acesso do Cliente nas
        seguintes hipóteses:
      </p>
      <ul>
        <li>Falta de pagamento após 15 dias do vencimento;</li>
        <li>Violação destes Termos ou da legislação aplicável;</li>
        <li>
          Determinação judicial ou requisição de autoridade competente.
        </li>
      </ul>

      <h2>11. Alterações destes Termos</h2>
      <p>
        Estes Termos podem ser atualizados periodicamente. Alterações
        materiais serão notificadas com antecedência mínima de 15 dias
        por e-mail e/ou aviso na Plataforma. O uso continuado após a
        vigência das alterações implica aceitação.
      </p>

      <h2>12. Lei Aplicável e Foro</h2>
      <p>
        Estes Termos são regidos pelas leis da República Federativa do
        Brasil. Fica eleito o foro da Comarca de [Cidade/UF a preencher]
        para dirimir quaisquer controvérsias, com renúncia expressa a
        qualquer outro, por mais privilegiado que seja.
      </p>

      <h2>13. Contato</h2>
      <p>
        Para questões legais, contratuais ou comerciais:{" "}
        <a href="mailto:legal@biazul.com">legal@biazul.com</a>
        <br />
        Para suporte:{" "}
        <a href="mailto:suporte@biazul.com">suporte@biazul.com</a>
      </p>

      <hr />
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Este documento é um modelo padrão para SaaS B2B brasileiro. Antes
        do uso definitivo em produção, recomendamos revisão por advogado(a)
        de sua confiança, especialmente para preencher dados de razão social,
        CNPJ, endereço e foro.
      </p>
    </article>
  );
}
