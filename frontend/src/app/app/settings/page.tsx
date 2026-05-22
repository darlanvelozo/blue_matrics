import { Settings } from "lucide-react";
import { ComingSoon } from "@/components/app/coming-soon";

export default function SettingsPage() {
  return (
    <ComingSoon
      icon={Settings}
      title="Configurações"
      description="Personalize sua experiência no BlueMetrics."
      features={[
        "Dados da empresa (nome, CNPJ, logo)",
        "Equipe — convidar usuários e definir permissões",
        "Notificações por e-mail (alertas, resumo diário)",
        "Exportar/excluir dados — conformidade com LGPD",
      ]}
    />
  );
}
