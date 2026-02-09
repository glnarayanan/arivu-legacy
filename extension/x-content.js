// x-content.js — Runs on x.com/twitter.com pages
// Scrapes tweet data from the DOM when requested by popup or background script

function scrapeTweetFromDOM() {
  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  if (!articles.length) return null;

  // If URL is a tweet permalink, grab the first (primary) tweet
  const isTweetPage = /\/status\/\d+/.test(window.location.pathname);
  const article = isTweetPage ? articles[0] : getMostVisibleArticle(articles);
  if (!article) return null;

  return extractTweetData(article);
}

function getMostVisibleArticle(articles) {
  const viewportCenter = window.innerHeight / 2;
  let closest = null;
  let closestDistance = Infinity;

  for (const article of articles) {
    const rect = article.getBoundingClientRect();
    const articleCenter = rect.top + rect.height / 2;
    const distance = Math.abs(articleCenter - viewportCenter);
    if (distance < closestDistance) {
      closestDistance = distance;
      closest = article;
    }
  }
  return closest;
}

function extractTweetData(article) {
  // Author info
  const userLinks = article.querySelectorAll('a[role="link"]');
  let authorUsername = '';
  let authorName = '';
  for (const link of userLinks) {
    const href = link.getAttribute('href') || '';
    if (href.match(/^\/[A-Za-z0-9_]+$/) && !href.startsWith('/i/')) {
      authorUsername = href.replace('/', '');
      const nameEl = link.querySelector('span');
      if (nameEl) authorName = nameEl.textContent.trim();
      break;
    }
  }

  // Tweet text
  const tweetTextEl = article.querySelector('[data-testid="tweetText"]');
  const tweetText = tweetTextEl ? tweetTextEl.innerText.trim() : '';

  // Timestamp & tweet ID
  const timeEl = article.querySelector('time');
  const createdAt = timeEl ? timeEl.getAttribute('datetime') : null;
  const timeLink = timeEl ? timeEl.closest('a') : null;
  const tweetHref = timeLink ? timeLink.getAttribute('href') : '';
  const tweetIdMatch = tweetHref.match(/\/status\/(\d+)/);
  const tweetId = tweetIdMatch ? tweetIdMatch[1] : null;

  // Metrics
  const metrics = {};
  const metricGroups = article.querySelectorAll('[role="group"] button');
  const metricNames = ['reply_count', 'retweet_count', 'like_count', 'view_count'];
  metricGroups.forEach((btn, i) => {
    if (i < metricNames.length) {
      const ariaLabel = btn.getAttribute('aria-label') || '';
      const numMatch = ariaLabel.match(/(\d[\d,]*)/);
      metrics[metricNames[i]] = numMatch ? parseInt(numMatch[1].replace(/,/g, ''), 10) : 0;
    }
  });

  // Media (images)
  const mediaUrls = [];
  const images = article.querySelectorAll('[data-testid="tweetPhoto"] img');
  images.forEach(img => {
    const src = img.getAttribute('src');
    if (src && !src.includes('emoji') && !src.includes('profile_images')) {
      mediaUrls.push(src);
    }
  });

  // External links in tweet
  const externalUrls = [];
  const cardLink = article.querySelector('[data-testid="card.wrapper"] a');
  if (cardLink) {
    const href = cardLink.getAttribute('href');
    if (href && !href.includes('x.com') && !href.includes('twitter.com')) {
      externalUrls.push(href);
    }
  }

  const tweetUrl = tweetId && authorUsername
    ? `https://x.com/${authorUsername}/status/${tweetId}`
    : window.location.href;

  return {
    tweet_id: tweetId,
    tweet_text: tweetText,
    tweet_url: tweetUrl,
    author_username: authorUsername,
    author_name: authorName,
    created_at: createdAt,
    metrics: metrics,
    media_urls: mediaUrls,
    external_urls: externalUrls,
  };
}

// Listen for scrape requests from popup or background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scrapeTweet') {
    const data = scrapeTweetFromDOM();
    sendResponse({ success: !!data, tweet: data });
  }
  return true;
});
