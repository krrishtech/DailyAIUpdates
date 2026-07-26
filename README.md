# Daily AI Feed — build log

Personal daily AI/agentic-AI learning digest, delivered via Telegram.
Built step by step to learn the agent pipeline, not as a one-shot prompt.

## Architecture (final target)
Trigger (cron) -> Fetch (allowlisted RSS/APIs, no LLM) -> Dedup filter
(embeddings, no LLM) -> Relevance filter (embeddings, no LLM) ->
Curate & verify agent (single LLM call) -> Deliver (Telegram, no LLM) ->
Update memory

Only one step in the whole pipeline calls an LLM for generation. Everything
else is deterministic code — this keeps token usage low and the output
trustworthy (a claim can only reach you if it survived a real check against
its source text).

## Status
- [x] Step 0 — Telegram delivery + daily cron, no AI
- [ ] Step 1 — Fetch from allowlisted sources
- [ ] Step 2 — Dedup filter (embeddings)
- [ ] Step 3 — Relevance filter (embeddings)
- [ ] Step 4 — Curate & verify agent (the one real LLM call)
- [ ] Step 5 — Memory update

## Setup
1. Create a Telegram bot via @BotFather, get the token.
2. Message the bot once, then hit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat id.
3. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as GitHub repo secrets.
4. Push this repo. Run the workflow manually from the Actions tab
   (workflow_dispatch) to test before waiting for the cron.
