import React, { useState, useEffect } from 'react';
import { 
  Settings, Database, Play, BarChart3, Info, Shield, 
  Wallet, Activity, CheckCircle2, XCircle, Clock, ChevronRight
} from 'lucide-react';
import axios from 'axios';

// Premium Shadow/Blur effects
const GlassCard = ({ children, className = "" }) => (
  <div className={`bg-zinc-950/40 border border-zinc-900 rounded-none p-8 backdrop-blur-xl ${className}`}>
    {children}
  </div>
);

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [config, setConfig] = useState([]);
  const [wallet, setWallet] = useState(10000);
  const [signals, setSignals] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [confRes, wallRes, sigRes, telRes] = await Promise.all([
        axios.get('/api/config'),
        axios.get('/api/wallet'),
        axios.get('/api/signals'),
        axios.get('/api/market-intel/overview')
      ]);
      setConfig(confRes.data);
      setWallet(wallRes.data.balance);
      setSignals(sigRes.data);
      setTelemetry(telRes.data);
      setLoading(false);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  };

  const updateConfig = async (key, val) => {
    try {
      await axios.post('/api/config', { [key]: val });
      setConfig(prev => prev.map(c => c.key === key ? { ...c, value: val } : c));
      // Refresh telemetry after config update
      const tel = await axios.get('/api/market-intel/overview');
      setTelemetry(tel.data);
    } catch (err) { alert("Update Failed"); }
  };

  if (loading) return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-t-2 border-white animate-spin" />
        <span className="text-[10px] uppercase tracking-[0.4em] font-bold">Establishing Secure Link</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans hyper-bg flex flex-col selection:bg-white selection:text-black">
      {/* Top Navigation Bar */}
      <header className="fixed top-0 left-0 right-0 h-20 border-b border-zinc-900 bg-black/80 backdrop-blur-md z-50 flex items-center justify-between px-12">
        <div className="flex items-center gap-4 group cursor-default">
          <Shield className="w-6 h-6 text-white group-hover:text-emerald-500 transition-colors" />
          <h1 className="text-xl font-black tracking-tighter uppercase italic">SNIPER <span className="font-light text-zinc-500">v10.2</span></h1>
        </div>
        
        <nav className="flex items-center gap-1">
          {[
            { id: 'dashboard', label: 'Overview', icon: BarChart3 },
            { id: 'settings', label: 'Settings', icon: Settings },
            { id: 'signals', label: 'Signal DB', icon: Database },
            { id: 'emulator', label: 'Emulator', icon: Play },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-2 text-[10px] uppercase font-bold tracking-[0.2em] transition-all flex items-center gap-2 ${
                activeTab === tab.id ? 'text-white border-b border-white' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/40'
              }`}
            >
              <tab.icon size={12} />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-[9px] uppercase tracking-widest text-zinc-500">Live Capital</span>
            <span className="text-sm font-bold tabular-nums">${wallet.toLocaleString()}</span>
          </div>
          <div className="w-10 h-10 border border-zinc-900 flex items-center justify-center bg-zinc-950 hover:border-emerald-500 transition-colors group cursor-pointer">
             <Activity className={`w-4 h-4 ${telemetry?.status === 'active' ? 'text-emerald-500 animate-pulse' : 'text-zinc-700'}`} />
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 mt-20 p-12 max-w-[1440px] mx-auto w-full">
        {activeTab === 'dashboard' && <Dashboard config={config} wallet={wallet} telemetry={telemetry} signals={signals} />}
        {activeTab === 'settings' && <SettingsTab config={config} onUpdate={updateConfig} />}
        {activeTab === 'signals' && <SignalsTab signals={signals} />}
        {activeTab === 'emulator' && <EmulatorTab wallet={wallet} />}
      </main>
    </div>
  );
};

const Dashboard = ({ config, wallet, telemetry, signals }) => (
  <div className="grid grid-cols-12 gap-1 px-4 animate-in fade-in duration-700">
    <div className="col-span-8 space-y-1">
      <GlassCard className="h-[430px] flex flex-col justify-end relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-8">
           <span className="text-[10px] uppercase tracking-[0.4em] text-zinc-800 font-bold group-hover:text-zinc-700 transition-colors">Encrypted Stream</span>
        </div>
        <h2 className="text-7xl font-black tracking-tighter uppercase leading-[0.8] mb-8">
          Intelligence<br/>Terminal
        </h2>
        <div className="flex gap-12 text-[10px] uppercase tracking-[0.3em] font-bold text-zinc-500">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${telemetry?.status === 'active' ? 'bg-emerald-500 shadow-[0_0_8px_#10b981]' : 'bg-rose-500'}`} /> 
            System {telemetry?.status || 'Unknown'}
          </div>
          <div>Location: US-East-Primary</div>
          <div>Lat: 0.04ms</div>
        </div>
      </GlassCard>
      
      <div className="grid grid-cols-2 gap-1">
        <GlassCard className="hover:bg-zinc-900/60 transition-colors cursor-default">
          <span className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-4 font-bold">Trading Mode</span>
          <span className="text-3xl font-black italic uppercase tracking-tighter text-white">
            {telemetry?.mode || 'OFFLINE'}
          </span>
        </GlassCard>
        <GlassCard className="hover:bg-zinc-900/60 transition-colors cursor-default">
          <span className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-4 font-bold">Network State</span>
          <span className={`text-3xl font-black uppercase tracking-tighter ${telemetry?.connection === 'optimized' ? 'text-emerald-500' : 'text-zinc-500'}`}>
            {telemetry?.connection?.toUpperCase() || 'DISCONNECTED'}
          </span>
        </GlassCard>
      </div>
    </div>

    <div className="col-span-4 space-y-1">
      <GlassCard className="h-full flex flex-col">
        <span className="text-[10px] uppercase tracking-widest text-zinc-500 block mb-8 font-bold">System Telemetry</span>
        <div className="space-y-6 flex-1">
           {[
             { label: 'Scout Depth', val: `Top ${telemetry?.scout_limit || 0}` },
             { label: 'AI Audit Max', val: `${telemetry?.audit_limit || 0} Symbols` },
             { label: 'Scan Interval', val: `${telemetry?.interval_min || 0} min` },
             { label: 'Min Volatility', val: `${telemetry?.min_vol || 0}%` },
             { label: 'Security Layer', val: 'Active' },
             { label: 'Last Scan', val: telemetry?.last_scan ? new Date(telemetry.last_scan).toLocaleTimeString() : 'Pending' }
           ].map(t => (
             <div key={t.label} className="flex justify-between items-end border-b border-zinc-900 pb-2 group/item">
               <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-600 group-hover/item:text-zinc-400 transition-colors">{t.label}</span>
               <span className="text-xs font-black uppercase tracking-tight text-zinc-200">{t.val}</span>
             </div>
           ))}
        </div>
        
        {signals.length > 0 && (
          <div className="mt-8 p-4 bg-zinc-900/40 border border-zinc-800">
             <span className="text-[9px] uppercase tracking-[0.2em] text-zinc-500 block mb-2 font-bold">Latest Alert</span>
             <div className="flex justify-between items-center">
                <span className="text-sm font-black italic tracking-tighter uppercase">{signals[0].symbol}</span>
                <span className={`text-[10px] font-black uppercase tracking-widest ${signals[0].verdict === 'buy' ? 'text-emerald-500' : 'text-rose-500'}`}>
                  {signals[0].verdict}
                </span>
             </div>
          </div>
        )}

        <div className={`mt-4 p-4 ${telemetry?.status === 'active' ? 'bg-emerald-500/5 text-emerald-500 border-emerald-500/20' : 'bg-rose-500/5 text-rose-500 border-rose-500/20'} border text-[10px] font-black uppercase tracking-[0.2em] text-center`}>
          {telemetry?.status === 'active' ? 'All Systems Nominal' : 'System Connectivity Required'}
        </div>
      </GlassCard>
    </div>
  </div>
);

const SettingsTab = ({ config, onUpdate }) => (
  <div className="grid grid-cols-12 gap-1 px-4 animate-in slide-in-from-right-4 duration-500">
     <div className="col-span-12 mb-12">
        <h2 className="text-6xl font-black tracking-tighter uppercase mb-4">Configurations</h2>
        <div className="h-1 w-32 bg-white" />
     </div>

     <div className="col-span-12 grid grid-cols-1 gap-8 pb-32">
        {['Scouting', 'AI Audit', 'Risk Control', 'Whale Tech', 'Emulator', 'System'].map(section => (
          <div key={section} className="space-y-1">
             <div className="p-4 bg-zinc-900/50 text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500">{section}</div>
             {config.filter(c => c.category === section).map(item => (
               <div key={item.key} className="glass p-8 flex items-center justify-between group hover:bg-zinc-800/20 transition-all">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                       <span className="text-sm font-black uppercase tracking-tight">{item.key.replace(/_/g, ' ')}</span>
                       <div className="relative group/tip">
                         <Info size={12} className="text-zinc-700 hover:text-white transition-colors cursor-help" />
                         <div className="absolute left-0 bottom-full mb-2 w-64 p-4 bg-white text-black text-[10px] font-bold uppercase tracking-wider opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all z-50">
                            {item.description}
                         </div>
                       </div>
                    </div>
                  </div>
                  <input 
                    type="text"
                    defaultValue={item.value}
                    onBlur={(e) => onUpdate(item.key, e.target.value)}
                    className="bg-transparent border-b border-zinc-800 focus:border-white outline-none text-right font-black tabular-nums transition-all w-24 text-lg"
                  />
               </div>
             ))}
          </div>
        ))}
     </div>
  </div>
);

const SignalsTab = ({ signals }) => (
  <div className="px-4 animate-in slide-in-from-bottom-4 duration-500">
     <div className="mb-12">
        <h2 className="text-6xl font-black tracking-tighter uppercase mb-4">Signal Database</h2>
        <p className="text-zinc-500 text-xs uppercase tracking-[0.2em] font-bold">Archive of the last 50 AI analytical verdicts</p>
     </div>

     <div className="border border-zinc-900">
        <table className="w-full text-left">
           <thead>
              <tr className="bg-zinc-900/50 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                 <th className="px-8 py-4">Symbol</th>
                 <th className="px-8 py-4">Verdict</th>
                 <th className="px-8 py-4">Confidence</th>
                 <th className="px-8 py-4">Strategy Metrics</th>
                 <th className="px-8 py-4">Timestamp</th>
              </tr>
           </thead>
           <tbody className="divide-y divide-zinc-900 border-t border-zinc-900">
              {signals.map((s, i) => (
                <tr key={i} className="hover:bg-zinc-900/20 transition-all group">
                   <td className="px-8 py-6 font-black text-xl italic tracking-tighter">{s.symbol}</td>
                   <td className="px-8 py-6">
                      <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-3 py-1 ${
                        s.verdict === 'buy' ? 'bg-emerald-500 text-black' : 
                        s.verdict === 'sell' ? 'bg-rose-500 text-black' : 'text-zinc-500'
                      }`}>
                        {s.verdict}
                      </span>
                   </td>
                   <td className="px-8 py-6 tabular-nums font-bold">{s.confidence}%</td>
                   <td className="px-8 py-6 text-[10px] text-zinc-500 italic max-w-sm truncate">{s.reasoning}</td>
                   <td className="px-8 py-6 text-zinc-600 text-[10px] font-mono">{new Date(s.time).toLocaleString()}</td>
                </tr>
              ))}
           </tbody>
        </table>
     </div>
  </div>
);

const EmulatorTab = () => {
  const [simulating, setSimulating] = useState(false);
  const [res, setRes] = useState(null);

  const runSim = async () => {
    setSimulating(true);
    try {
      const { data } = await axios.post('/api/emulator/run');
      setRes(data);
    } finally { setSimulating(false); }
  };

  return (
    <div className="px-4 animate-in fade-in duration-500">
      <div className="mb-12">
        <h2 className="text-6xl font-black tracking-tighter uppercase mb-4">Backtest Engine</h2>
        <p className="text-zinc-500 text-xs uppercase tracking-[0.2em] font-bold">Simulating verified signals against Bybit M1 candles</p>
      </div>

      <div className="grid grid-cols-12 gap-1">
        <div className="col-span-4">
           <GlassCard className="h-full flex flex-col justify-between">
              <div>
                <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 mb-8">Initialization</h3>
                <p className="text-sm text-zinc-400 leading-relaxed mb-8">
                  Run a full cycle simulation on the last 50 verified signals to determine historical accuracy and drawdown.
                </p>
              </div>
              <button 
                onClick={runSim}
                disabled={simulating}
                className="w-full h-16 bg-white text-black font-black uppercase tracking-[0.3em] hover:bg-zinc-200 transition-all flex items-center justify-center gap-4 disabled:opacity-50"
              >
                {simulating ? <Activity className="animate-spin" /> : <Play />}
                {simulating ? "In Course" : "Execute Scan"}
              </button>
           </GlassCard>
        </div>

        <div className="col-span-8">
           {res ? (
             <div className="grid grid-cols-3 gap-1">
                <div className="glass p-12 col-span-1">
                   <span className="text-[10px] font-black uppercase text-zinc-500 mb-4 block">Winrate</span>
                   <span className="text-6xl font-black tracking-tighter text-emerald-500">{res.stats.winrate.toFixed(0)}%</span>
                </div>
                <div className="glass p-12 col-span-2">
                   <span className="text-[10px] font-black uppercase text-zinc-500 mb-4 block">Accumulated PnL</span>
                   <span className={`text-6xl font-black tracking-tighter ${res.stats.total_pnl >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {res.stats.total_pnl >= 0 ? '+' : ''}{res.stats.total_pnl.toFixed(2)}%
                   </span>
                </div>
                
                <div className="col-span-3 border border-zinc-900 bg-black mt-1">
                   <div className="p-4 bg-zinc-900/50 text-[10px] font-black uppercase tracking-widest text-zinc-500">Top Outcomes</div>
                   <table className="w-full text-left text-[10px]">
                      <tbody>
                        {res.trades.slice(0, 5).map((t, i) => (
                          <tr key={i} className="border-t border-zinc-900">
                             <td className="px-6 py-4 font-bold">{t.symbol}</td>
                             <td className={`px-6 py-4 font-bold ${t.outcome === 'WIN' ? 'text-emerald-500' : 'text-rose-500'}`}>{t.outcome}</td>
                             <td className="px-6 py-4 font-black tabular-nums">{t.pnl.toFixed(2)}%</td>
                          </tr>
                        ))}
                      </tbody>
                   </table>
                </div>
             </div>
           ) : (
             <GlassCard className="h-full flex items-center justify-center border-dashed border-zinc-800">
                <span className="text-zinc-800 text-8xl font-black uppercase tracking-tighter opacity-20 select-none">Idle Engine</span>
             </GlassCard>
           )}
        </div>
      </div>
    </div>
  );
}

export default App;
