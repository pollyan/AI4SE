# New Agents Provider Recovery Actions Design

## Problem

When the model provider or local model configuration fails, ChatPane currently explains the likely cause and offers stage retry. The user still has to discover where settings and connection checks live. This makes provider failures feel like dead ends, especially after the header actions have been simplified into a compact "more" menu.

## Scope

Add lightweight recovery actions directly to the provider failure card:

- Open model settings from the failure card.
- Run the existing model connection check from the failure card.
- Show a local success or failure result for that connection check.
- Keep retry available after the user fixes configuration.

This slice does not move the observability modal into global state. Runtime statistics deep-linking remains a later model governance improvement.

## UX Contract

Provider failure messages that include `模型配置或供应商异常` should render a recovery card with three clear actions:

- `打开模型设置`
- `检测连接`
- `重试本阶段生成`

Connection check results should be concise and local to the card. The right-side artifact must remain unchanged; this UI only helps users recover.

## Architecture Notes

- Reuse the shared SettingsModal state through `useStore.setSettingsOpen`.
- Reuse the existing `/new-agents/api/config/check` backend endpoint.
- Keep the behavior generic across workflows and agents.
- Do not add Lisa/Alex-specific UI branches.
