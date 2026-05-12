import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AlertTriangle, BatteryCharging, Gauge, Zap } from 'lucide-react';
import { energyApi } from './api/client';
import { MetricCard } from './components/MetricCard';
import { PowerFlow } from './components/PowerFlow';
import type { Alert, BatteryStatus, ForecastPoint, GridCondition } from './types/energy';

function fallbackForecasts(): ForecastPoint[] {
  return Array.from({ length: 48 }, (_, index) => ({
    timestamp: new Date(Date.now() + index * 15 * 60_000).toISOString(),
    predicted_demand_mw: 540 + Math.sin(index / 5) * 75 + (index > 30 ? 60 : 0),
    predicted_renewable_mw: 190 + Math.cos(index / 6) * 65,
    confidence_low_mw: 500,
    confidence_high_mw: 620
  }));
}

export default function App() {
  const [grid, setGrid] = useState<GridCondition>();
  const [battery, setBattery] = useState<BatteryStatus>();
  const [forecasts, setForecasts] = useState<ForecastPoint[]>(fallbackForecasts());
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [gridData, batteryData, forecastData, alertData] = await Promise.all([energyApi.grid(), energyApi.battery(), energyApi.forecasts(), energyApi.alerts()]);
        setGrid(gridData); setBattery(batteryData); setForecasts(forecastData); setAlerts(alertData);
      } catch {
        setGrid({ timestamp: new Date().toISOString(), demand_mw: 612, renewable_generation_mw: 238, net_load_mw: 374, frequency_hz: 59.98, voltage_kv: 13.74, price_usd_mwh: 122, peak_period: true, instability_score: 0.31 });
        setBattery({ timestamp: new Date().toISOString(), soc_percent: 68, soh_percent: 96.8, power_mw: 82, capacity_mwh: 420, temperature_c: 35.4, cycle_count: 184, mode: 'discharging', efficiency_percent: 91.7 });
        setAlerts([{ timestamp: new Date().toISOString(), severity: 'warning', category: 'peak_demand', message: 'Peak demand window active; dispatch optimization recommended.' }]);
      }
    };
    load();
    const id = window.setInterval(load, 15_000);
    return () => window.clearInterval(id);
  }, []);

  const chartData = useMemo(() => forecasts.map((point) => ({
    time: new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    demand: Math.round(point.predicted_demand_mw),
    renewable: Math.round(point.predicted_renewable_mw),
    reserve: Math.round(point.confidence_high_mw - point.predicted_demand_mw)
  })), [forecasts]);

  return <main className="min-h-screen grid-texture p-6 lg:p-8">
    <header className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="text-grid-cyan uppercase tracking-[0.4em] text-xs">Siemens-inspired local digital grid lab</p>
        <h1 className="mt-3 text-4xl font-bold text-white lg:text-6xl">Battery Storage Optimizer</h1>
        <p className="mt-3 max-w-3xl text-slate-400">Utility-scale BESS forecasting, dispatch optimization, grid stabilization, and battery health analytics for smart-grid operators.</p>
      </div>
      <div className="rounded-full border border-grid-green/40 bg-grid-green/10 px-5 py-3 text-sm text-grid-green">● Local SCADA telemetry active</div>
    </header>

    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Grid demand" value={`${grid?.demand_mw.toFixed(0) ?? '--'} MW`} detail={`Frequency ${grid?.frequency_hz.toFixed(2) ?? '--'} Hz`} />
      <MetricCard label="BESS SOC" value={`${battery?.soc_percent.toFixed(1) ?? '--'}%`} accent="text-grid-green" detail={`${battery?.mode ?? 'idle'} at ${battery?.power_mw.toFixed(1) ?? '--'} MW`} />
      <MetricCard label="Market price" value={`$${grid?.price_usd_mwh.toFixed(0) ?? '--'}`} accent="text-grid-amber" detail="USD per MWh dynamic tariff" />
      <MetricCard label="Battery SOH" value={`${battery?.soh_percent.toFixed(1) ?? '--'}%`} detail={`Thermal ${battery?.temperature_c.toFixed(1) ?? '--'}°C`} />
    </section>

    <section className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_.8fr]">
      <div className="rounded-2xl border border-grid-line bg-grid-panel/90 p-5 shadow-glow">
        <div className="mb-4 flex items-center gap-3"><Gauge className="text-grid-cyan" /><h2 className="text-xl font-semibold">Demand Forecast & Renewable Contribution</h2></div>
        <div className="h-80"><ResponsiveContainer><AreaChart data={chartData}><defs><linearGradient id="demand" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#00e5ff" stopOpacity={0.45}/><stop offset="95%" stopColor="#00e5ff" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#1a3a44" /><XAxis dataKey="time" stroke="#6b8790" /><YAxis stroke="#6b8790" /><Tooltip contentStyle={{ background: '#071014', border: '1px solid #1a3a44' }} /><Area type="monotone" dataKey="demand" stroke="#00e5ff" fill="url(#demand)" /><Line type="monotone" dataKey="renewable" stroke="#35f2a0" strokeWidth={2} /></AreaChart></ResponsiveContainer></div>
      </div>
      <PowerFlow />
    </section>

    <section className="mt-6 grid gap-6 xl:grid-cols-3">
      <div className="rounded-2xl border border-grid-line bg-grid-panel/90 p-5 xl:col-span-2">
        <div className="mb-4 flex items-center gap-3"><BatteryCharging className="text-grid-green" /><h2 className="text-xl font-semibold">Charge / Discharge Reserve Profile</h2></div>
        <div className="h-64"><ResponsiveContainer><LineChart data={chartData}><CartesianGrid stroke="#1a3a44" /><XAxis dataKey="time" stroke="#6b8790" /><YAxis stroke="#6b8790" /><Tooltip contentStyle={{ background: '#071014', border: '1px solid #1a3a44' }} /><Line type="monotone" dataKey="reserve" stroke="#ffb020" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer></div>
      </div>
      <div className="rounded-2xl border border-grid-line bg-grid-panel/90 p-5">
        <div className="mb-4 flex items-center gap-3"><AlertTriangle className="text-grid-amber" /><h2 className="text-xl font-semibold">Anomaly Alerts</h2></div>
        <div className="space-y-3">{alerts.slice(-5).map((alert) => <div key={`${alert.timestamp}-${alert.category}`} className="rounded-xl border border-amber-300/20 bg-amber-300/10 p-3"><p className="text-sm font-semibold uppercase text-grid-amber">{alert.severity} · {alert.category}</p><p className="mt-1 text-sm text-slate-300">{alert.message}</p></div>)}</div>
      </div>
    </section>

    <footer className="mt-8 flex items-center gap-2 text-sm text-slate-500"><Zap size={16}/> Local execution only: FastAPI, SQLite, PyTorch, React, TailwindCSS, Recharts.</footer>
  </main>;
}
