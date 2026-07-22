---
name: Always confirm before deploying to VPS
description: User was surprised when Claude ran deploy.sh without asking — always confirm before deploying
type: feedback
---

Always ask for explicit confirmation before running `bash deploy/deploy.sh` or any command that deploys to the production VPS.

**Why:** User did not expect Claude to automatically deploy after committing/pushing. Deploying to production is a separate, irreversible action that affects the live site.

**How to apply:** After pushing to git, stop and ask "Ready to deploy to the VPS?" before running the deploy script. Do not treat commit+push+deploy as a single automatic flow.
