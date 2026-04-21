# Multi-Agent Debate (MAD)

An interactive web app that orchestrates structured debates between multiple AI agents. Set a topic, configure the debaters, and watch them argue — with a judge scoring each round.

## What it does

- **Configure debaters** — add 2–6 agents, each with a custom persona (Socratic, Empiricist, Populist, etc.) or a free-form system prompt
- **Run debates** — step through rounds manually or let it auto-play up to 5 rounds
- **Judge scoring** — a neutral judge agent evaluates each round and tallies a running score
- **MAST analysis** — detects multi-agent failure modes (task disobedience, role confusion, step repetition, history loss) via GPT-4o-mini
- **Human moderation** — flag a bad round, provide feedback, and regenerate it with moderator context
- **Keyword extraction** — per-debater TF-IDF keyword highlights each round
- **Auto-save** — completed debates are saved to `backend/saved_debates/` as JSON

## Stack

| Layer | Tech |
|-------|------|
| Frontend | SvelteKit + TypeScript + Tailwind CSS |
| Visualization | D3.js |
| Backend | FastAPI (Python) |
| Agent orchestration | PyAutoGen |
| LLM | OpenAI GPT-4o-mini |
| NLP | TF-IDF, BERTopic, sentence-transformers |

## Getting started

**Backend**
```bash
cd backend
pip install -r requirements.txt
# Add your OpenAI API key to backend/.env:  OPENAI_API_KEY=sk-...
uvicorn main:app --reload   # http://localhost:8000
```

**Frontend**
```bash
npm install
npm run dev                 # http://localhost:5173
```

## Project structure

```
mad-app/
├── src/
│   ├── routes/+page.svelte          # Main UI and app state
│   └── lib/
│       ├── components/              # Svelte UI components
│       ├── services/                # API client, NLP, Gemini
│       ├── personas.ts              # Preset debater personalities
│       └── types.ts                 # Shared TypeScript types
└── backend/
    ├── main.py                      # FastAPI server + endpoints
    ├── debate_logic.py              # PyAutoGen debate orchestration
    ├── nlp_logic.py                 # Keyword & topic analysis
    ├── mast_logic.py                # MAST failure mode detection
    └── saved_debates/               # Auto-saved debate JSON files
```
