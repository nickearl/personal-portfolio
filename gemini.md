# Gemini Context: Personal Portfolio

This file contains context and architectural notes for the `personal-portfolio` repository to assist AI agents.

## Project Overview

*   **Name:** `personal-portfolio`
*   **Type:** Flask application embedding a Plotly Dash multipage app.
*   **Goal:** A professional portfolio and technical demonstration platform showcasing capabilities in Data Engineering, BI, and AI/LLM integration.
*   **Stack:** Python 3.13, Flask, Dash, Redis, Celery, Pandas.

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

5.  **Background Tasks (Celery/Redis):**
    *   Used for long-running AI tasks (e.g., image generation, complex RAG queries) to prevent blocking the UI.

## Content & Features

*   **Home / Portfolio (`pages/home.py`):**
    *   Landing page with professional introduction.
    *   **Interactive Resume:** Data sourced from `assets/data/resume.json`. Parsed and rendered dynamically.
    *   **Press Coverage:** Carousel of articles and media mentions.
*   **AI Demonstrations (`pages/ai.py`):**
    *   **Generative UI:** Using OpenAI to generate color themes and CSS on the fly based on user prompts.
    *   **Image Generation:** DALL-E 3 integration for dynamic asset creation.
    *   **Virtual Interviewer:** Integration with ElevenLabs and LLMs to simulate a voice-interactive interview (Nick's AI Clone).

## Common Tasks & Commands

*   **Run Local:** `flask --app app run -p 8050`
*   **Run Celery:** `celery -A app:celery_app worker ...`
*   **Dependency Management:** Uses `uv` (e.g., `uv add openai`).
*   **Deployment:** Dockerized deployment via Terraform to Google Cloud Run.

## Directory Map

*   `app/`: Application source.
*   `app/dash_app/assets/`: CSS, Images, and Data Files (`resume.json`).
*   `app/dash_app/pages/`: Dashboard logic.
*   `modules/`: Terraform infrastructure modules.

## External Data & APIs

*   **OpenAI API:** Used for text and image generation.
*   **ElevenLabs API:** Used for voice synthesis and conversational AI.
*   **Local Data:** `resume.json` acts as the primary data source for the portfolio section, treated as a structured document store.

## Infrastructure

*   **Containerization:** Dockerfile defines the runtime environment.
*   **IaC:** Terraform manages GCP resources (Cloud Run, Redis, Secret Manager).
*   **CI/CD:** GitHub Actions triggers builds on push.

- **Sales Enablement / Slide Deck Generation:**
    - The `python-pptx` approach produced only marginally acceptable results.
    - **Status:** Success.
    - **Approach:** We generate 5 high-fidelity slide images using Gemini (Imagen 3) based on a structured plan.
    - **Display:** Images are displayed in a Dash Carousel.
    - **Features:**
        *   **RAG Integration:** Injecting platform stats into the prompt.
        *   **GenAI Images:** Full slide generation via Imagen.
        *   **UX:** Example deck (Weyland-Yutani) loaded by default with an onboarding modal.