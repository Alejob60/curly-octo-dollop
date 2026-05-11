#!/bin/bash
# ============================================================================
# VALIDACIÓN DE VM MIGRADA EN GCP
# ============================================================================
# Ejecutar en Google Cloud Shell después de crear la VM
# ============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok() { echo -e "${GREEN}✓${NC} $1"; }
log_fail() { echo -e "${RED}✗${NC} $1"; }
log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

PROJECT="tu-proyecto-gcp"      # REEMPLAZAR
ZONE="us-central1-a"           # REEMPLAZAR
VM="minecraft-gcp"             # REEMPLAZAR
SSH_USER="ubuntu"              # Para Ubuntu

log_info "=== VALIDACIÓN DE VM EN GCP ==="

gcloud config set project $PROJECT
gcloud config set compute/zone $ZONE

# 1. Verificar que la VM existe y está running
log_info "1. Verificando estado de la VM..."
STATE=$(gcloud compute instances describe $VM --format='get(status)')
if [ "$STATE" = "RUNNING" ]; then
    log_ok "VM está corriendo"
else
    log_fail "VM no está en RUNNING (Estado: $STATE)"
    exit 1
fi

# 2. Obtener IP pública
log_info "2. Obteniendo IP pública..."
IP=$(gcloud compute instances describe $VM --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
if [ -z "$IP" ]; then
    IP=$(gcloud compute instances describe $VM --format='get(networkInterfaces[0].networkIP)')
    log_fail "No hay IP pública, usando IP privada: $IP"
else
    log_ok "IP pública: $IP"
fi

# 3. Permitir SSH desde esta máquina
log_info "3. Configurando firewall para SSH..."
gcloud compute firewall-rules create allow-ssh-minecraft \
    --allow=tcp:22 \
    --source-ranges=0.0.0.0/0 \
    --description="Permitir SSH a minecraft" \
    --quiet \
    2>/dev/null || log_info "Regla SSH ya existe"

# 4. Crear clave SSH si no existe
log_info "4. Preparando clave SSH..."
SSH_KEY="$HOME/.ssh/minecraft-gcp"
if [ ! -f "$SSH_KEY" ]; then
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "minecraft@gcp"
    chmod 400 "$SSH_KEY"
    log_ok "Clave SSH creada"
else
    log_ok "Clave SSH ya existe"
fi

# 5. Agregar clave SSH a la VM
log_info "5. Agregando clave SSH a la VM..."
gcloud compute instances add-metadata $VM \
    --metadata-from-file=ssh-keys=<(cat << EOF
${SSH_USER}:$(cat "${SSH_KEY}.pub")
EOF
) || log_info "SSH ya configurado"

# 6. Intentar conexión SSH
log_info "6. Intentando conexión SSH..."
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${SSH_USER}@${IP}" "echo 'SSH OK'" 2>/dev/null; then
    log_ok "Conexión SSH exitosa"
else
    log_fail "No se puede conectar por SSH"
    log_info "Espera 30 segundos e intenta de nuevo"
fi

# 7. Verificar disco y sistema de archivos
log_info "7. Verificando discos..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${IP}" "df -h /" 2>/dev/null || log_fail "No se pudo ejecutar df"

# 8. Verificar servicios relevantes
log_info "8. Verificando servicios..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${SSH_USER}@${IP}" "systemctl status --no-pager" 2>/dev/null || log_info "No se pudo verificar systemctl"

# 9. Resumen
cat << SUMMARY

${GREEN}════════════════════════════════════════════════════════════════${NC}
${GREEN}VALIDACIÓN COMPLETADA${NC}
${GREEN}════════════════════════════════════════════════════════════════${NC}

Información de la VM:
  Proyecto: $PROJECT
  Zona: $ZONE
  Nombre: $VM
  IP: $IP
  Usuario SSH: $SSH_USER
  Clave SSH: $SSH_KEY

Para acceder:
  ${YELLOW}ssh -i $SSH_KEY ${SSH_USER}@${IP}${NC}

O usar gcloud:
  ${YELLOW}gcloud compute ssh $VM${NC}

Próximos pasos:
1. Conecta por SSH y verifica que los servicios funcionan
2. Si es Minecraft, inicia el servidor: ${YELLOW}python3 ~/start_minecraft.py${NC} (o lo que uses)
3. Verifica conectividad: ${YELLOW}curl http://${IP}:8080${NC} (o puerto correspondiente)
4. Cuando confirmes que funciona, elimina recursos de Azure

IMPORTANTE:
⚠️  Mantén esta clave SSH segura: $SSH_KEY
⚠️  El servidor está expuesto públicamente (0.0.0.0/0)
⚠️  Considera restringir a tus IPs específicas en firewall

Restringir acceso a tu IP:
${YELLOW}gcloud compute firewall-rules update allow-ssh-minecraft --source-ranges=TU_IP/32${NC}

════════════════════════════════════════════════════════════════
SUMMARY
