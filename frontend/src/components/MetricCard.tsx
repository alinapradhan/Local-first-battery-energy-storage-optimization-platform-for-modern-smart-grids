interface Props { label: string; value: string; accent?: string; detail: string; }
export function MetricCard({ label, value, accent = 'text-grid-cyan', detail }: Props) {
  return <div className="rounded-2xl border border-grid-line bg-grid-panel/90 p-5 shadow-glow">
    <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{label}</p>
    <div className={`mt-3 text-3xl font-semibold ${accent}`}>{value}</div>
    <p className="mt-2 text-sm text-slate-400">{detail}</p>
  </div>;
}
