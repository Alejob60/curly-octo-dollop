import re
from loguru import logger

class IntegrationSecurityService:
    def __init__(self):
        # Patrones para identificar PII (Personally Identifiable Information)
        self.patterns = {
            "cedula": r'\b\d{1,3}(?:\.\d{3}){2}\b|\b\d{7,10}\b',
            "email": r'[\w\.-]+@[\w\.-]+\.\w+',
            "telefono": r'\b(?:\+?57)?\s?(?:[3]\d{2})\s?\d{3}\s?\d{4}\b'
        }

    def anonymize_pii(self, text: str) -> tuple[str, dict]:
        """
        Detecta y enmascara datos sensibles para cumplimiento de Ley 1581 (Habeas Data).
        Retorna el texto anonimizado y el mapa para re-inyección.
        """
        pii_map = {}
        anonymized_text = text
        
        # 1. Anonimizar Cédulas
        found_ids = re.findall(self.patterns["cedula"], anonymized_text)
        for i, val in enumerate(found_ids):
            token = f"[ID_TOKEN_{i}]"
            pii_map[token] = val
            anonymized_text = anonymized_text.replace(val, token)

        # 2. Anonimizar Correos
        found_emails = re.findall(self.patterns["email"], anonymized_text)
        for i, val in enumerate(found_emails):
            token = f"[EMAIL_TOKEN_{i}]"
            pii_map[token] = val
            anonymized_text = anonymized_text.replace(val, token)

        logger.info(f"🛡️ Habeas Data Shield: {len(pii_map)} datos sensibles enmascarados.")
        return anonymized_text, pii_map

    def reinject_pii(self, anonymized_text: str, pii_map: dict) -> str:
        """Restaura los datos reales en el documento final (ejecutado localmente)."""
        final_text = anonymized_text
        for token, val in pii_map.items():
            final_text = final_text.replace(token, val)
        return final_text

integration_security_service = IntegrationSecurityService()
