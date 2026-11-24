#!/bin/bash
# Laboratorio SSH de Nortia Distribuciones S.A.S. - cuentas de empleados.
# Entorno deliberadamente vulnerable (claves debiles, cuenta compartida,
# cuentas de ex-empleados sin dar de baja). Solo expuesto a 127.0.0.1.
set -e

mkdir -p /opt/dumps

while IFS=: read -r username password; do
    [ -z "$username" ] && continue
    if ! id "$username" &>/dev/null; then
        useradd -m -s /bin/bash "$username"
    fi
    echo "${username}:${password}" | chpasswd
done < /opt/users.csv

# Simula un volcado de /etc/shadow ya obtenido en una fase previa del
# pentest (p. ej. mediante una escalada de privilegios fuera de alcance de
# este laboratorio), para que el grupo pueda practicar John the Ripper sin
# necesidad de root dentro del contenedor.
grep -Ff <(cut -d: -f1 /opt/users.csv) /etc/shadow > /opt/dumps/shadow_dump.txt
chmod 644 /opt/dumps/shadow_dump.txt

ssh-keygen -A

echo "PermitRootLogin no" >> /etc/ssh/sshd_config
echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

exec /usr/sbin/sshd -D
