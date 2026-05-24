import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { CookieConsent } from "@/components/cookie-consent";
import { Providers } from "@/components/providers";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const SITE_URL = "https://biazul.com";
const SITE_NAME = "BI AZUL";
const TITLE = "BI AZUL — Copiloto financeiro com IA para Conta Azul";
const DESCRIPTION =
  "Conecte sua Conta Azul e veja os números do seu negócio em minutos. Dashboards inteligentes, Analista IA conversacional, previsões de caixa e curva ABC. Teste grátis por 7 dias.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s — BI AZUL",
  },
  description: DESCRIPTION,
  keywords: [
    "BI Conta Azul",
    "Business Intelligence PME",
    "copiloto financeiro",
    "dashboard Conta Azul",
    "IA para empresas brasileiras",
    "análise financeira PME",
  ],
  authors: [{ name: "BI AZUL" }],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: TITLE,
    description: DESCRIPTION,
    images: [
      {
        url: `${SITE_URL}/og-image.png`,
        width: 1200,
        height: 630,
        alt: "BI AZUL — copiloto financeiro com IA",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: [`${SITE_URL}/og-image.png`],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-[color:var(--background)] text-[color:var(--foreground)]">
        <Providers>{children}</Providers>
        <CookieConsent />
      </body>
    </html>
  );
}
