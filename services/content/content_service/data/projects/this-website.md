---
slug: this-website
title: This Website
blurb: A personal site rebuilt as three FastAPI microservices talking over HTTP+JSON RPC.
year: 2026
featured: true
tech: [Python, FastAPI, HTMX, Alpine.js, httpx, Docker]
role: Designer & sole engineer
highlights:
  - Three independently-runnable services (web / content / ai) with a shared typed RPC layer.
  - Dependency inversion throughout — every cross-service call is injected and fakeable in tests.
  - An AI chat whose tool surface is the same RPC surface the services use.
links:
  source: https://github.com/logeman123/logan-website
---
This site is itself the portfolio piece: a from-scratch exploration of microservices,
dependency inversion, and RPC using Python and HTMX. The write-up below walks through the
architecture and the decisions behind it.

## Why microservices for a personal site
Honestly? To learn them well. Read on for how the pieces fit together.
