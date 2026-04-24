# embr-foundry-chat-sample

A tiny chat app that demonstrates **Scenario 1** of the [Embr × Foundry POC](https://github.com/coreai-microsoft/embr/issues/300):

> An agent is orchestrated *inside* an Embr-hosted Python app using **Microsoft Agent Framework**. The Foundry project only provides the underlying LLM (the model deployment) — the agent loop, system prompt, tool-calling, and memory all live in this repo's own code.

```
┌───────────────────────────────────────────────┐
│              Embr-hosted container            │
│                                               │
│   ┌─────────────┐     ┌──────────────────┐   │
│   │   FastAPI   │────▶│  Microsoft       │   │
│   │   + HTML UI │     │  Agent Framework │   │
│   └─────────────┘     │  (agent loop +   │   │
│                       │   local tools)   │   │
│                       └────────┬─────────┘   │
└────────────────────────────────┼──────────────┘
                                 │ inference only
                                 ▼
                      ┌──────────────────────┐
                      │  Foundry project     │
                      │  → model deployment  │
                      │  (gpt-4o / ...)      │
                      └──────────────────────┘
```

Two toy tools are wired in (`get_weather`, `roll_dice`) so you can actually see tool-calling happen. Replace them with whatever your demo needs.

---

## Part 1 — Create the Foundry resources

You do this **once**, in the Azure AI Foundry portal. The app just needs a model endpoint + key.

### 1. Create a Foundry project

1. Go to [ai.azure.com](https://ai.azure.com) and sign in.
2. Click **+ New project**.
3. Pick an existing hub or let the portal create one. Region: anywhere that has the model you want (e.g., East US 2).
4. After the project is provisioned, open it.

### 2. Deploy a model

1. In the left nav choose **Models + endpoints**.
2. Click **+ Deploy model → Deploy base model**.
3. Pick `gpt-4o-mini` (cheap + fast for this demo) or `gpt-4o`.
4. Accept the default deployment name or give it one you'll remember (e.g., `gpt-4o-mini`).
5. Click **Deploy**.

### 3. Grab the three values you need

On the deployment's detail page, click **View code** (or the endpoint tile on the project home). You need:

| Env var | Where to find it | Example |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | The **Target URI** *base* — just the `https://<resource>.openai.azure.com/` portion, not the full completions URL | `https://my-foundry.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | **Key 1** on the deployment page | `abc123…` |
| `AZURE_OPENAI_MODEL` | The **Deployment name** you chose above (this is the deployment name, NOT the underlying model name) | `gpt-4o-mini` |

Optional: `AZURE_OPENAI_API_VERSION` (defaults to `2024-10-21`).

---

## Part 2 — Run locally

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in the three values from Part 1

uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000). Try:

- *"What's the weather in Seattle and Tokyo?"* → should call `get_weather` twice and summarize.
- *"Roll 3d20 and tell me the highest."* → should call `roll_dice` three times.

---

## Part 3 — Deploy to Embr

### Prerequisite

The [Embr GitHub App](https://github.com/apps/embr-platform) must be installed on this repo.

### Deploy

```bash
# Push this repo to GitHub first (under your account)
gh repo create embr-foundry-chat-sample --source=. --public --push

# One-command deploy
embr quickstart deploy <your-user>/embr-foundry-chat-sample -i <installation-id>
```

`embr installations config` returns the installation ID if you don't know it.

### Configure the Foundry values

```bash
embr variables set AZURE_OPENAI_ENDPOINT https://<your-foundry>.openai.azure.com/
embr variables set AZURE_OPENAI_API_KEY <your-key> --secret
embr variables set AZURE_OPENAI_MODEL <your-deployment-name>
```

Trigger a redeploy so the new env vars take effect:

```bash
embr deployments create --restart
```

---

## Project layout

```
.
├── app/
│   ├── __init__.py
│   ├── agent.py          # Agent definition + local tools (get_weather, roll_dice)
│   ├── main.py           # FastAPI: /, /health, /api/chat, /api/config
│   └── static/index.html # Minimal chat UI
├── embr.yaml             # platform: python 3.12, port 8000
├── requirements.txt
├── .env.example
└── README.md
```

## Known limitations / gaps (feeding into the POC findings doc)

- **No auth on `/api/chat`.** V1 intentionally skipped auth so we could focus on the Embr ↔ Foundry wiring. Before shipping anything like this for real, put Entra in front of it.
- **Conversation history is in-memory.** Pod restart = lost context. Would want Redis / Cosmos in a real app.
- **API-key auth to Foundry.** Managed identity would be the secure story; not attempted in this POC.
- **No streaming.** `agent.run()` waits for the full response. Streaming via `agent.run_stream()` + SSE would be a small follow-up.
