import os
import json
import datetime
from loguru import logger

class VaultManager:
    def __init__(self, base_vault_path: str = "vault_digital"):
        self.base_path = os.path.join(os.getcwd(), base_vault_path)
        os.makedirs(self.base_path, exist_ok=True)

    def create_radicado_container(self, radicado_id: str, citizen_name: str = "ANONIMO") -> dict:
        """
        VAULT-01: Crea la estructura física del expediente electrónico Orbital Pro.
        [RADICADO_ID] - [NOMBRE_CIUDADANO]
        """
        clean_name = citizen_name.upper().replace(' ', '_')
        folder_name = f"{radicado_id} - {clean_name}"
        radicado_path = os.path.join(self.base_path, folder_name)
        
        # Estándar de carpetas judiciales
        subfolders = {
            "peticion": "01_Peticion_Ciudadana",
            "proyeccion": "02_Proyeccion_Dependencia",
            "logs": "03_Logs_Auditoria"
        }
        
        paths = {"root": radicado_path}
        for key, sub in subfolders.items():
            path = os.path.join(radicado_path, sub)
            os.makedirs(path, exist_ok=True)
            paths[key] = path
            
        logger.success(f"🏛️ Expediente Electrónico Creado: {folder_name}")
        return paths

    def save_bitacora(self, container_paths: dict, chat_history: list):
        """
        VAULT-02: Registro inmutable de la conversación inicial.
        """
        log_path = os.path.join(container_paths["logs"], "bitacora_chat.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "history": chat_history
            }, f, indent=2)
        logger.info("📝 Bitácora de conversación sellada en el expediente.")
        return log_path

    def save_judicial_log(self, container_paths: dict, process_nodes: list):
        """
        VAULT-03: Genera el Log de Proceso Judicial detallado (Nodos de Pensamiento).
        """
        log_path = os.path.join(container_paths["logs"], "LOG_PROCESO.json")
        radicado_id = os.path.basename(container_paths["root"]).split(" - ")[0]
        
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "radicado_id": radicado_id,
                "process_start": datetime.datetime.utcnow().isoformat(),
                "nodes": process_nodes,
                "audit_version": "3.0_JUDICIAL_ENGINE"
            }, f, indent=2)
        logger.info("⚖️ Log de Proceso Judicial (Thought Nodes) sellado.")
        return log_path

vault_manager = VaultManager()
