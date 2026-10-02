# Personal Portfolio & AI Demo Platform

A professional portfolio and technical demonstration platform showcasing capabilities in Data Engineering, BI, and AI/LLM integration.

Built using **Flask** as the web framework and **Plotly Dash** for interactive analytics, served serverless on **Google Cloud Run**.

## Features

*   **AI Agents:** Voice and chat agents (ElevenLabs), including a virtual-interview clone trained on a structured career dataset.
*   **BI Dashboard Demo:** A fully interactive executive dashboard demonstrating advanced filtering, cross-filtering, and dynamic aggregation using Pandas and Plotly.
*   **AI Design Lab:**
    *   **Theme Generator:** Uses Gemini/LLMs to generate color palettes and CSS themes from natural language prompts.
    *   **Asset Generator:** Creates consistent visual assets on the fly.
*   **Sales Enablement Tool:** Plans a 3-5 slide pitch deck from platform data, then renders every slide in parallel so they appear as they finish (about 15 seconds for a whole deck).
*   **Enterprise-Grade Architecture:**
    *   **Hybrid Flask/Dash:** Seamless integration of standard web routes with reactive Dash apps.
    *   **Serverless Hosting:** Runs on Cloud Run with a warm instance for instant first loads, autoscaling under load, and Google-managed TLS on the custom domain.
    *   **Keyless CI/CD:** GitHub Actions deploys via Workload Identity Federation, with no long-lived credentials; all infrastructure is Terraform.
    *   **Abuse Protection:** Per-visitor daily caps on the AI demos, and server-signed slide jobs so the image renderer only renders prompts the app planned.

## Tech Stack

*   **Core:** Python 3.13, Flask, Plotly Dash
*   **Data:** Pandas, Plotly, AG Grid
*   **AI/LLM:** Google Gemini (`gemini-3.8-flash`, `gemini-3.1-flash-image`), ElevenLabs agents
*   **Analytics:** PostHog (cookieless)
*   **Infrastructure:** Docker, Terraform, Google Cloud Run
*   **Package Management:** uv

## Project Structure

```text
personal-portfolio/
├── app/
│   ├── app.py                  # Flask server, Dash app, robots/sitemap routes
│   ├── conf.py                 # Global layout & page definitions (incl. link-preview descriptions)
│   └── dash_app/
│       ├── callbacks.py        # All Dash callbacks
│       ├── rate_limit.py       # Per-visitor caps on the AI demos
│       ├── pages/              # One module per page
│       └── assets/             # CSS, posthog.js, images (share/ holds the 1200x630 link-preview cards)
├── infrastructure/             # Terraform: Cloud Run, secrets, domain, DNS, monitoring, CI identity
└── bootstrap.sh                # terraform init + apply wrapper
```

## ⚡ Local Development

### Prerequisites

*   Python 3.13+
*   uv (for dependency management)

### 1. Clone & Setup

```bash
git clone <repository-url>
cd personal-portfolio
uv sync  # Installs dependencies from uv.lock
```

### 2. Environment Variables

Create a `.env` file in the repository root directory with the following keys:

```ini
FLASK_SECRET_KEY=<your-secret-key>
GEMINI_API_KEY=<gemini-api-key>
SERVER_NAME=personal-portfolio
```

### 3. Running the App

```bash
flask --app ./app/app run -p 1701
```

The app will be available at `http://localhost:1701/`.

## Deployment

Infrastructure is managed by **Terraform** (`infrastructure/`); application code is deployed by **GitHub Actions**.

### 1. Provision Infrastructure

```bash
./bootstrap.sh          # terraform init + apply
./bootstrap.sh plan     # any terraform subcommand works
```

This manages the Cloud Run service, its runtime service account and secrets (the Flask secret key and a dedicated Gemini API key in Secret Manager), Artifact Registry, the custom domain mapping and Cloudflare DNS record, and the Workload Identity Federation pool GitHub Actions uses. It also writes the GitHub Actions secrets and variables the workflow needs. The script reads the Cloudflare token from Secret Manager and authenticates the GitHub provider with `gh auth token`.

### 2. Deploy Application

Push to `main`. The workflow builds the image, pushes it to Artifact Registry, and runs `gcloud run deploy` with the new image. Only the image changes on deploy; every other service setting is owned by Terraform.

### DNS & TLS

`cloudflare_record.app_dns` is a DNS-only (unproxied) CNAME to `ghs.googlehosted.com`. Google issues and renews the certificate for the domain mapping automatically. The record must stay unproxied or certificate issuance fails.

## Analytics, SEO & Link Previews

*   **Analytics:** `app/dash_app/assets/posthog.js` loads PostHog on `portfolio.nickearl.net` only, without cookies. Events go to the PostHog project "Portfolio" (US cloud).
*   **SEO:** `/robots.txt` and `/sitemap.xml` are served by `app.py` from the enabled pages.
*   **Link previews:** each page's `share_description` in `conf.py` and its card in `assets/images/share/` feed the description and `og:image` tags.
