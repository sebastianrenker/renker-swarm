# Oracle Cloud Always-Free VM — 24/7 setup

This runs the swarm as a real always-on daemon (true 24/7), for free, off your PC.
Oracle's **Always Free** tier includes an Ampere ARM VM that never expires.

> Honest notes: the signup needs a credit card for identity verification (you are
> **not** charged for Always-Free resources). Oracle can reclaim idle Always-Free
> VMs — keeping the daemon busy helps. CPU-only, so the local `ollama` fallback is
> for small models; the real intelligence comes from the free cloud APIs.

## 1. Create the VM
1. Sign up: https://www.oracle.com/cloud/free/ → pick your home region.
2. Compute → Instances → Create.
3. Image **Canonical Ubuntu 22.04**, Shape **VM.Standard.A1.Flex** (Always Free
   eligible; 1–4 OCPU / up to 24 GB — 1 OCPU/6 GB is plenty here).
4. Add your SSH public key, create, note the public IP.

## 2. Install
```bash
ssh ubuntu@YOUR_VM_IP
sudo apt update && sudo apt install -y python3-pip git
git clone YOUR_REPO_URL renker-swarm      # or scp the folder up
cd renker-swarm
pip3 install -r requirements.txt
cp .env.example .env && nano .env          # paste your free API keys
python3 run_once.py                        # smoke test (should print a cycle line)
```

## 3. (Optional) local small-model fallback
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
# then in .env: OLLAMA_HOST=http://127.0.0.1:11434
```

## 4. Run 24/7 as a service
```bash
sudo cp deploy/renker-swarm.service /etc/systemd/system/
# edit paths/user in the file if you didn't clone to /home/ubuntu/renker-swarm
sudo systemctl daemon-reload
sudo systemctl enable --now renker-swarm
systemctl status renker-swarm            # should be "active (running)"
journalctl -u renker-swarm -f            # live logs
```

That's it — the swarm now runs cycles forever, self-throttled by `config.yaml`.
