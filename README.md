# Scraperrrr 2: Glaido AI News Dashboard

A high-performance, premium AI news aggregator and dashboard.

## 🚀 Overview

Glaido is a sophisticated platform that aggregates AI news from curated sources (Ben's Bites, The Rundown AI, Reddit), enriches them with Open Graph images, and presents them in a sleek, high-fidelity React dashboard.

## 🏗️ Architecture

The project follows a modular 3-layer architecture:

1.  **Ingestion Layer (`tools/`)**: Python-based scrapers that fetch data from various sources.
2.  **Aggregation Layer (`tools/aggregator.py`)**: Merges data, filters promotional content, and enriches articles with metadata/images using parallel processing.
3.  **Visualization Layer (`dashboard/`)**: A premium React + TypeScript + Tailwind CSS dashboard with micro-animations.

## ⚙️ How it Works

1.  **Scraping**: The individual scripts in `tools/` fetch the latest articles and save them to `.tmp/`.
2.  **Aggregation**: `aggregator.py` runs all scrapers, applies smart filters, fetches missing thumbnails via OG tags, and generates `dashboard/public/data.json`.
3.  **Display**: The Vite-powered dashboard reads the JSON and displays it with a premium "Glassmorphism" UI.

## 🛠️ Getting Started

### Prerequisites

- Node.js (v18+)
- Python 3.9+
- Python packages: `requests`, `beautifulsoup4`, `asyncio`

### Running the Aggregator

```bash
python3 tools/aggregator.py
```

### Running the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## ✨ Features

- **Parallel Scraping**: Multiple sources fetched simultaneously.
- **Smart Filtering**: Automatically removes ads, sponsors, and meta-content.
- **OG Image Enrichment**: Automatically finds the best thumbnail for every article.
- **Premium UI**: Custom "Flow Field" background and smooth Framer Motion transitions.
- **Local Persistence**: Save articles for later reading.

---

Built with Antigravity / B.L.A.S.T Protocol.
