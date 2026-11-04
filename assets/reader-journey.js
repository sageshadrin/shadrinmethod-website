/*
 * Shadrin Method reader journey tracking, v1.
 *
 * This script is deliberately usable before Google Analytics is configured:
 * links from articles identify their source, book pages retain it in UTM
 * parameters on Amazon links, and no Google script is loaded without the
 * visitor's opt-in plus a valid GA4 Measurement ID.
 *
 * Amazon sales attribution requires official Amazon Attribution links;
 * ordinary UTM parameters do not measure purchases on Amazon.
 */
(function () {
  "use strict";

  var config = window.SHADRIN_TRACKING || {};
  var ga4Id = typeof config.ga4_measurement_id === "string" &&
      /^G-[A-Z0-9]{7,}$/i.test(config.ga4_measurement_id)
      ? config.ga4_measurement_id : "";
  var attributionLinks = config.amazon_attribution_links || {};
  var choiceKey = "shadrin_analytics_choice_v1";
  var validArticles = {
    "replaying-work-conversations": true,
    "analysis-paralysis-at-work": true,
    "why-boss-criticism-still-hurts": true,
    "client-presentation-anxiety": true,
    "how-to-stop-thinking-about-work": true
  };

  var path = window.location.pathname;
  var language = /^\/ru\//.test(path) ? "ru" : "en";
  var articleMatch = path.match(/^\/(?:ru\/)?resources\/overthinking\/([a-z0-9-]+)\/?$/);
  var sourceArticle = articleMatch && validArticles[articleMatch[1]] ? articleMatch[1] : "";
  var bookMatch = path.match(/^\/(?:ru\/)?books\/([a-z0-9-]+)\/?$/);
  var bookId = bookMatch ? bookMatch[1] : "";
  var query = new URLSearchParams(window.location.search);
  var fromArticle = bookId && validArticles[query.get("from")] ? query.get("from") : "";
  var fromLanguage = fromArticle && /^(en|ru)$/.test(query.get("src_lang") || "")
    ? query.get("src_lang") : language;
  var gaReady = false;
  var impressionSent = false;

  function targetOf(anchor) {
    try { return new URL(anchor.getAttribute("href"), window.location.href); }
    catch (err) { return null; }
  }

  function isAmazon(url) {
    return url && /^(?:www\.)?amazon\.[a-z.]+$/i.test(url.hostname);
  }

  function bookFromUrl(url) {
    if (!url || url.origin !== window.location.origin) return "";
    var match = url.pathname.match(/^\/(?:ru\/)?books\/([a-z0-9-]+)\/?$/);
    return match ? match[1] : "";
  }

  function emit(name, parameters) {
    if (!gaReady || typeof window.gtag !== "function") return;
    window.gtag("event", name, parameters || {});
  }

  function sendBookLandingEvent() {
    if (!bookId || !fromArticle || impressionSent) return;
    impressionSent = true;
    emit("book_view_from_article", {
      book_id: bookId,
      article_id: fromArticle,
      article_language: fromLanguage
    });
  }

  function startGoogleAnalytics() {
    if (!ga4Id || gaReady) return;
    gaReady = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", ga4Id);
    var tag = document.createElement("script");
    tag.async = true;
    tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(ga4Id);
    document.head.appendChild(tag);
    sendBookLandingEvent();
  }

  function readChoice() {
    try { return window.localStorage.getItem(choiceKey); }
    catch (err) { return null; }
  }

  function saveChoice(value) {
    try { window.localStorage.setItem(choiceKey, value); }
    catch (err) { /* No persistence in private browsing mode. */ }
  }

  function addConsentStyles() {
    if (document.getElementById("shadrin-analytics-styles")) return;
    var css = document.createElement("style");
    css.id = "shadrin-analytics-styles";
    css.textContent = ".shadrin-consent{position:fixed;bottom:12px;left:12px;right:12px;z-index:1000;max-width:800px;margin:auto;padding:19px 23px;background:#182538;color:#f5f4f0;border:1px solid #dfb87b;border-radius:10px;box-shadow:0 15px 45px #0008;font:15px/1.6 system-ui,sans-serif}.shadrin-consent p{margin:0 0 14px}.shadrin-consent-actions{display:flex;flex-wrap:wrap;gap:12px}.shadrin-consent button,.shadrin-consent-settings{cursor:pointer;font:inherit}.shadrin-consent button{padding:8px 15px;border:1px solid #dfb87b;border-radius:5px;background:#dfb87b;color:#172132;font-weight:700}.shadrin-consent button.shadrin-decline{background:transparent;color:#dfb87b}.shadrin-consent-settings{background:transparent;border:0;color:#b6c0cd;text-decoration:underline;padding:0}";
    document.head.appendChild(css);
  }

  function showConsent() {
    if (!ga4Id || document.getElementById("shadrin-analytics-consent")) return;
    addConsentStyles();
    var box = document.createElement("section");
    box.id = "shadrin-analytics-consent";
    box.className = "shadrin-consent";
    box.setAttribute("aria-label", language === "ru" ? "Настройки аналитики" : "Analytics preferences");
    var explanation = document.createElement("p");
    explanation.textContent = language === "ru"
      ? "Помогите улучшить сайт: разрешите Google Analytics собирать статистику посещений и переходов к книгам. Без согласия аналитика не загружается."
      : "Help improve this site: allow Google Analytics to measure visits and clicks to books. Analytics does not load without your consent.";
    var actions = document.createElement("div");
    actions.className = "shadrin-consent-actions";
    var yes = document.createElement("button");
    yes.type = "button";
    yes.textContent = language === "ru" ? "Разрешить аналитику" : "Allow analytics";
    var no = document.createElement("button");
    no.type = "button";
    no.className = "shadrin-decline";
    no.textContent = language === "ru" ? "Не разрешать" : "Decline";
    yes.addEventListener("click", function () {
      saveChoice("accepted");
      box.remove();
      startGoogleAnalytics();
    });
    no.addEventListener("click", function () {
      saveChoice("declined");
      box.remove();
      if (gaReady) window.location.reload();
    });
    actions.appendChild(yes);
    actions.appendChild(no);
    box.appendChild(explanation);
    box.appendChild(actions);
    document.body.appendChild(box);
  }

  function addSettingsControl() {
    if (!ga4Id) return;
    var target = document.querySelector("footer .container");
    if (!target || document.getElementById("shadrin-analytics-settings")) return;
    var btn = document.createElement("button");
    btn.id = "shadrin-analytics-settings";
    btn.className = "shadrin-consent-settings";
    btn.type = "button";
    btn.textContent = language === "ru" ? "Настройки аналитики" : "Analytics preferences";
    btn.addEventListener("click", showConsent);
    target.appendChild(btn);
  }

  function positionOf(anchor) {
    if (anchor.closest && anchor.closest(".book-lead")) return "primary";
    if (anchor.closest && anchor.closest(".book-end")) return "bottom";
    return "other";
  }

  function prepareLinks() {
    var anchors = document.querySelectorAll("a[href]");
    for (var i = 0; i < anchors.length; i++) {
      var anchor = anchors[i], url = targetOf(anchor);
      if (!url) continue;

      // Source query parameters survive even when analytics is unavailable.
      if (sourceArticle && bookFromUrl(url) === "overthinking") {
        url.searchParams.set("from", sourceArticle);
        url.searchParams.set("src_lang", language);
        anchor.href = url.pathname + url.search + url.hash;
      }

      if (!bookId || !isAmazon(url)) continue;

      // Unique official Amazon Attribution tags, once provided by Amazon,
      // are used exactly as generated; never append UTM values to those tags.
      var attributionKey = bookId + ":" + (fromArticle ? fromLanguage + ":" + fromArticle : "direct");
      var officialTag = attributionLinks[attributionKey];
      if (typeof officialTag === "string" && officialTag) {
        try {
          var taggedUrl = new URL(officialTag);
          if (taggedUrl.protocol === "https:" && isAmazon(taggedUrl)) {
            anchor.href = officialTag;
            continue;
          }
        } catch (err) { /* Fall back to the original Amazon URL. */ }
      }

      // Fallback UTM tagging records the referring article in the link.
      // This does NOT mean an Amazon purchase can be attributed to it.
      if (fromArticle) {
        url.searchParams.set("utm_source", "shadrinmethod.com");
        url.searchParams.set("utm_medium", "referral");
        url.searchParams.set("utm_campaign", bookId === "overthinking" ? "book2_overthinking" : "book_" + bookId);
        url.searchParams.set("utm_content", fromLanguage + "_article_" + fromArticle + "_" + positionOf(anchor));
        anchor.href = url.toString();
      }
    }
  }

  function trackClicks() {
    document.addEventListener("click", function (event) {
      var anchor = event.target && event.target.closest ? event.target.closest("a[href]") : null;
      if (!anchor) return;
      var url = targetOf(anchor);
      if (!url) return;
      var destinationBook = bookFromUrl(url);
      if (sourceArticle && destinationBook) {
        emit("article_to_book", {
          article_id: sourceArticle,
          article_language: language,
          book_id: destinationBook,
          link_position: anchor.closest(".article-book-feature") ? "featured" : "editorial"
        });
      }
      if (isAmazon(url)) {
        emit("book_to_amazon", {
          article_id: fromArticle || "direct",
          article_language: fromArticle ? fromLanguage : language,
          book_id: bookId || "other",
          link_position: positionOf(anchor),
          transport_type: "beacon"
        });
      }
    }, true);
  }

  function setup() {
    prepareLinks();
    trackClicks();
    if (!ga4Id) return;
    addSettingsControl();
    if (readChoice() === "accepted") startGoogleAnalytics();
    else if (readChoice() !== "declined") showConsent();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
  else setup();
})();
