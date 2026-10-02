# Gemini Context: Personal Portfolio

This file contains context and architectural notes for the `personal-portfolio` repository to assist AI agents.

## ✅ Deployment Status

*   **Status:** Live & Operational.
*   **Infrastructure:** Google Cloud Run (us-west1), one warm instance, custom domain via Cloud Run domain mapping (Google-managed TLS).
*   **CI/CD:** GitHub Actions (Build -> Push to GAR -> `gcloud run deploy`), authenticated with Workload Identity Federation.

## Project Overview

*   **Name:** `personal-portfolio`
*   **Type:** Flask application embedding a Plotly Dash multipage app.
*   **Goal:** A professional portfolio and technical demonstration platform showcasing capabilities in Data Engineering, BI, and AI/LLM integration.
*   **Stack:** Python 3.13, Flask, Dash, Pandas.

## Key Architectural Patterns

1.  **Hybrid Flask/Dash:**
    *   `app/app.py` initializes the Flask server first, then mounts the Dash app.
    *   Dash runs on the same server instance.
    *   Standard Flask routes handle API endpoints (e.g., for AI webhooks), while Dash handles the interactive UI.

2.  **Configuration Centralization (`app/conf.py`):**
    *   This is the **single source of truth** for UI structure.
    *   The `GlobalUInterface` class defines:
        *   `self.pages`: Dictionary of all dashboard pages (Home, AI Demos, Resume), their URLs, and active status.
        *   `self.layout`: Global UI shells (sidebar, navbar, footer).

3.  **Page Structure (`app/dash_app/pages/`):**
    *   Each page (e.g., `home.py`, `ai.py`) defines a `UInterface` class.
    *   The `UInterface` initializes specific components and layouts for that page.
    *   **Convention:** Page logic is encapsulated in its class.

4.  **Callbacks (`app/dash_app/callbacks.py`):**
    *   Dash callbacks are primarily registered here to keep page logic clean.
    *   It imports the UI classes from `pages/` to access component IDs.

5.  **AI callbacks run inside the request, one Gemini call each:**
    *   There is no task queue. The sales deck is planned by one callback (`gemini-3.8-flash`), which renders a placeholder per slide carrying an HMAC-signed job; a `MATCH` callback per slide renders it (`gemini-3.1-flash-image`). The browser fires those in parallel, so slides appear as they finish (~20s for a whole deck). The signature stops the slide callback from rendering arbitrary prompts.
    *   Cloud Run's request timeout (120s, Terraform) and gunicorn's `--timeout` (app/Dockerfile) must stay at least as long as one Gemini call.
    *   `dash_app/rate_limit.py` caps each visitor (last `X-Forwarded-For` entry, which Cloud Run sets) per 24h: 5 decks, 30 slide renders, 30 themes, 10 images. Counts are in memory, so gunicorn runs one worker.

## Content & Features

*   **Home / Portfolio (`pages/home.py`):**
    *   Landing page with professional introduction, employer logo strip (every file in `assets/images/company_logos/`), demo panels, and press coverage of analyses.
    *   **AI Agents:** ElevenLabs widgets, including Nick's AI Clone. Its knowledge base lives in ElevenLabs and is maintained by hand, not from this repo.
*   **Design Lab (`pages/ai.py`):** Gemini theme generator (text) and style-wrapped image generator.
*   **Sales Enablement (`pages/sales_enablement.py`):** progressive deck generator (see pattern 5).
*   **Layout:** below Bootstrap's lg breakpoint the fixed sidebar is replaced by a menu button + offcanvas; two-column sections carry `.stack-mobile` and stack below md (`assets/styles.css`). Charts autosize; don't give figures fixed widths.

## Common Tasks & Commands

*   **Run Local:** `flask --app app run -p 8050`
*   **Dependency Management:** Uses `uv` (e.g., `uv add <package>`).
*   **Deployment:** Push to `main` deploys the app; `./bootstrap.sh` plans/applies Terraform.

## Directory Map

*   `app/`: Application source.
*   `app/dash_app/assets/`: CSS, `posthog.js`, images (WebP; `share/` = 1200x630 link-preview JPGs), data CSVs.
    *   Everything in `assets/` is publicly downloadable at `/portfolio/assets/...`, so never put private data there.
*   `app/dash_app/pages/`: Dashboard logic.
*   `infrastructure/`: Terraform (Cloud Run, secrets, domain mapping, DNS, CI identity).

## External Data & APIs

*   **Google Gemini API:** text and image generation (key: Secret Manager `personal-portfolio-gemini-api-key`).
*   **ElevenLabs:** voice/chat agents embedded on the home page.
*   **PostHog:** web analytics, cookieless (`assets/posthog.js`, production hostname only).
*   **Link previews:** `app.py` wraps Dash's `_pages._path_to_page` so meta tags match pages under the `/portfolio` prefix; descriptions are `share_description` in `conf.py`.

## Infrastructure

*   **Containerization:** Dockerfile defines the runtime environment.
*   **IaC:** Terraform manages GCP resources:
    *   **Cloud Run:** service `personal-portfolio` (1 vCPU, 1 GiB, min 1 / max 3 instances) running as its own service account.
    *   **Domain:** Cloud Run domain mapping + DNS-only Cloudflare CNAME to `ghs.googlehosted.com`.
    *   **Storage:** Artifact Registry (Docker images), GCS bucket `ne-tf` prefix `default/state` (Terraform state; other projects' state shares the bucket).
    *   **Security:** Secret Manager (Flask keys, dedicated Gemini API key), Workload Identity Federation pool `personal-portfolio-github`.
*   **CI/CD:** GitHub Actions triggers builds on push to `main`.

- **Sales Enablement / Slide Deck Generation:**
    - The `python-pptx` approach produced only marginally acceptable results.
    - **Status:** Success.
    - **Approach:** We generate 5 high-fidelity slide images using Gemini (Imagen 3) based on a structured plan.
    - **Display:** Images are displayed in a Dash Carousel.
    - **Features:**
        *   **RAG Integration:** Injecting platform stats into the prompt.
        *   **GenAI Images:** Full slide generation via Imagen.
        *   **UX:** Example deck (Weyland-Yutani) loaded by default with an onboarding modal.