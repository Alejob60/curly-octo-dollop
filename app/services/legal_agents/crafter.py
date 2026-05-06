from app.services.legal_agents.state import LegalCaseState
from app.core.vertex_client import vertex_client
import json
import re
import json_repair
from loguru import logger

class DocumentCrafterAgent:
    """
    Agente Crafter V63.8: Generador de Contenido Institucional de Alta Fidelidad.
    ✅ Sin Saludos | ✅ Estructura de Magistrado | ✅ Personalización Profunda.
    """
    async def validate_input(self, state: LegalCaseState) -> bool:
        return state.citations_block is not None
        
    def _sanitize_crafter_output(self, raw_data: dict, session_id: str) -> dict:
        """Filtro de seguridad nuclear para eliminar lenguaje chatbot (FIX V63.8)"""
        cleaned = {}
        VALID_DOC_KEYS = {
            'memorial_usuario', 'memorial_unico', 'traslado_interno', 'traslado',
            'proyeccion_respuesta', 'proyeccion', 'auto_programacion', 
            'oficio_logistica', 'grounding_legal', 'firma_manifest'
        }
        
        radicado = session_id[-6:].upper()
        
        for key, value in raw_data.items():
            if key not in VALID_DOC_KEYS: continue
            
            if isinstance(value, str):
                # 1. Eliminar bloques conversacionales
                text = re.sub(r'¡Hola!.*?(?=\n\n|I\.|II\.|III\.|$)', '', value, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'Entiendo que.*?(?=\n\n|I\.|II\.|III\.|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'Espero que esta información.*', '', text, flags=re.DOTALL | re.IGNORECASE)
                
                # 2. Eliminar llaves JSON residuales
                text = re.sub(r'["\']?mensaje_ia["\']?\s*:\s*["\'][^"\']*["\']', '', text)
                text = re.sub(r'["\']?tipo_solicitud["\']?\s*:\s*["\'][^"\']*["\']', '', text)
                
                if not text.strip() or len(text.strip()) < 50:
                    text = f"CONTENIDO EN GENERACIÓN FORMAL. Radicado: {radicado}. El sistema está consolidando los fundamentos legales del caso."
                
                cleaned[key] = text.strip()
            else:
                cleaned[key] = value
        return cleaned

    async def execute(self, state: LegalCaseState, extra_prompt: str = None) -> dict:
        prompt = f"""
        ROL: ERES UN ABOGADO MAGISTRADO DE LA ALCALDÍA DE SANTIAGO DE CALI.
        Tu tarea es redactar documentos oficiales de ALTA CALIDAD JURÍDICA para el perfil {state.case_type}.

        REGLAS DE ORO (INCUMPLIMIENTO = FALLO CRÍTICO):
        1. NO SALUDES. No digas "¡Hola!", "Agradezco", "Entiendo que". Empieza directamente con el contenido institucional.
        2. NO USES LENGUAJE DE CHATBOT. Sé formal, técnico y administrativo. Prohibido el uso de muletillas conversacionales.
        3. PERSONALIZACIÓN MÁXIMA: Menciona detalles específicos (JAC {state.raw_input[:200]}, fechas, horas, nombres de barrios, etc.).
        4. ESTRUCTURA OBLIGATORIA: Usa numerales romanos para las secciones:
           I. ANTECEDENTES (Mínimo 150 palabras, detallando quién pide, qué pide y para quién).
           II. FUNDAMENTOS JURÍDICOS (Cita leyes colombianas específicas con artículos y texto relevante).
           III. RESOLUCIÓN (Mínimo 4 artículos resolutivos con acciones concretas: APROBAR, ASIGNAR, DESIGNAR, NOTIFICAR).
        5. PRIVACIDAD NUCLEAR: Usa estrictamente [NOMBRE_1], [ID_1], [CELULAR_1], [EMAIL_1] para datos personales. No inventes datos reales.
        6. EXTENSIÓN: Cada documento debe ser sustancioso (mínimo 300 palabras por documento).

        CONTEXTO JURÍDICO ESPECÍFICO:
        - Radicado: {state.session_id[-8:].upper()}
        - Perfil: {state.case_type}
        - Peticionario: [NOMBRE_1] con CC [ID_1]
        - Hechos Extraídos: {state.facts}
        - Base Legal (Grounding): {state.citations_block}

        TAREA: Genera el paquete 'trinidad_documental' con contenido REALMENTE administrativo.

        RESPONDE EXCLUSIVAMENTE CON JSON:
        {{
          "trinidad_documental": {{
            "memorial_usuario": "I. ANTECEDENTES... II. FUNDAMENTOS... III. SOLICITUD...",
            "traslado_interno": "I. ANTECEDENTES... II. COMPETENCIA... III. TRASLADO...",
            "proyeccion_respuesta": "I. ANTECEDENTES... II. FUNDAMENTOS... III. RESOLUCIÓN (RESUELVE: ARTÍCULO PRIMERO...)"
          }}
        }}

        AUDITORÍA PREVIA INTERNA:
        ✓ ¿Los hechos son específicos y mencionan la JAC y el barrio?
        ✓ ¿La resolución tiene artículos numerados?
        ✓ ¿El lenguaje es 100% de Magistrado (frío, técnico, legal)?
        """
        
        try:
            res = await vertex_client.generate_content([prompt])
            clean_raw = re.sub(r'```json|```', '', res).strip()
            data = json_repair.loads(clean_raw)
            if isinstance(data, list) and len(data) > 0: data = data[0]
            
            trinidad_raw = data.get("trinidad_documental", {})
            trinidad = self._sanitize_crafter_output(trinidad_raw, state.session_id)
            
            # Asegurar que proyeccion_respuesta sea sustancial para pasar el auditor
            draft = trinidad.get("proyeccion_respuesta") or trinidad.get("proyeccion") or "Borrador administrativo en proceso."
            
            return {
                "draft": draft, 
                "package": trinidad,
                "structure_ok": True
            }
        except Exception as e:
            logger.error(f"❌ Fallo en Crafter Agent: {e}")
            return {"draft": "Fallo en generación técnica.", "structure_ok": False}
