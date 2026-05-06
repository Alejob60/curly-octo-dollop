import React, { useState } from 'react';
import { Scale, ChevronRight } from 'lucide-react';

export const IdentityCard = ({ data, onConfirm }) => {
  const [formData, setFormData] = useState({
    tipo_solicitante: data.peticionario_tipo || data.tipo_solicitante || 'Persona Natural',
    tipo_documento: data.tipo_documento || 'Cedula de Ciudadania',
    documento: data.documento || '',
    nombres: data.nombres || '',
    apellidos: data.apellidos || `${data.primer_apellido || ''} ${data.segundo_apellido || ''}`.trim()
  });

  // Split apellidos for internal logic if needed
  const [primerApellido, setPrimerApellido] = useState(data.primer_apellido || (data.apellidos ? data.apellidos.split(' ')[0] : ''));
  const [segundoApellido, setSegundoApellido] = useState(data.segundo_apellido || (data.apellidos ? data.apellidos.split(' ').slice(1).join(' ') : ''));

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalData = {
      ...formData,
      primer_apellido: primerApellido,
      segundo_apellido: segundoApellido,
      apellidos: `${primerApellido} ${segundoApellido}`.trim()
    };
    onConfirm(finalData);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-lg w-full animate-in slide-in-from-bottom-2 duration-500 text-slate-900">
      <div className="flex items-center gap-2 mb-4 border-b border-slate-50 pb-2">
        <div className="p-1 bg-indigo-600 rounded shadow-sm">
          <Scale className="w-3 h-3 text-white" />
        </div>
        <p className="text-[8px] font-black uppercase tracking-widest text-slate-400">Paso 1: Validación de Identidad</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Tipo Solicitante</label>
            <select 
              name="tipo_solicitante"
              autoComplete="honorific-prefix"
              value={formData.tipo_solicitante}
              onChange={(e) => setFormData({...formData, tipo_solicitante: e.target.value})}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500"
            >
              <option>Persona Natural</option>
              <option>Persona Jurídica</option>
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Tipo Documento</label>
            <select 
              name="tipo_documento"
              value={formData.tipo_documento}
              onChange={(e) => setFormData({...formData, tipo_documento: e.target.value})}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500"
            >
              <option>Cedula de Ciudadania</option>
              <option>NIT</option>
              <option>Cedula de Extranjeria</option>
              <option>Pasaporte</option>
            </select>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Número de Documento (Sin puntos)</label>
          <input 
            type="text" 
            name="documento"
            autoComplete="username"
            value={formData.documento}
            onChange={(e) => setFormData({...formData, documento: e.target.value.replace(/\D/g,'')})}
            className={`w-full bg-slate-50 border ${!formData.documento ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500 transition-colors`}
            required
          />
        </div>

        <div className="space-y-1">
          <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Nombre(s) Completo</label>
          <input 
            type="text" 
            name="given-name"
            autoComplete="given-name"
            value={formData.nombres}
            onChange={(e) => setFormData({...formData, nombres: e.target.value})}
            className={`w-full bg-slate-50 border ${!formData.nombres ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500 transition-colors`}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Primer Apellido</label>
            <input 
              type="text" 
              name="family-name"
              autoComplete="family-name"
              value={primerApellido}
              onChange={(e) => setPrimerApellido(e.target.value)}
              className={`w-full bg-slate-50 border ${!primerApellido ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500 transition-colors`}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Segundo Apellido</label>
            <input 
              type="text" 
              name="additional-name"
              autoComplete="additional-name"
              value={segundoApellido}
              onChange={(e) => setSegundoApellido(e.target.value)}
              className={`w-full bg-slate-50 border ${!segundoApellido ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-indigo-500 transition-colors`}
              required
            />
          </div>
        </div>

        <button 
          type="submit"
          className="w-full bg-slate-900 text-white font-black py-3 rounded-lg text-[9px] uppercase tracking-[0.2em] hover:bg-indigo-600 transition-all shadow-md flex items-center justify-center gap-2 group"
        >
          Continuar a Contacto
          <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
        </button>
      </form>
    </div>
  );
};
