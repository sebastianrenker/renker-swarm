"""Continuous loop for an always-on box (e.g. an Oracle Cloud Always-Free VM).
Runs a cycle, sleeps, repeats — forever, restarting on errors. Use the systemd
unit in deploy/ so it also survives reboots.
"""
import time

import yaml

from swarm.env import load_env
from swarm.runner import ROOT, run_cycle


def main():
    load_env()  # picks up a local .env if present
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    sleep = cfg.get("cycle_sleep_seconds", 300)
    print(f"[daemon] renker-swarm up — one cycle every {sleep}s. Ctrl+C to stop.")
    while True:
        try:
            run_cycle()
        except Exception as e:  # noqa: BLE001 — keep the daemon alive
            print(f"[daemon] cycle error: {e}")
        time.sleep(sleep)


if __name__ == "__main__":
    main()
