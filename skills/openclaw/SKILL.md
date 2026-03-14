---
name: openclaw
description: Diagnose and fix OpenClaw (personal AI assistant) issues on this Mac. Use this skill whenever the user mentions openclaw being down, broken, not responding, or needs debugging — including problems with the gateway, node service, Telegram bot, or launchd services. Also use when the user asks about openclaw configuration, logs, or status. Even if the user just says "openclaw挂了" or "Link不回消息了", this skill applies.
---

# OpenClaw Troubleshooting Guide

OpenClaw is a personal AI assistant running on this Mac mini. It has two main components managed by launchd, both depending on Node.js from Homebrew. Most failures trace back to one of a few root causes — this guide helps you find it fast.

## Architecture at a Glance

```
OpenClaw.app (menu bar)  ←→  Gateway (ws://127.0.0.1:18789)  ←→  Node Host
                                  ↕                                    ↕
                            Telegram Bot                        Browser Control
                          (@lance778665_bot)                 (http://127.0.0.1:18791)
```

- **Gateway** (`ai.openclaw.gateway`): core process, handles agent logic, Telegram, webchat
- **Node Host** (`ai.openclaw.node`): executes tool calls (browser, shell, etc.)
- **Model**: Primary is configurable in `openclaw.json` → `agents.defaults.model.primary`, currently Sonnet 4.6. Via AWS Bedrock `ap-northeast-1`

## Key Paths

| What | Where |
|------|-------|
| Config | `~/.openclaw/openclaw.json` |
| Gateway plist | `~/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| Node plist | `~/Library/LaunchAgents/ai.openclaw.node.plist` |
| Gateway log | `~/.openclaw/logs/gateway.log` |
| Gateway errors | `~/.openclaw/logs/gateway.err.log` |
| Node log | `~/.openclaw/logs/node.log` |
| Node errors | `~/.openclaw/logs/node.err.log` |
| Runtime log (detailed JSON) | `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |
| Agent workspace | `~/.openclaw/workspace/` (SOUL.md, IDENTITY.md, etc.) |
| Memory DB | `~/.openclaw/memory/main.sqlite` |
| npm package | `/opt/homebrew/lib/node_modules/openclaw/` |
| macOS app | `/Applications/OpenClaw.app` |

## Diagnostic Steps (in order)

### 1. Quick status check

```bash
launchctl list | grep openclaw
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18789/
```

In launchctl output: first column is PID (`-` = not running), second is last exit code.
- Exit code 78 = config/startup error
- Exit code 1 = crash (check err logs)
- Gateway returning HTTP 200 = healthy

### 2. Check Node.js (the #1 failure mode)

```bash
ls -la /opt/homebrew/bin/node          # broken symlink?
node --version                          # actually runs?
grep "node/" ~/Library/LaunchAgents/ai.openclaw.*.plist  # what path do plists use?
```

Both plists hardcode the **full Cellar path** like `/opt/homebrew/Cellar/node/25.7.0/bin/node`. When Homebrew upgrades or cleans node, this path breaks and both services die silently. The node host may keep running (binary already in memory) while the gateway fails to restart — making it look like a config issue when it's really a missing binary.

**Fix**: `brew install node && brew pin node`, then update plist paths to `/opt/homebrew/bin/node` (the symlink that survives upgrades). Note that `openclaw gateway install --force` will regenerate the plist and re-hardcode the Cellar path, so check again after running it.

### 3. Check the logs

Read the **err logs first** — they're much shorter and contain the actual errors.

```bash
tail -20 ~/.openclaw/logs/gateway.err.log
tail -20 ~/.openclaw/logs/node.err.log
```

Common errors:
- `"Gateway start blocked: set gateway.mode=local"` → v2026.3.1+ needs `--allow-unconfigured` in plist ProgramArguments when mode is "remote"
- `"pairing required"` in err.log → device (including OpenClaw.app) needs pairing approval. Check with `openclaw devices list` and approve with `openclaw devices approve <request-id>`. OpenClaw.app needs `node` role to provide screen/camera capabilities.
- `"token_mismatch"` → webchat/control-ui using stale gateway token after restart

Then check the main gateway log for the timeline of events:
```bash
tail -100 ~/.openclaw/logs/gateway.log
```

Look for `[health-monitor]` entries — if Telegram shows repeated "restarting (reason: stuck)" every 30 minutes, that's a symptom of a deeper problem (gateway instability or network issue), not the root cause itself.

### 4. Version mismatch check

The gateway plist and node plist can be on **different OpenClaw versions**. The npm package might be yet another version. This matters because new versions can change startup requirements.

```bash
grep SERVICE_VERSION ~/Library/LaunchAgents/ai.openclaw.gateway.plist
grep SERVICE_VERSION ~/Library/LaunchAgents/ai.openclaw.node.plist
cat /opt/homebrew/lib/node_modules/openclaw/package.json | grep '"version"'
```

If they don't match, run `openclaw gateway install --force` to regenerate the gateway plist, then verify the node path wasn't re-hardcoded.

## Bedrock Credentials ("Could not load credentials from any providers")

Authentication uses `AWS_BEARER_TOKEN_BEDROCK` env var in the gateway plist — same mechanism as Claude Code. Config must use `"auth": "aws-sdk"` (NOT `"api-key"`).

**Required env vars in gateway plist** (`EnvironmentVariables` dict):
- `AWS_BEARER_TOKEN_BEDROCK` — the Bedrock API key (starts with `ABSK...`)
- `AWS_REGION` — e.g. `ap-northeast-1`
- `AWS_DEFAULT_REGION` — same value

**Key gotcha**: The current working API key can be found in `~/.claude/settings.json` under `env.AWS_BEARER_TOKEN_BEDROCK`. If OpenClaw's key stops working, compare it with the one Claude Code is using.

**Critical**: After editing the plist, `launchctl kickstart -k` does NOT reload plist file changes. You must `bootout` then `bootstrap`:
```bash
launchctl bootout gui/$(id -u)/ai.openclaw.gateway 2>/dev/null
sleep 1
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

Verify env vars are loaded: `launchctl print gui/$(id -u)/ai.openclaw.gateway | grep AWS`

## Common Fixes

### Restart services
```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
launchctl kickstart -k gui/$(id -u)/ai.openclaw.node
```

### Full reinstall of services (when plists are broken)
```bash
launchctl bootout gui/$(id -u)/ai.openclaw.gateway 2>/dev/null
launchctl bootout gui/$(id -u)/ai.openclaw.node 2>/dev/null
openclaw gateway install --force
# Then check and fix the node path in the regenerated plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.node.plist
```

### Node.js went missing
```bash
brew install node
brew pin node
# Update plists to use symlink path instead of Cellar path
# Then restart both services
```

## Bedrock Model IDs

Cross-region inference profile IDs (verified 2026-03-14):
- Opus 4.6: `global.anthropic.claude-opus-4-6-v1` (has `-v1` suffix)
- Sonnet 4.6: `global.anthropic.claude-sonnet-4-6` (**NO** `-v1` suffix)

Can test model IDs with:
```bash
AWS_BEARER_TOKEN_BEDROCK=$(plutil -extract EnvironmentVariables.AWS_BEARER_TOKEN_BEDROCK raw ~/Library/LaunchAgents/ai.openclaw.gateway.plist) \
AWS_REGION=ap-northeast-1 AWS_DEFAULT_REGION=ap-northeast-1 \
node -e "const{BedrockRuntimeClient,ConverseCommand}=require('/opt/homebrew/lib/node_modules/openclaw/node_modules/@aws-sdk/client-bedrock-runtime');const c=new BedrockRuntimeClient({region:'ap-northeast-1'});c.send(new ConverseCommand({modelId:'MODEL_ID_HERE',messages:[{role:'user',content:[{text:'hi'}]}],inferenceConfig:{maxTokens:5}})).then(()=>console.log('OK')).catch(e=>console.log('FAIL:',e.name))"
```

## Proxy (ClashX Pro) and Telegram Networking

ClashX Pro runs on `127.0.0.1:7890` with **fake-ip mode** (DNS returns `198.18.x.x`). This affects the gateway's Telegram long-polling:

- Node.js `autoSelectFamily=true` (Happy Eyeballs) tries IPv6 first → fails → falls back to IPv4, causing delays
- Long-poll connections get killed by the proxy every ~30 minutes → health-monitor detects "stuck" and restarts Telegram provider
- **Fix**: Add `NODE_OPTIONS=--dns-result-order=ipv4first` to the gateway plist `EnvironmentVariables`
- After `openclaw gateway install --force`, this env var will be lost — re-add it manually

## Response Latency (Telegram feels slow)

Each Telegram message triggers **two model API calls** (OpenClaw architecture, not configurable). With `thinking=adaptive` (default for Claude 4.6 on Bedrock, hardcoded in `model-selection-DFUO-6cE.js`), each call can take 5-30s depending on context size.

**Root cause of slow responses is usually context bloat:**
- Check compaction config: `agents.defaults.compaction` in `openclaw.json`
- `"safeguard"` mode is conservative — only compacts near contextWindow limit
- `"default"` mode with `maxHistoryShare: 0.5` compacts earlier
- Runtime log shows session context via `lane enqueue` → `embedded run start` → `embedded run done` timestamps
- Trace timing with: `grep -o '"time":"[^"]*"\|"1":"[^"]*"' /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | paste - - | awk -F'"' '{print $4" | "$8}' | tail -30`

**Do NOT** reduce `contextWindow` or disable `thinking=adaptive` to fix latency — user prefers accuracy over speed.

## Things That Waste Time

- The `gateway.err.log` is full of `[config/schema] possibly sensitive key found` messages — these are harmless info logs, scroll past them to find actual errors.
- The `node.log` repeats "Doctor warnings" about Telegram groupPolicy allowlist being empty on every restart — also harmless unless you're debugging group message issues.
- Runtime logs at `/tmp/openclaw/` are JSON format and very verbose. Only dig into them if the regular logs don't show the cause.
