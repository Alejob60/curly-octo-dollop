#!/bin/bash
# Configura acceso de VM GCP + sube backup + prepara restauracion.
# Uso:
#   chmod +x configure_and_restore_minecraft_gcp.sh
#   ./configure_and_restore_minecraft_gcp.sh /ruta/a/backup.tar.gz [usuario]

set -euo pipefail

PROJECT_ID="misybot"               # Cambia si aplica
ZONE="us-central1-a"
INSTANCE="minecraft-realculture"
NETWORK_TAG="minecraft-server"
MINECRAFT_PORT="25565"
RCON_PORT="25575"

BACKUP_FILE="${1:-}"
SSH_USER="${2:-enterprise}"

if [[ -z "$BACKUP_FILE" ]]; then
  echo "ERROR: Debes indicar el archivo de backup."
  echo "Ejemplo: ./configure_and_restore_minecraft_gcp.sh ./minecraft-backup.tar.gz enterprise"
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: No existe el backup en: $BACKUP_FILE"
  exit 1
fi

echo "[1/9] Configurando proyecto y zona..."
gcloud config set project "$PROJECT_ID"
gcloud config set compute/zone "$ZONE"

echo "[2/9] Habilitando puerto serie para troubleshooting (opcional pero recomendado)..."
gcloud compute instances add-metadata "$INSTANCE" \
  --zone "$ZONE" \
  --metadata serial-port-enable=TRUE

echo "[3/9] Asegurando tag de red en la VM..."
gcloud compute instances add-tags "$INSTANCE" \
  --zone "$ZONE" \
  --tags "$NETWORK_TAG"

echo "[4/9] Regla firewall SSH (22/tcp)..."
if ! gcloud compute firewall-rules describe allow-${NETWORK_TAG}-ssh >/dev/null 2>&1; then
  gcloud compute firewall-rules create allow-${NETWORK_TAG}-ssh \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=0.0.0.0/0 \
    --target-tags="$NETWORK_TAG"
fi

echo "[5/9] Regla firewall Minecraft (25565 tcp/udp)..."
if ! gcloud compute firewall-rules describe allow-${NETWORK_TAG}-mc >/dev/null 2>&1; then
  gcloud compute firewall-rules create allow-${NETWORK_TAG}-mc \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:${MINECRAFT_PORT},udp:${MINECRAFT_PORT} \
    --source-ranges=0.0.0.0/0 \
    --target-tags="$NETWORK_TAG"
fi

echo "[6/9] Regla firewall RCON (25575/tcp) solo para tu IP publica..."
MY_IP="$(curl -s https://ifconfig.me || true)"
if [[ -n "$MY_IP" ]]; then
  if ! gcloud compute firewall-rules describe allow-${NETWORK_TAG}-rcon >/dev/null 2>&1; then
    gcloud compute firewall-rules create allow-${NETWORK_TAG}-rcon \
      --direction=INGRESS \
      --priority=1000 \
      --network=default \
      --action=ALLOW \
      --rules=tcp:${RCON_PORT} \
      --source-ranges="${MY_IP}/32" \
      --target-tags="$NETWORK_TAG"
  fi
else
  echo "No se pudo detectar IP publica local; omitiendo regla RCON restringida."
fi

echo "[7/9] Verificando acceso SSH..."
gcloud compute ssh "${SSH_USER}@${INSTANCE}" --zone "$ZONE" --command "echo SSH_OK && uname -a"

echo "[8/9] Subiendo backup a /tmp en la VM..."
BASENAME="$(basename "$BACKUP_FILE")"
gcloud compute scp "$BACKUP_FILE" "${SSH_USER}@${INSTANCE}:/tmp/${BASENAME}" --zone "$ZONE"

echo "[9/9] Preparando directorio y comandos de restauracion en la VM..."
gcloud compute ssh "${SSH_USER}@${INSTANCE}" --zone "$ZONE" --command "
set -e
sudo mkdir -p /opt/minecraft
sudo chown -R ${SSH_USER}:${SSH_USER} /opt/minecraft
echo 'Backup recibido en /tmp/${BASENAME}'
file /tmp/${BASENAME} || true
echo 'Si es .tar.gz, restaura con:'
echo '  tar -xzf /tmp/${BASENAME} -C /opt/minecraft'
echo 'Si es .zip, restaura con:'
echo '  unzip /tmp/${BASENAME} -d /opt/minecraft'
"

EXTERNAL_IP="$(gcloud compute instances describe "$INSTANCE" --zone "$ZONE" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"

echo ""
echo "Completado."
echo "IP publica VM: ${EXTERNAL_IP}"
echo "Prueba Minecraft: ${EXTERNAL_IP}:${MINECRAFT_PORT}"
echo "Consola serie (si la necesitas):"
echo "  gcloud compute connect-to-serial-port ${INSTANCE} --zone ${ZONE} --port 1"
echo ""
echo "Siguiente paso sugerido en la VM:"
echo "  tar -xzf /tmp/${BASENAME} -C /opt/minecraft"
echo "  cd /opt/minecraft"
echo "  java -Xms2G -Xmx6G -jar server.jar nogui"
