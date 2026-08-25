# Free and Local Runtime Notes

Research checked 2026-08-25. These notes are design inputs, not guarantees; the agent should re-check provider terms and model availability before recommending a provider.

## OpenRouter

OpenRouter's official pricing page lists a free tier with free models only and a platform limit of 50 requests per day. The official limits documentation says free model variants use rate limits, that account balance and per-key credit limits can still affect requests, and that a negative account balance may produce a 402 even for free models. Free variants may be subject to daily and per-minute limits and can be unavailable or provider-rate-limited. Upstack must never tell a learner that OpenRouter requires no account balance in every circumstance or that a named free model will remain available.

Useful official pages:

- https://openrouter.ai/pricing
- https://openrouter.ai/docs/api_reference/limits

## Hugging Face Inference Providers

Hugging Face documents a free tier for Inference Providers and requires a Hugging Face token with inference permission. The service routes through providers and exposes model/provider availability and pricing; the free tier is not the same as unlimited free inference. Upstack should present it as a current option to verify, not as a guaranteed no-cost quota.

Useful official page:

- https://huggingface.co/docs/inference-providers/en/index

## Local models with Ollama

Ollama's official Windows documentation describes a local HTTP API at `http://localhost:11434`, specifies supported Windows versions and hardware drivers, and notes that model storage can consume tens to hundreds of gigabytes. Local inference avoids per-token provider charges but requires compatible hardware, disk, memory, and time. Upstack should check whether Ollama is installed and reachable rather than assuming local capacity.

Useful official page:

- https://docs.ollama.com/windows

## Product policy

For a learner with no budget, the default project must still be teachable without a paid model:

1. Begin with a provider-neutral adapter interface.
2. Implement deterministic mock/stub responses for orchestration lessons.
3. Offer local Ollama only when the host reports it as available.
4. Offer OpenRouter or Hugging Face only after the learner explicitly chooses a provider and confirms current terms, limits, and credential handling.
5. Keep model calls optional for the lesson curriculum; never make a paid API prerequisite for learning the architecture.
6. Never request or write credentials without explicit user action and never store secrets in `.upstack/` artifacts.

A model provider is an implementation option inside the project, not the definition of the learning outcome. The learner should first understand interfaces, planning, tool contracts, state, memory, evaluation, and observability using mocks or deterministic fixtures, then add a real provider when available.

## Evidence labels

Provider availability and quotas are time-sensitive. Label them `current_provider_signal` with a retrieval date; label exact quotas as `provider_documented_limit`; label any model recommendation as `availability_to_verify`.
