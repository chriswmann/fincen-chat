# FinCEN Chat

A small demo app that allows a user to interrogate the [FinCEN](https://github.com/jexp/fincen) data in Neo4j via natural language.

# Usage

Provide a Google Gemini API key (or change the `MODEL` variable in `.env` to another provider).

```bash
mise run setup     # Boot Docker services and load FinCEN data
mise run run       # Start the FastAPI dev server
mise run teardown  # Stop services and delete local data
```
# Security
`.env` doesn't contain any real secrets and I wanted to keep manual configuration to a minimum, hence why it isn't in `.gitignore` (or, even better, a secrets manager isn't used).

The guardrails are very limited and basic at the moment but the model will decline to answer many messages that aren't related to the FinCEN data.