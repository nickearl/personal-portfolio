# Personal Portfolio & AI Demo Platform

A professional portfolio and technical demonstration platform showcasing capabilities in Data Engineering, BI, and AI/LLM integration.

Built using **Flask** as the web framework and **Plotly Dash** for interactive analytics, with **Redis** and **Celery** managing background tasks and caching.

## Features

*   **Interactive Portfolio:** A data-driven resume and portfolio section parsed dynamically from JSON.
*   **BI Dashboard Demo:** A fully interactive executive dashboard demonstrating advanced filtering, cross-filtering, and dynamic aggregation using Pandas and Plotly.
*   **AI Design Lab:**
    *   **Theme Generator:** Uses Gemini/LLMs to generate color palettes and CSS themes from natural language prompts.
    *   **Asset Generator:** Creates consistent visual assets on the fly.
*   **Sales Enablement Tool:** An AI-powered agent that generates tailored sales presentation outlines and slide content based on prospect data.
*   **Enterprise-Grade Architecture:**
    *   **Hybrid Flask/Dash:** Seamless integration of standard web routes with reactive Dash apps.
    *   **Async Processing:** Celery workers handle long-running AI inference tasks to keep the UI responsive.
    *   **Security:** Google OAuth 2.0 authentication with role-based access control (RBAC).

## Tech Stack

*   **Core:** Python 3.13, Flask, Plotly Dash
*   **Data & Async:** Pandas, Redis, Celery
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
*   Redis (running locally or accessible via URL)

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
REDIS_URL=redis://localhost:6379/0
SERVER_NAME=Personal Portfolio
DISPLAY_NAME=Personal Portfolio
ENABLE_GOOGLE_AUTH=true # or false for local dev without auth
GOOGLE_OAUTH_CLIENT_ID=<client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
```

### 3. Running the App

You need two terminal sessions:

**Terminal 1: Flask/Dash Server**
```bash
flask --app ./app/app run -p 1701
```

**Terminal 2: Celery Worker**
```bash
celery --workdir app -A app:celery_app worker --loglevel=INFO --concurrency=2 -Q Base-Insights
```

The app will be available at `http://localhost:1701/`.

## Deployment

Deployment is fully automated via **Terraform** (Infrastructure) and **GitHub Actions** (Application Code).

### 1. Provision Infrastructure
Run the bootstrap script to initialize and apply Terraform. This creates the VM, Networking, and Artifact Registry.

```bash
./bootstrap.sh
```

### 2. Configure Secrets
Terraform will output the secrets needed for CI/CD. Add these to your GitHub Repository under **Settings > Secrets and variables > Actions**:
*   `GCP_WORKLOAD_IDENTITY_PROVIDER`
*   `GCP_SERVICE_ACCOUNT`
*   `GCP_SSH_PRIVATE_KEY`

### 3. Deploy Application
The application is deployed automatically when you push to the `main` branch.

1.  Commit and push your code:
    ```bash
    git push origin main
    ```
2.  **Wait**: The GitHub Action will build the Docker image, push it to Google Artifact Registry, and deploy it to the VM.
3.  The app will launch automatically.

### DNS & SSL
DNS is managed by Cloudflare. Ensure you have the following variables in your `terraform.tfvars`:
*   `cloudflare_api_token`: API Token with `Zone.DNS` permissions.
*   `cloudflare_zone_id`: The Zone ID for your domain found in the Cloudflare dashboard.

## Authentication & Access

*   **Google Auth:** Managed in `app/auth.py`.
*   **Access Control:**
    *   **Groups:** Permissions are defined in `app/conf.py` using `permission_groups` which map internal departments (from `internal_employees`) to roles (e.g., `EXECUTIVE`, `FIELD_LEADERSHIP`).
    *   **Page Access:** Each page in `conf.py` defines which `access_groups` are allowed to view it.
