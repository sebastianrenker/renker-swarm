# Renker Swarm

A free, self-throttling agent orchestrator. A roster of agent roles (scales to
200+) takes turns running on **free cloud LLM tiers**, on a schedule, **off your
PC**. It rotates providers and enforces a hard daily budget, so it keeps running
24/7 without anyone watching a rate limit.

The same code runs two ways:
- **GitHub Actions** — a cron workflow runs cycles on GitHub's servers. Fastest to start.
- **Oracle Always-Free VM** — a real always-on daemon. True 24/7.

## Honest limits

AI inference costs compute, so **free + unlimited + frontier-quality + 24/7 all at
once does not exist.** This project gets as close as honestly possible:
- **Throughput is capped** by the free tiers and by `daily_call_budget`. 200 agents
  don't run at once — they rotate. Most idle; a few run each cycle.
- **Quality = free models** (Gemini Flash, Llama-70B via Groq/OpenRouter). Good for
  research, drafts, and ideas — not frontier-model quality.
- **Free tiers can change.** That is why it rotates across several.
- Agents **prepare** work; real money, contract, and authority actions stay with you.

## How it works

```
roster.yaml  ──►  scheduler picks the agents that are "due"
                    │   (throttled: max_agents_per_cycle)
                    ▼
             provider rotation  ──►  gemini → groq → openrouter → cloudflare → ollama
                    │   (429? cool it down, try the next; stop at daily_call_budget)
                    ▼
             outputs/<department>/<agent>/<timestamp>.md   +   <agent>-latest.md
```

- `config.yaml` — budget, throttle, provider order/models.
- `roster.yaml` — the agents (hand-written core, mirrors the RenkerNet departments).
- `state/state.json` — last-run times + today's call count (auto-managed).
- `outputs/` — what the agents produce. Generated at runtime and gitignored, so
  the repository stays clean; inspect them locally or in the CI run logs.

## Get the free keys (all free tiers)

Create whichever you want — the swarm uses whatever is present and rotates them:
- **Gemini** (most generous): https://aistudio.google.com/apikey
- **Groq** (fast): https://console.groq.com/keys
- **OpenRouter** (`:free` models): https://openrouter.ai/keys
- **Cloudflare Workers AI** (optional): dashboard → AI → Workers AI

## Deploy A — GitHub Actions

The workflow in `.github/workflows/swarm.yml` runs a cycle every 15 minutes on
GitHub's servers. Add at least one API key as a repository secret:

```bash
gh secret set GEMINI_API_KEY --repo sebastianrenker/renker-swarm
# paste your free key from https://aistudio.google.com/apikey when prompted
```

(or on the web: repo → Settings → Secrets and variables → Actions → New secret,
name `GEMINI_API_KEY`). Add `GROQ_API_KEY` / `OPENROUTER_API_KEY` the same way for
more free throughput.

## Deploy B — Oracle Always-Free VM (true 24/7)

See [`deploy/oracle-vm-setup.md`](deploy/oracle-vm-setup.md). In short: create the
free ARM VM, `pip install -r requirements.txt`, fill `.env`, install the systemd
service.

## Run it locally (test)

```bash
pip install -r requirements.txt
python run_once.py          # one cycle; prints what it would do (idle without keys)
python daemon.py            # continuous loop
```

Without keys it prints a "no providers" line and exits cleanly — the skeleton is
safe to run before you wire anything up.

## Scale toward 200 agents

```bash
python tools/expand_roster.py     # stamps town × role scouts into roster.generated.yaml
```

The runner merges `roster.generated.yaml` with `roster.yaml` automatically. Edit
the `TOWNS`/`ROLES` lists in `tools/expand_roster.py` to grow it. More agents means
a longer rotation, never a bigger bill (the daily budget still caps everything).

## Feeds RenkerNet / Rencora

`outputs/` is plain Markdown per department. Point Rencora's brain scan at it, or
show it in the RenkerNet station, to close the loop: the cloud swarm does the 24/7
work, the local cockpit displays it.
