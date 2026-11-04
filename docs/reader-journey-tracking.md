# Shadrin Method — Reader Journey Tracking V1 (2026-11-03)

## Status

- Source-aware navigation code: **installed on all 28 HTML pages**.
- Google Analytics 4: **NOT LIVE** until the real `G-...` ID is added to `assets/tracking-config.js`; the user has not yet supplied one.
- Amazon Attribution: **NOT LIVE** until official Amazon-generated attribution URLs are added.
- No paid services are required by the site implementation.

## How the click path works

1. A visitor reads one of the four published Overthinking articles in English or Russian.
2. A link from the article to `/books/overthinking/` (or `/ru/books/overthinking/`) receives the URL query parameters `from=<article_slug>&src_lang=<language>`.
3. The book page reads only four approved article slugs; with analytics consent and a valid GA4 ID, it sends the `book_view_from_article` event.
4. The visit's Amazon links receive an article-specific `utm_content` value if no official Amazon Attribution URL is configured.
5. If an official Amazon Attribution link is present for that book and source, the system replaces the outbound link **exactly** with that Amazon-generated URL, without modifying its parameters.
6. With analytics consent and a valid GA4 ID, clicks trigger `article_to_book` and `book_to_amazon` events.

The site can observe a click to Amazon but **cannot confirm a purchase on Amazon through Google Analytics**. KDP sales attribution requires Amazon Attribution.

## GA4 setup: manual ID required

Create or locate a GA4 property, add a web data stream for `https://shadrinmethod.com/`, and copy its Measurement ID (`G-...`). In `assets/tracking-config.js`, update:

```js
ga4_measurement_id: "G-ACTUAL_ID_HERE",
```

Only then will Google Analytics be offered via a language-appropriate consent banner. The Google tag loads after opt-in; visitors may change their choice from the footer.

Events:
- `article_to_book`: clicking from an article to a book page.
- `book_view_from_article`: landing on the book page carrying a valid article source.
- `book_to_amazon`: clicking an Amazon link (not a purchase).

Event parameters: `article_id`, `article_language`, `book_id`, `link_position`. Register relevant event-scoped custom dimensions in GA4 for convenient breakdowns, and check Realtime/DebugView after connecting the measurement ID.

## Amazon Attribution setup: official URLs required

Amazon officially supports Amazon Attribution for eligible KDP accounts. In the Amazon Ads advertising console, open **Measurement and Reporting → Amazon Attribution**, create one campaign for Book II (Overthinking, ASIN B0HM27MPX7), and create separate ad groups or tags for the following sources, using shadrinmethod.com as the publisher and the corresponding organic channel where available:

| Suggested ad group | Config key |
|---|---|
| Site Direct / Overthinking | `overthinking:direct` |
| EN / Replay Conversations | `overthinking:en:replaying-work-conversations` |
| RU / Replay Conversations | `overthinking:ru:replaying-work-conversations` |
| EN / Analysis Paralysis | `overthinking:en:analysis-paralysis-at-work` |
| RU / Analysis Paralysis | `overthinking:ru:analysis-paralysis-at-work` |
| EN / Boss Criticism | `overthinking:en:why-boss-criticism-still-hurts` |
| RU / Boss Criticism | `overthinking:ru:why-boss-criticism-still-hurts` |
| EN / Presentation Anxiety | `overthinking:en:client-presentation-anxiety` |
| RU / Presentation Anxiety | `overthinking:ru:client-presentation-anxiety` |

Paste each corresponding **exact** generated tag URL into `amazon_attribution_links` in `assets/tracking-config.js`:

```js
amazon_attribution_links: Object.freeze({
  "overthinking:direct": "https://www.amazon.com/...",
  "overthinking:en:replaying-work-conversations": "https://www.amazon.com/..."
})
```

Do not fabricate Amazon Attribution tags or add/change parameters on an official tagged URL. Create separate tags for editions only if the Amazon Attribution console requires or benefits from distinct promoted products. Other books can later use book IDs matching the website URL, e.g. `behavioral-patterns:direct`.

Amazon Attribution uses a 14-day last-touch attribution model (not all sales are necessarily assigned to the site). Standard UTM parameters on Amazon links alone **do not** confirm conversions.

## Code

- `assets/tracking-config.js` — measurement ID and exact official Amazon Attribution URLs.
- `assets/reader-journey.js` — first-party reader journey and optional GA4 event tracking.
- All website `index.html` files include these two scripts with `defer`.

## Operating checklist

- Confirm the GitHub Pages deployment is successful.
- Check article → book link contains `?from=<slug>&src_lang=<lang>`.
- Check the book → Amazon link contains article-specific `utm_content` until official tags are supplied.
- With GA4 configured and analytics consent, use Realtime/DebugView to confirm three events.
- With Amazon Attribution tags configured, use Amazon Attribution reports to assess attributed purchases, units and royalties where the account supports those metrics.
- Never equate clicks with confirmed book sales.
