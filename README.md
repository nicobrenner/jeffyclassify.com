# jeffyclassify.com

Source for [jeffyclassify.com](https://jeffyclassify.com), the landing page and blog for [Jeffy](https://github.com/nicobrenner/jeffy)

## Deploy

```bash
source ~/.jeffy-ts/cf-env.sh
wrangler pages deploy . --project-name jeffy-landing --branch main --commit-dirty=true
```

## Structure

```
index.html                          # landing page
blog/
  mind-reader/                      # Can AI Read Your Mind?
  pacman/                           # Pac-Man AI tutorial
  when-llms-fail-at-classification/ # LLM vs classifier benchmarks
  n8n-jeffy/                        # n8n community node
benchmark/                          # interactive benchmark explorer
```

## Stack

Static HTML + CSS + vanilla JS, hosted on Cloudflare Pages. No build step. Fonts from Google Fonts, analytics via [Umami](https://umami.is). The playground at `playground.jeffyclassify.com` is a separate service (see the [main repo](https://github.com/nicobrenner/jeffy))
