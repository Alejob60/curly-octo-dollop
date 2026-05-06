import { useEffect, useMemo, useState } from "react";
import { useI18n } from "./i18n";
import { CaliLexPrime } from "./components/CaliLexPrime";
import { FormalCitizenPortal } from "./components/FormalCitizenPortal";
import { GovernanceDashboard } from "./components/GovernanceDashboard";
import { Layout, MessageSquare, Bot, Database, Shield, Gavel, BarChart3, Settings, LogOut, User } from "lucide-react";

function App() {
  const { t } = useI18n();
  const [role, setRole] = useState("citizen");
  const [activeModule, setActiveModule] = useState("calilex_prime");

  const renderContent = () => {
    switch (activeModule) {
      case "calilex_prime":
        return <CaliLexPrime />;
      case "formal_portal":
        return <FormalCitizenPortal />;
      case "dashboard":
        return <GovernanceDashboard />;
      default:
        return <CaliLexPrime />;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden font-sans">
      {/* NAVBAR SUPERIOR */}
      <nav className="bg-[#0A2540] text-white px-6 py-3 flex items-center justify-between shadow-2xl z-20 border-b border-white/10">
        <div className="flex items-center gap-4">
          <div className="bg-indigo-500/20 p-2 rounded-xl border border-indigo-400/30">
            <Shield className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <h1 className="text-sm font-black uppercase tracking-[0.3em] text-white leading-none">Orbital Prime</h1>
            <p className="text-[7px] font-bold text-indigo-300 uppercase tracking-widest mt-1 opacity-80 italic">GovDocs Forensic Engine</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex bg-white/5 rounded-2xl p-1 border border-white/10">
            <button 
              onClick={() => { setRole("citizen"); setActiveModule("calilex_prime"); }}
              className={`px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all ${activeModule === 'calilex_prime' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              CaliLex Chat
            </button>
            <button 
              onClick={() => { setRole("citizen"); setActiveModule("formal_portal"); }}
              className={`px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all ${activeModule === 'formal_portal' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              Formulario Tradicional
            </button>
            <button 
              onClick={() => { setRole("staff"); setActiveModule("dashboard"); }}
              className={`px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all ${activeModule === 'dashboard' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              Funcionario
            </button>
          </div>

          <div className="h-8 w-[1px] bg-white/10 mx-2"></div>
          
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-[9px] font-black uppercase tracking-widest text-indigo-200">Alejandro Benavides</p>
              <p className="text-[7px] font-bold text-slate-400 uppercase tracking-widest leading-none">Super Administrador</p>
            </div>
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center border-2 border-white/20 shadow-lg">
              <User className="w-4 h-4 text-white" />
            </div>
          </div>
        </div>
      </nav>

      {/* ÁREA DE TRABAJO DINÁMICA */}
      <main className="flex-1 flex overflow-hidden">
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
