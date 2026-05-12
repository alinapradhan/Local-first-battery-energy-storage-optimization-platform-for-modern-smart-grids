export function PowerFlow() {
  return <div className="relative min-h-72 rounded-2xl border border-grid-line bg-grid-panel/80 p-6 overflow-hidden">
    <div className="absolute inset-0 grid-texture opacity-60" />
    <div className="relative grid grid-cols-3 gap-8 text-center">
      {['Renewables', 'BESS', 'Smart Grid'].map((label, idx) => <div key={label} className="rounded-xl border border-cyan-400/30 bg-slate-950/70 p-5">
        <div className={`mx-auto mb-3 h-20 w-20 rounded-full border ${idx === 1 ? 'border-grid-green shadow-[0_0_35px_rgba(53,242,160,.35)]' : 'border-grid-cyan shadow-[0_0_35px_rgba(0,229,255,.25)]'} flex items-center justify-center text-2xl`}>{idx === 0 ? '☀' : idx === 1 ? '▰' : '⌁'}</div>
        <p className="text-sm uppercase tracking-[0.25em] text-slate-300">{label}</p>
      </div>)}
    </div>
    <div className="relative mt-8 h-2 rounded-full bg-gradient-to-r from-grid-green via-grid-cyan to-grid-amber animate-pulse" />
    <p className="relative mt-5 text-sm text-slate-400">Digital twin power-flow view: renewable surplus is routed into storage, then dispatched during feeder stress or high-price intervals.</p>
  </div>;
}
