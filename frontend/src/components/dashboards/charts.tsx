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
  if (Math.abs(v) >= 1_000_000) {
    return `R$ ${(v / 1_000_000).toFixed(1).replace(".", ",")}M`;
  }
  if (Math.abs(v) >= 1000) {
    return `R$ ${(v / 1000).toFixed(1).replace(".", ",")}k`;
  }
  return `R$ ${v.toFixed(0)}`;
}

const MONTHS_PT = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

function fmtMonthShort(ym: string) {
  const [y, m] = ym.split("-");
  const abbrev = MONTHS_PT[Number(m) - 1].slice(0, 3);
  return `${abbrev}/${y.slice(2)}`;
}

function fmtMonthLong(ym: string) {
  const [y, m] = ym.split("-");
  return `${MONTHS_PT[Number(m) - 1]} de ${y}`;
}

// ---------------------------------------------------------------------------
// Tooltip rico: mostra mês completo + valor formatado + comparação opcional
// ---------------------------------------------------------------------------
function RichTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name: string; color?: string; dataKey: string }>;
  label?: string;
}) {
  if (!active || !payload || payload.length === 0 || !label) return null;
  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--card)] px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold capitalize">{fmtMonthLong(String(label))}</p>
      <ul className="space-y-0.5">
        {payload.map((p) => (
          <li key={p.dataKey} className="flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: p.color }}
            />
            <span className="text-[color:var(--muted-foreground)]">{p.name}:</span>
            <span className="font-mono font-semibold">{formatCurrencyBRL(p.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
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
          tickFormatter={fmtMonthShort}
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
        <Tooltip content={<RichTooltip />} />
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
          tickFormatter={fmtMonthShort}
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
        <Tooltip content={<RichTooltip />} />
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
          tickFormatter={fmtMonthShort}
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
        <Tooltip content={<RichTooltip />} />
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

// ---------------------------------------------------------------------------
// Sparkline mini-chart para usar dentro de KpiCard
// ---------------------------------------------------------------------------
export function Sparkline({
  data,
  color = palette.primary,
  height = 36,
}: {
  data: Array<{ value: number }>;
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#spark-${color})`}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
