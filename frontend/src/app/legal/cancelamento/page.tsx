import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Política de Cancelamento e Reembolso — BI AZUL",
  description:
    "Como cancelar sua assinatura BI AZUL e quando você tem direito a reembolso.",
};

export default function CancelamentoPage() {
  return (
    <article>
      <p className="text-xs text-[color:var(--muted-foreground)]">
        Última atualização: 24 de maio de 2026
      </p>
      <h1>Política de Cancelamento e Reembolso</h1>

      <p>
        Esta política descreve como cancelar sua assinatura no BI AZUL e
        quando você tem direito a reembolso. Foi escrita em linguagem
        simples para facilitar a leitura.
      </p>

      <h2>1. Como Cancelar (3 cliques, sem ligação)</h2>
      <ol>
        <li>
          Acesse a área logada em{" "}
          <Link href="/app/billing">biazul.com/app/billing</Link>.
        </li>
        <li>Clique em <strong>"Cancelar assinatura"</strong>.</li>
        <li>Confirme — pronto.</li>
      </ol>
      <p>
        O cancelamento é instantâneo. Você não precisa entrar em contato
        com suporte, ligar ou enviar e-mail. Não há fidelidade, multa nem
        burocracia.
      </p>

      <h2>2. O que Acontece após o Cancelamento</h2>
      <ul>
        <li>
          <strong>A renovação automática é encerrada</strong> — você não será
          cobrado novamente.
        </li>
        <li>
          <strong>Seu acesso continua disponível até o fim do ciclo já pago</strong>.
          Exemplo: se você está no plano Anual e cancelou no 4º mês, você
          continua usando até o 12º mês.
        </li>
        <li>
          Após o fim do ciclo, a conta entra em modo "leitura" por 30 dias,
          permitindo que você exporte seus dados (Painel &gt; Configurações
          &gt; Exportar dados).
        </li>
        <li>
          Após 30 dias, todos os dados são excluídos definitivamente — exceto
          faturas e dados fiscais retidos por obrigação legal (5 anos).
        </li>
      </ul>

      <h2>3. Reembolso</h2>

      <h3>3.1 Trial gratuito</h3>
      <p>
        Durante o trial de 7 dias não há cobrança. Não se aplica reembolso.
      </p>

      <h3>3.2 Plano Mensal</h3>
      <p>
        Devido ao baixo valor mensal, <strong>não oferecemos reembolso
        proporcional</strong> em cancelamentos no meio do mês. Você mantém
        acesso até o fim do ciclo já pago e a renovação seguinte é cancelada.
      </p>

      <h3>3.3 Planos Semestral e Anual</h3>
      <p>
        Para compras dos planos Semestral (R$ 1.649,45) e Anual (R$ 2.999),
        você tem dois caminhos de reembolso:
      </p>
      <ul>
        <li>
          <strong>Até 7 dias corridos após a compra:</strong> reembolso
          integral, conforme o direito de arrependimento previsto no art. 49
          do Código de Defesa do Consumidor. Solicitação via{" "}
          <a href="mailto:suporte@biazul.com">suporte@biazul.com</a>.
        </li>
        <li>
          <strong>Após 7 dias:</strong> o cancelamento encerra a renovação,
          mas não há reembolso dos meses restantes do ciclo já pago. Você
          mantém acesso até o fim do período.
        </li>
      </ul>
      <p>
        <em>Exceção:</em> se a Plataforma apresentar indisponibilidade severa
        documentada por mais de 30 dias acumulados em um mesmo ciclo,
        avaliamos reembolso proporcional caso a caso.
      </p>

      <h2>4. Como Solicitar Reembolso</h2>
      <ol>
        <li>
          Envie um e-mail para{" "}
          <a href="mailto:suporte@biazul.com">suporte@biazul.com</a> com:
          <ul>
            <li>Nome da sua empresa cadastrada;</li>
            <li>E-mail da conta;</li>
            <li>Data da compra;</li>
            <li>Motivo (opcional, ajuda a melhorar o serviço).</li>
          </ul>
        </li>
        <li>Confirmamos o recebimento em até 1 dia útil.</li>
        <li>
          O reembolso é processado em até 5 dias úteis, pelo mesmo método
          de pagamento original (cartão de crédito ou boleto). O Stripe e
          o emissor do cartão podem levar mais alguns dias para refletir
          o crédito.
        </li>
      </ol>

      <h2>5. Cobrança Não Autorizada</h2>
      <p>
        Se você identificou uma cobrança que não autorizou:
      </p>
      <ol>
        <li>
          Envie um e-mail urgente para{" "}
          <a href="mailto:suporte@biazul.com">suporte@biazul.com</a> com
          detalhes da cobrança.
        </li>
        <li>
          Em paralelo, contate seu banco/emissor do cartão para registrar a
          contestação (chargeback).
        </li>
        <li>
          Vamos investigar imediatamente e, comprovada a cobrança indevida,
          o reembolso é integral.
        </li>
      </ol>

      <h2>6. Reativação</h2>
      <p>
        Mudou de ideia? Dentro dos 30 dias após o fim do ciclo, basta logar
        e reativar — sua conta volta exatamente do mesmo ponto, com todos
        os dados intactos. Após 30 dias, você precisa criar uma nova conta
        (sem dados antigos).
      </p>

      <h2>7. Contato</h2>
      <p>
        <a href="mailto:suporte@biazul.com">suporte@biazul.com</a> —
        respondemos em até 1 dia útil (segunda a sexta).
      </p>
    </article>
  );
}
