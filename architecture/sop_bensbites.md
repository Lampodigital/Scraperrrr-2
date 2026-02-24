# SOP: Ben's Bites Scraper

## 🎯 Goal
Extract the latest AI news articles from the last 24 hours from `bensbites.com`.

## 📥 Inputs
- **Base URL:** `https://www.bensbites.com/` (or beehiiv archive)
- **Time Window:** 24 Hours

## ⚙️ Logic
1. Navigate to the archive/home page.
2. Identify the latest newsletter issue.
3. Parse the issue for article links, titles, and summaries.
4. Filter articles by publication date (if available) or simply take the latest issue's content.
5. Format findings into the `ArticlePayload` schema defined in `gemini.md`.

## 📤 Outputs
- List of `ArticlePayload` objects.

## ⚠️ Edge Cases
- **Dynamic Loading:** Use `playwright` if the page doesn't render static HTML.
- **Paywalls/Popups:** Implement logic to close or ignore newsletter modals.
