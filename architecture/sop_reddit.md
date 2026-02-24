# SOP: Reddit AI News Fetcher

## 🎯 Goal
Fetch top AI-related posts from the last 24 hours from relevant subreddits.

## 📥 Inputs
- **Subreddits:** `r/ArtificialInteligence`, `r/MachineLearning`, `r/openai`
- **Filter:** "New" or "Top" posts from the last 24 hours.

## ⚙️ Logic
1. Use Reddit API (PRAW) or Scraper.
2. Iterate through target subreddits.
3. Filter posts by `created_utc` (must be within last 86,400 seconds).
4. Ignore meta-posts or low-quality content (optional score filter).
5. Format into `ArticlePayload`.

## 📤 Outputs
- List of `ArticlePayload` objects.

## ⚠️ Edge Cases
- **Rate Limiting:** Ensure delays between requests.
- **Auth:** Reddit API requires Client ID/Secret.
