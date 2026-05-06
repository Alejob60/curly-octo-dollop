from locust import HttpUser, task, between
import uuid
import random

class OrbitalPrimeUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.session_id = f"stress-{uuid.uuid4().hex[:6]}"
        self.official_id = "FUNC-STRESS-01"

    @task(3)
    def simulate_citizen_ingestion(self):
        """Simula la radicación y flujo de IA."""
        # 1. Ingesta
        self.client.post("/api/v1/pqrs/analyze", json={
            "session_id": self.session_id,
            "message": "Reporte de falla en semáforo y bache en la calle 5ta."
        })
        
        # 2. Update Slots
        self.client.post("/api/v1/pqrs/update-slot", json={
            "session_id": self.session_id,
            "slots": {
                "documento": str(random.randint(1000000, 99999999)),
                "nombres": "User",
                "apellidos": "Stress",
                "email": "stress@example.com",
                "autorizacion_datos": True
            }
        })
        
        # 3. Finalize (Generación de PDF e IA Review)
        self.client.post("/api/v1/pqrs/finalize", json={"session_id": self.session_id})

    @task(1)
    def simulate_official_review(self):
        """Simula al funcionario revisando la cola y aprobando."""
        # 1. Ver Cola
        response = self.client.get("/api/v1/copilot-engine/queue")
        if response.status_code == 200:
            queue = response.json().get("queue", [])
            if queue:
                target = queue[0]["radicado"]
                # 2. Aprobar
                self.client.post(f"/api/v1/copilot-engine/master-approve/{target}", json={
                    "official_id": self.official_id,
                    "comments": "Stress test approval"
                })

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/copilot-engine/health")
        self.client.get("/api/v1/public/health") # Asumiendo que existe
