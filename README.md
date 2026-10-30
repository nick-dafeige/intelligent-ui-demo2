# Intelligent UI Lab

Interactive, side-by-side teaching demo comparing a **prebuilt dashboard with AI-populated fields** and a **UI rendered from a runtime component specification**.

## Run (no installation necessary)

- Open `index.html` directly in Chrome, Safari, or Edge for **scripted mode**.
- Or run `python3 server.py` and visit http://localhost:8765.
- Click any scenario, try the surprise follow-up, and inspect the spec plus event trace.

## Enable a real model

Run the server with a DeepSeek API key (recommended for this variant):

```bash
export DEEPSEEK_API_KEY='YOUR_DEEPSEEK_API_KEY'
python3 server.py
```

Then visit http://localhost:8765 and check **Live AI**. DeepSeek defaults to `deepseek-chat`. To choose another supported model, set `DEEPSEEK_MODEL`. The server uses DeepSeek's Chat Completions API and JSON output, and validates the returned UI specification.

To use OpenAI instead:

```bash
export AI_PROVIDER=openai
export OPENAI_API_KEY='YOUR_OPENAI_API_KEY'
python3 server.py
```

OpenAI defaults to `gpt-4.1-mini` (override with `OPENAI_MODEL`). If you have both keys, set `AI_PROVIDER=deepseek` or `AI_PROVIDER=openai` explicitly.

**Important:** Never put an API key in the HTML, paste one into the browser, or publicly expose this server. The key stays server-side. The local endpoint binds to 127.0.0.1. Live mode makes paid API requests to the configured model.

The DeepSeek live path has been verified end to end against the chat completions endpoint (`deepseek-chat`): responses validate and render. The OpenAI path uses the Responses API with a strict JSON schema and has not been exercised in this environment. Scripted mode needs no key at all — open `index.html` and everything works offline.

## What the demo proves

- Fixed layout: structure remains constant even when its recommendation text changes.
- Composed UI: a validated JSON specification chooses which components to render, their structure, and permitted actions.
- In scripted mode the spec comes from local deterministic rules—**not an LLM**.
- In live mode the spec is returned by a model using structured outputs. Inspect the event trace and JSON.
- State changes from sliders and form controls are deterministic and do not require another model call.
- Data is synthetic, and actions are review-only. Staffing and compliance illustrations are not production models.

## Known limitations

- The spec is a custom teaching format, **not official A2UI syntax** or OpenAI's internal Intelligent UI format.
- It is not a true enterprise integration; metrics and business rules are illustrative.
- A production renderer needs tighter validation, identity/permission checks, API tool contracts, policy enforcement, error boundaries and stronger output sanitization.
- The server uses only Python standard library. Browser-based scripted mode is fully self-contained.
