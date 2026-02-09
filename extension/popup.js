const DEFAULT_API_URL = 'https://arivu.app/api';

let currentTab = null;
let accessToken = null;
let refreshToken = null;
let apiUrl = DEFAULT_API_URL;

async function getApiUrl() {
  const result = await chrome.storage.local.get(['apiUrl']);
  return result.apiUrl || DEFAULT_API_URL;
}

async function init() {
  apiUrl = await getApiUrl();

  const tokenResult = await chrome.storage.session.get(['accessToken', 'refreshToken']);
  accessToken = tokenResult.accessToken;
  refreshToken = tokenResult.refreshToken;

  if (!accessToken) {
    document.getElementById('loginPrompt').style.display = 'block';
    const loginLink = document.getElementById('loginLink');
    const baseUrl = apiUrl.replace('/api', '');
    loginLink.href = `${baseUrl}/auth`;
    return;
  }

  document.getElementById('saveForm').style.display = 'block';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;

  document.getElementById('url').value = tab.url;
  document.getElementById('title').value = tab.title;

  // Detect x.com/twitter.com and scrape tweet data
  const isXPage = currentTab.url?.match(/https:\/\/(x\.com|twitter\.com)/);

  if (isXPage) {
    const stored = await chrome.storage.session.get(['pendingTweet']);
    let tweetData = stored.pendingTweet;

    if (!tweetData) {
      tweetData = await new Promise((resolve) => {
        chrome.tabs.sendMessage(currentTab.id, { action: 'scrapeTweet' }, (response) => {
          resolve(response?.success ? response.tweet : null);
        });
      });
    }

    if (tweetData) {
      await chrome.storage.session.remove(['pendingTweet']);

      document.getElementById('tweetPreview').style.display = 'block';
      document.getElementById('tweetContent').textContent = tweetData.tweet_text;
      document.getElementById('tweetAuthor').value =
        `@${tweetData.author_username}` + (tweetData.author_name ? ` (${tweetData.author_name})` : '');
      document.getElementById('url').value = tweetData.tweet_url || currentTab.url;
      document.getElementById('title').value = tweetData.tweet_text?.substring(0, 100) || currentTab.title;

      window._tweetData = tweetData;
    }
  }

  loadCollections();
}

async function loadCollections() {
  try {
    const response = await fetch(`${apiUrl}/collections`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    if (!response.ok) return;
    const collections = await response.json();

    const select = document.getElementById('collection');
    collections.forEach(col => {
      const option = document.createElement('option');
      option.value = col.id;
      option.textContent = col.name;
      select.appendChild(option);
    });
  } catch (error) {
    console.error('Failed to load collections:', error);
  }
}

document.getElementById('bookmarkForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const btn = document.getElementById('saveBtn');
  const status = document.getElementById('status');

  btn.disabled = true;
  btn.textContent = 'Saving...';
  status.style.display = 'none';

  try {
    const url = document.getElementById('url').value;
    const collectionId = document.getElementById('collection').value || null;

    const response = await fetch(`${apiUrl}/bookmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify((() => {
        const payload = { url, collection_id: collectionId };
        if (window._tweetData) {
          payload.source = 'x';
          payload.x_tweet_id = window._tweetData.tweet_id;
          payload.x_author_username = window._tweetData.author_username;
          payload.x_author_name = window._tweetData.author_name;
          payload.x_tweet_url = window._tweetData.tweet_url;
          payload.x_metrics = window._tweetData.metrics;
          payload.text_content = window._tweetData.tweet_text;
        }
        return payload;
      })())
    });

    if (response.ok) {
      status.className = 'status success';
      status.textContent = 'Saved — AI is processing';
      status.style.display = 'block';
      setTimeout(() => window.close(), 1500);
    } else if (response.status === 401) {
      await chrome.storage.session.remove(['accessToken', 'refreshToken']);
      status.className = 'status error';
      status.textContent = 'Session expired — reopen Arivu to reconnect';
      status.style.display = 'block';
    } else {
      throw new Error('Failed to save');
    }
  } catch (error) {
    status.className = 'status error';
    status.textContent = 'Failed to save bookmark';
    status.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Bookmark';
  }
});

// Settings toggle
const settingsToggle = document.getElementById('settingsToggle');
const settingsPanel = document.getElementById('settingsPanel');
const apiUrlInput = document.getElementById('apiUrlInput');

settingsToggle.addEventListener('click', async () => {
  const isVisible = settingsPanel.style.display === 'block';
  settingsPanel.style.display = isVisible ? 'none' : 'block';

  if (!isVisible) {
    apiUrlInput.value = await getApiUrl();
  }
});

apiUrlInput.addEventListener('change', async () => {
  const value = apiUrlInput.value.trim();
  if (value) {
    await chrome.storage.local.set({ apiUrl: value });
    apiUrl = value;
  } else {
    await chrome.storage.local.remove(['apiUrl']);
    apiUrl = DEFAULT_API_URL;
  }
});

init();
