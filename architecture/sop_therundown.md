# SOP: The Rundown AI Scraper

## 🎯 Goal
Extract the latest AI news articles from the last 24 hours from `therundown.ai`.

## 📥 Inputs
- **Base URL:** `https://www.therundown.ai/`
- **Time Window:** 24 Hours

## ⚙️ Logic
1. Navigate to the archive page.
2. Extract the post list.
3. For each post:
    - Check if it was published within the last 24 hours.
    - Extract Title, URL, and Thumbnail.
    - (Optionally) Visit the URL to get a summary if not present on the list page.
4. Format findings into the `ArticlePayload` schema.

## 📤 Outputs
- List of `ArticlePayload` objects.

## ⚠️ Edge Cases
- **Pagination:** Check if multiple pages need to be crawled to cover 24 hours (unlikely for daily newsletters).
- **Structure Changes:** Monitor for selector failures.
