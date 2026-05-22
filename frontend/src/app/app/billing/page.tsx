import { CreditCard } from "lucide-react";
import { ComingSoon } from "@/components/app/coming-soon";

export default function BillingPage() {
  return (
    <ComingSoon
      icon={CreditCard}
      title="Planos & Assinatura"
      description="Gerencie sua assinatura, faturas e plano. Você está no trial de 7 dias — sem cartão necessário."
      features={[
        "Plano atual (Starter, Growth ou Business)",
        "Histórico de faturas em PDF",
        "Trocar de plano com pró-rateio",
        "Cancelar com 1 clique, sem fidelidade",
      ]}
    />
  );
}
