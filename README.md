# Personal Portfolio & AI Demo Platform

A professional portfolio and technical demonstration platform showcasing capabilities in Data Engineering, BI, and AI/LLM integration.

Built using **Flask** as the web framework and **Plotly Dash** for interactive analytics, served serverless on **Google Cloud Run**.

## Features

*   **Interactive Portfolio:** A data-driven resume and portfolio section parsed dynamically from JSON.
*   **BI Dashboard Demo:** A fully interactive executive dashboard demonstrating advanced filtering, cross-filtering, and dynamic aggregation using Pandas and Plotly.
*   **AI Design Lab:**
    *   **Theme Generator:** Uses Gemini/LLMs to generate color palettes and CSS themes from natural language prompts.
    *   **Asset Generator:** Creates consistent visual assets on the fly.
*   **Sales Enablement Tool:** An AI-powered agent that generates tailored sales presentation outlines and slide content based on prospect data.
*   **Enterprise-Grade Architecture:**
    *   **Hybrid Flask/Dash:** Seamless integration of standard web routes with reactive Dash apps.
    *   **Serverless Hosting:** Runs on Cloud Run with a warm instance for instant first loads, autoscaling under load, and Google-managed TLS on the custom domain.
    *   **Keyless CI/CD:** GitHub Actions deploys via Workload Identity Federation, with no long-lived credentials; all infrastructure is Terraform.
    *   **Security:** Google OAuth 2.0 authentication with role-based access control (RBAC).

## Tech Stack

*   **Core:** Python 3.13, Flask, Plotly Dash
*   **Data:** Pandas, DuckDB
*   **AI/LLM:** OpenAI API, Google Gemini
*   **Infrastructure:** Docker, Terraform, Google Cloud Run
*   **Package Management:** uv

## Project Structure

```text
base-insights-app/
├── app/
│   ├── app.py                  # Main Flask entry point
│   ├── auth.py                 # Google OAuth & session logic
│   ├── conf.py                 # Global UI configuration & page definitions
```

## ⚡ Local Development

### Prerequisites

*   Python 3.13+
*   uv (for dependency management)

### 1. Clone & Setup

```bash
git clone <repository-url>
cd base-insights-app
uv sync  # Installs dependencies from uv.lock
```

### 2. Environment Variables

Create a `.env` file in the repository root directory with the following keys:

```ini
DEPLOY_ENV=dev
FLASK_SECRET_KEY=<your-secret-key>
FLASK_ENCRYPTION_KEY=<fernet-key>
GEMINI_API_KEY=<gemini-api-key>
SERVER_NAME=Personal Portfolio
DISPLAY_NAME=Personal Portfolio
ENABLE_GOOGLE_AUTH=true # or false for local dev without auth
GOOGLE_OAUTH_CLIENT_ID=<client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
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

This manages the Cloud Run service, its runtime service account and secrets (Flask keys and a dedicated Gemini API key in Secret Manager), Artifact Registry, the custom domain mapping and Cloudflare DNS record, and the Workload Identity Federation pool GitHub Actions uses. It also writes the GitHub Actions secrets and variables the workflow needs. The script reads the Cloudflare token from Secret Manager and authenticates the GitHub provider with `gh auth token`.

### 2. Deploy Application

Push to `main`. The workflow builds the image, pushes it to Artifact Registry, and runs `gcloud run deploy` with the new image. Only the image changes on deploy; every other service setting is owned by Terraform.

### DNS & TLS

`cloudflare_record.app_dns` is a DNS-only (unproxied) CNAME to `ghs.googlehosted.com`. Google issues and renews the certificate for the domain mapping automatically. The record must stay unproxied or certificate issuance fails.

## Authentication & Access

*   **Google Auth:** Managed in `app/auth.py`.
*   **Access Control:**
    *   **Groups:** Permissions are defined in `app/conf.py` using `permission_groups` which map internal departments (from `internal_employees`) to roles (e.g., `EXECUTIVE`, `FIELD_LEADERSHIP`).
    *   **Page Access:** Each page in `conf.py` defines which `access_groups` are allowed to view it.
