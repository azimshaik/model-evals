#!/usr/bin/env bash
# rig-diag.sh — workstation health battery for the 4x RTX 2080 Ti / X99 rig.
#
#   ./rig-diag.sh            # snapshot (no load, no sudo changes)
#   ./rig-diag.sh --load     # + 3x1000-token sustained decode with telemetry
#   ./rig-diag.sh --caps 175 150   # + power-limit sweep (applies -pl, leaves last)
#
# Notes:
#  - sudo works only when invoked from a Hermes terminal call (password is piped
#    by Hermes). Inside a background/nohup process sudo has no askpass -> fails,
#    which silently skips -pl application. Run cap changes from the shell prompt.
set -uo pipefail
# Privileged reads (nvidia-smi -q -d PERFORMANCE, dmesg, lspci -vv, smartctl) need root.
# Run it as:  sudo ~/inference/rig-diag.sh [--load|--caps N ...]
# A sudo *inside* a script does not get Hermes' piped password, so run the whole script with sudo.
if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
INF=$HOME/inference
OUT=/tmp/rig-diag-$(date +%Y%m%d-%H%M); mkdir -p "$OUT"
say() { printf '\n===== %s =====\n' "$1"; }

say "GPU snapshot"
nvidia-smi --query-gpu=index,pci.bus_id,name,driver_version,pstate,temperature.gpu,power.draw,power.limit,enforced.power.limit,clocks.current.sm,utilization.gpu,memory.used,memory.total,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current --format=csv

say "Thermal / power headroom (limits per NVIDIA)"
nvidia-smi -q -d TEMPERATURE 2>/dev/null | grep -E "GPU 0000|Shutdown Temp|Slowdown Temp|Max Operating" | sed 's/^ *//'

say "Throttle counters since driver load (us)"
$SUDO nvidia-smi -q -d PERFORMANCE 2>/dev/null | awk '/GPU 0000/{g=$2} /SW Power Capping|HW Thermal Slowdown|HW Slowdown|SW Thermal Slowdown/{printf "%-14s %s\n", g, $0}' | sed 's/  */ /g'

say "ECC / retired pages (GeForce: N/A as expected)"
nvidia-smi --query-gpu=index,ecc.mode.current,ecc.errors.uncorrected.volatile.total,retired_pages.pending --format=csv

say "Xid / NVRM / AER in kernel log (all boots)"
$SUDO journalctl -k --no-pager 2>/dev/null | grep -icE "Xid" | sed 's/^/Xid count: /'
for f in /sys/bus/pci/devices/*/aer_dev_correctable /sys/bus/pci/devices/*/aer_dev_fatal; do
  v=$(grep -v " 0$" "$f" 2>/dev/null | grep -v TOTAL_ERR | head -2 | tr '\n' ';')
  [ -n "$v" ] && echo "$(basename "$(dirname "$f")"): $v"
done
echo "(no AER lines above = clean)"

say "ECC memory (EDAC)"
for f in /sys/devices/system/edac/mc/mc*/ce_count /sys/devices/system/edac/mc/mc*/ue_count; do
  [ -f "$f" ] && echo "$f: $(cat "$f")"
done

say "CPU / board temps (coretemp)"
sensors 2>/dev/null | grep -E "Package id|^Core" | head -18
echo "(board fans/rails unavailable: nct6775 blocked by ACPI \_GPE.HWM OpRegion conflict)"

say "PCIe link state"
for d in 05:00.0 06:00.0 09:00.0 0a:00.0; do
  printf '%s ' "$d"; $SUDO lspci -vv -s "$d" 2>/dev/null | grep -m1 LnkSta:
done

say "Storage"
$SUDO smartctl -H -A /dev/sda 2>/dev/null | grep -E "overall-health|Reallocated_Sector|Power_On_Hours|Power_Cycle|Temperature_C|Current_Pending|Total_LBAs"
df -h / | tail -1
$SUDO smartctl -l error /dev/sda 2>/dev/null | grep -E "No Errors|Error Count"

say "Services / processes"
systemctl --user is-active vllm27b.service
systemctl --failed --no-pager | tail -3
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader

if [ "${1:-}" = "--load" ] || [ "${1:-}" = "--caps" ]; then
  say "Sustained decode + telemetry"
  if [ "${1:-}" = "--caps" ]; then
    shift
    python3 "$INF/power_cap_sweep3.py" "$@" 2>&1 | grep -vE "persistence mode|Known Issues"
  else
    python3 "$INF/measure_run.py" snapshot 3 1000
  fi
fi

say "Artifacts"
echo "csv/logs in $OUT (copies of /tmp/rigdiag-*.csv)"
cp -f /tmp/rigdiag-*.csv "$OUT"/ 2>/dev/null
ls "$OUT" 2>/dev/null | head
echo "done: $(date)"
