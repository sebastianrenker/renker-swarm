"""Run exactly one cycle, then exit. This is what GitHub Actions calls on its
cron schedule. Exits 0 even when idle so the Actions run never shows red just
because no keys are wired up yet.
"""
from swarm.env import load_env
from swarm.runner import run_cycle

if __name__ == "__main__":
    load_env()  # picks up a local .env if present (no-op on GitHub Actions)
    ran = run_cycle()
    print(f"done — {ran} agent(s) ran this cycle")
