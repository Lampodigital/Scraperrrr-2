# 🔍 Findings & Research

## 🧪 Discoveries
- **Ben's Bites:** Primary archive found at `bensbites.com` (likely Beehiiv).
- **The Rundown AI:** Primary archive at `therundown.ai`. Verified via Playwright (Status 200).
- **Reddit:** Highly active subreddits for AI news. Initial Playwright check returned 403 Forbidden. Will likely require API (PRAW) or advanced header spoofing.

- **Newsletter Authenticated Scraping:** Bypassed paywalls on Rundown and Ben's Bites using session cookies and manual "handshake" process.
- **Image Extraction:** Inline image extraction is brittle for newsletter layouts; parallel OpenGraph (OG) fetching in `aggregator.py` provides much higher reliability and fidelity.
- **Content Filtering:** Newsletter archives contain significant "junk" (RSVPs, workshops, referral links). A keyword-based filter in the aggregator is essential for a premium experience.
- **Reddit:** Still challenging for OG images due to rate limiting/scraping protections on Reddit's link-out pages.

## 📚 Resources
- [The Rundown AI Archive](https://www.therundown.ai/)
- [Ben's Bites Archive](https://www.bensbites.com/)
- [Reddit AI Search](https://www.reddit.com/r/ArtificialInteligence/new/)
