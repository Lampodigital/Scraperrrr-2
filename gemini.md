# 📄 Project Constitution: Scraperrrr 2

## 🎯 Project Overview
**North Star:** Build a premium, gorgeous, and interactive dashboard that aggregates the latest AI news and articles (from the last 24 hours) from curated sources (Ben's Bites, The Rundown AI, Reddit). The system must support "Saving" articles with persistence across refreshes.

## 🏗️ Architectural Invariants
1. **Protocol:** B.L.A.S.T. (Blueprint, Link, Architect, Stylize, Trigger)
2. **Architecture:** A.N.T. 3-Layer (Architecture, Navigation, Tools)
3. **Data-First:** All tools must have defined schemas here before implementation.
4. **Self-Healing:** Failures trigger the Repair Loop (Analyze -> Patch -> Test -> Update Architecture).
5. **Aesthetics:** The UI must be professional, interactive, and visually stunning.
6. **Design System:** Follow the "Scraper Design Brand Guidelines" (Neon Lime on Deep Black).

## 🎨 Design Guidelines
- **Primary/Accent:** `#BFF549` (Neon Lime)
- **Background:** `#0D0D0D` (Deep Black)
- **Text (On Primary):** `#0D0D0D`
- **Link:** `#0000EE`
- **Typography:**
    - Heading: `Aspekta` (h1: 76px, h2: 52px)
    - Body: `Inter` (16px)
    - Monospace: `Geist Mono`

## 📊 Data Schemas
### Article Payload (Output Shape)
```json
{
  "id": "string (uuid or hash)",
  "title": "string",
  "source": "string (Ben's Bites | The Rundown AI | Reddit)",
  "url": "string",
  "summary": "string (optional)",
  "published_at": "ISO8601 string",
  "thumbnail": "string (url)",
  "tags": ["string"],
  "is_saved": "boolean"
}
```

### Dashboard State (Persistence)
```json
{
  "last_updated": "ISO8601 string",
  "articles": ["ArticlePayload"],
  "saved_ids": ["string"]
}
```

## 📜 Behavioral Rules
1. **Freshness:** Only display articles published within the last 24 hours.
2. **Persistence:** Saved articles must persist across sessions (Storage: LocalStorage initially, Supabase later).
3. **Automation:** The system should be designed to run/check for updates every 24 hours.
4. **No Placeholders:** All UI elements must be functional or clearly marked as "Build in Progress".

## 🛠️ Maintenance Log
- [2026-02-23] Initialization of Project Constitution.
