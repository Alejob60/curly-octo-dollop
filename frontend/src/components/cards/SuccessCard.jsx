import React from 'react';
import { CheckCircle2, Download, ShieldCheck, FileText, Share2, Sparkles, Files, Folder } from 'lucide-react';

export const SuccessCard = ({ data }) => {
  if (!data) return null;

  // Manejar tanto la nueva estructura 'documents' como la antigua 'artifacts'
  const documents = data.documents || [];
  const artifacts = data.artifacts || {};
  const radicadoId = data.radicado_id || "SIN_RADICADO";

  // Si no hay array de documentos pero hay artifacts, convertimos
  const normalizedDocs = documents.length > 0 ? documents : Object.entries(artifacts).map(([key, url]) => ({
    type: key,
    preview_url: url,
    name: (typeof url === 'string' ? url.split('/').pop() : `${key}.pdf`) || `${key}.pdf`,
    folder: "00_Generales"
  }));

  // Agrupar por folder de forma segura
  const grouped = normalizedDocs.reduce((acc, doc) => {
    if (!doc || !doc.type) return acc;
    const folder = doc.folder || "99_Otros";
    if (!acc[folder]) acc[folder] = [];
    acc[folder].push(doc);
    return acc;
  }, {});

  const formatLabel = (key) => {
    if (typeof key !== 'string') return "DOCUMENTO";
    return key.replace(/_/g, ' ').toUpperCase();
  };

  return (
    <div className="bg-[#F8FAFC] border-2 border-emerald-500/20 rounded-2xl p-5 shadow-xl w-full animate-in zoom-in-95 duration-500 text-slate-900 overflow-hidden relative">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <ShieldCheck className="w-16 h-16 text-emerald-600" />
      </div>

      <div className="flex flex-col items-center text-center gap-4 relative z-10">
        <div className="p-3 bg-emerald-500 rounded-full shadow-lg shadow-emerald-500/20">
          <CheckCircle2 className="w-8 h-8 text-white" />
        </div>
        
        <div className="space-y-1">
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-emerald-900 leading-none">Radicación Exitosa</h3>
          <p className="text-[8px] font-bold text-emerald-700/60 uppercase tracking-widest">Expediente Sellado - Alcaldía de Cali</p>
        </div>

        <div className="bg-white border border-emerald-100 rounded-xl p-3 w-full shadow-sm">
          <p className="text-[7px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Radicado No.</p>
          <p className="text-xl font-black text-slate-800 tracking-tighter">#{radicadoId}</p>
        </div>

        <div className="w-full text-left space-y-4">
            {Object.entries(grouped).sort().map(([folder, docs]) => (
                <div key={folder} className="space-y-1.5">
                    <div className="flex items-center gap-2 ml-1 opacity-60">
                        <Folder className="w-2.5 h-2.5 text-indigo-500" />
                        <span className="text-[7px] font-black uppercase tracking-widest text-slate-500">
                            {typeof folder === 'string' ? folder.replace(/^\d+_/, '').replace(/_/g, ' ') : "OTROS"}
                        </span>
                    </div>
                    
                    <div className="space-y-1">
                        {docs.map((doc, i) => (
                            <a 
                                key={`${doc.type}-${i}`}
                                href={doc.preview_url} 
                                target="_blank" 
                                rel="noreferrer" 
                                className="flex items-center justify-between px-3 py-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all group"
                            >
                                <div className="flex items-center gap-2 overflow-hidden">
                                    <FileText className="w-3 h-3 text-indigo-400 shrink-0" />
                                    <span className="text-[9px] font-bold text-slate-700 truncate">
                                        {formatLabel(doc.type)}
                                    </span>
                                </div>
                                <Download className="w-2.5 h-2.5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
                            </a>
                        ))}
                    </div>
                </div>
            ))}
        </div>

        <div className="pt-3 border-t border-slate-100 w-full">
          <p className="text-[6px] font-bold text-slate-400 leading-relaxed uppercase tracking-widest text-center">
            Sello Digital: <span className="text-emerald-600">GCP-IMMUTABLE-WORM</span> <br/>
            Expediente Inalterable · 20 Años de Retención
          </p>
        </div>
      </div>
    </div>
  );
};
