import React, { useState } from 'react';
import { MapPinned, ChevronRight } from 'lucide-react';

export const ContactCard = ({ data, onConfirm }) => {
  const [formData, setFormData] = useState({
    departamento: data.departamento || 'Valle del Cauca',
    municipio: data.municipio || 'Cali',
    direccion: data.direccion || data.direccion_residencia || '',
    celular: data.celular || data.telefono_celular || '',
    email: data.email || data.notificacion_email || '',
    confirmar_email: data.email || data.notificacion_email || ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.email !== formData.confirmar_email) {
      alert("Los correos electrónicos no coinciden.");
      return;
    }
    // Sincronizamos con los campos esperados por el backend
    const finalData = {
      ...formData,
      direccion_residencia: formData.direccion,
      telefono_celular: formData.celular,
      notificacion_email: formData.email
    };
    onConfirm(finalData);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-lg w-full animate-in slide-in-from-bottom-2 duration-500 text-slate-900">
      <div className="flex items-center gap-2 mb-4 border-b border-slate-50 pb-2">
        <div className="p-1 bg-rose-600 rounded shadow-sm">
          <MapPinned className="w-3 h-3 text-white" />
        </div>
        <p className="text-[8px] font-black uppercase tracking-widest text-slate-400">Paso 2: Ubicación y Notificación</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Departamento</label>
            <input 
              type="text" 
              value={formData.departamento} 
              disabled 
              className="w-full bg-slate-100 border border-slate-200 rounded-lg p-2 text-[10px] font-bold text-slate-500 cursor-not-allowed" 
            />
          </div>
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Municipio</label>
            <input 
              type="text" 
              value={formData.municipio} 
              disabled 
              className="w-full bg-slate-100 border border-slate-200 rounded-lg p-2 text-[10px] font-bold text-slate-500 cursor-not-allowed" 
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Dirección (Barrio, Calle, Número)</label>
          <input 
            type="text" 
            name="street-address"
            autoComplete="street-address"
            value={formData.direccion}
            onChange={(e) => setFormData({...formData, direccion: e.target.value})}
            placeholder="Ej: Calle 47c # 14a-05 Barrio Santa Cecilia"
            className={`w-full bg-slate-50 border ${!formData.direccion ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-rose-500 transition-colors`}
            required
          />
        </div>

        <div className="space-y-1">
          <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Celular (10 dígitos)</label>
          <input 
            type="tel" 
            name="tel"
            autoComplete="tel"
            maxLength="10"
            value={formData.celular}
            onChange={(e) => setFormData({...formData, celular: e.target.value.replace(/\D/g,'')})}
            className={`w-full bg-slate-50 border ${!formData.celular ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-rose-500 transition-colors`}
            required
          />
        </div>

        <div className="grid grid-cols-1 gap-3">
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Correo Electrónico</label>
            <input 
              type="email" 
              name="email"
              autoComplete="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className={`w-full bg-slate-50 border ${!formData.email ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-rose-500 transition-colors`}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Confirmar Correo Electrónico</label>
            <input 
              type="email" 
              name="confirm-email"
              autoComplete="email"
              value={formData.confirmar_email}
              onChange={(e) => setFormData({...formData, confirmar_email: e.target.value})}
              className={`w-full bg-slate-50 border ${!formData.confirmar_email ? 'border-rose-500' : 'border-slate-200'} rounded-lg p-2 text-[10px] font-bold outline-none focus:border-rose-500 transition-colors`}
              required
            />
          </div>
        </div>

        <button 
          type="submit"
          className="w-full bg-rose-600 text-white font-black py-3 rounded-lg text-[9px] uppercase tracking-[0.2em] hover:bg-rose-700 transition-all shadow-md flex items-center justify-center gap-2 group"
        >
          Confirmar Datos de Contacto
          <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
        </button>
      </form>
    </div>
  );
};
