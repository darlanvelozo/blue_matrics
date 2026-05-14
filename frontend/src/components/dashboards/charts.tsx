"use client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrencyBRL } from "@/lib/utils";

const palette = {
  primary: "#3b82f6",
  secondary: "#8b5cf6",
  positive: "#16a34a",
  negative: "#dc2626",
  muted: "#94a3b8",
};

function compactBRL(v: number) {
  if (Math.abs(v) >= 1000) {
    return `R$ ${(v / 1000).toFixed(1).replace(".", ",")}k`;
  }
  return `R$ ${v.toFixed(0)}`;
}

function fmtMonth(ym: string) {
  // "2026-04" → "abr/26"
  const [y, m] = ym.split("-");
  const months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  return `${months[Number(m) - 1]}/${y.slice(2)}`;
}

interface RevenueDatum {
  month: string;
  revenue: number;
  sales_count: number;
}

export function RevenueChart({ data }: { data: RevenueDatum[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="rev-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={palette.primary} stopOpacity={0.5} />
            <stop offset="100%" stopColor={palette.primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
        <XAxis
          dataKey="month"
          tickFormatter={fmtMonth}
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tickFormatter={compactBRL}
        />
        <Tooltip
          formatter={(v) => formatCurrencyBRL(Number(v))}
          labelFormatter={(l) => fmtMonth(String(l))}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          dataKey="revenue"
          name="Faturamento"
          stroke={palette.primary}
          strokeWidth={2}
          fill="url(#rev-grad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

interface CashflowDatum {
  month: string;
  in: number;
  out: number;
  net: number;
}

export function CashflowChart({ data }: { data: CashflowDatum[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
        <XAxis
          dataKey="month"
          tickFormatter={fmtMonth}
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tickFormatter={compactBRL}
        />
        <Tooltip
          formatter={(v) => formatCurrencyBRL(Number(v))}
          labelFormatter={(l) => fmtMonth(String(l))}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="in" name="Entradas" fill={palette.positive} radius={[4, 4, 0, 0]} />
        <Bar dataKey="out" name="Saídas" fill={palette.negative} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function NetProfitChart({ data }: { data: CashflowDatum[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
        <XAxis
          dataKey="month"
          tickFormatter={fmtMonth}
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke={palette.muted}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tickFormatter={compactBRL}
        />
        <Tooltip
          formatter={(v) => formatCurrencyBRL(Number(v))}
          labelFormatter={(l) => fmtMonth(String(l))}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Line
          dataKey="net"
          name="Lucro líquido"
          stroke={palette.secondary}
          strokeWidth={2.5}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
