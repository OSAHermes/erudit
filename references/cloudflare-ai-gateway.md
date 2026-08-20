# Cloudflare AI Gateway Guide

## Overview

Cloudflare AI Gateway provides:
- Unified billing (one API key for multiple models)
- Caching to reduce costs
- Rate limiting
- Model failover
- Analytics

## Quick Start

### 1. Create AI Gateway

Access: https://dash.cloudflare.com → AI → AI Gateway

Get:
- Gateway ID (e.g., `abc123`)
- Gateway Domain (e.g., `https://abc123.gateway.ai`)

### 2. API Examples

```bash
# OpenAI GPT-4o
curl https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT_ID/cloudflare-ai/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Claude 3.5 Sonnet
curl https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT_ID/cloudflare-ai/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4-20250514",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Supported Models

| Provider | Model ID |
|----------|----------|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini` |
| Anthropic | `anthropic/claude-sonnet-4-20250514`, `anthropic/claude-haiku-4-20250414` |
| Google | `google/gemini-2.0-flash-001`, `google/gemini-2.5-pro-preview-05-06` |
| Groq | `groq/llama-3.3-70b-versatile` |
| DeepSeek | `deepseek/deepseek-r1`, `deepseek/deepseek-chat` |
| xAI | `xai/grok-2-latest` |

## Advanced Features

### Caching
```bash
curl https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT_ID/cloudflare-ai/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}],
    "custom_cache": {
      "ttl": 3600
    }
  }'
```

### Rate Limiting
Configure in Gateway settings:
```
Rate Limit: 100 requests/minute
```

### Failover
Automatic fallback to backup models when primary fails.

## Hermes Integration

```yaml
# ~/.hermes/config.yaml
custom_providers:
  - name: cloudflare-gateway
    base_url: "https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT_ID/cloudflare-ai"
    api_key: "YOUR_API_KEY"
    model: "openai/gpt-4o"
    api_mode: chat_completions
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401 Unauthorized | Check API key and Account ID |
| 429 Too Many Requests | Check rate limit configuration |
| 503 Service Unavailable | Check model availability |

## References

- Docs: https://developers.cloudflare.com/ai-gateway/
- API: https://developers.cloudflare.com/api/
- GitHub: https://github.com/cloudflare/mcp-server-cloudflare
