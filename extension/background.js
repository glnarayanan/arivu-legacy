// Context menu for saving tweets
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-tweet-to-arivu',
    title: 'Save tweet to Arivu',
    contexts: ['page', 'link'],
    documentUrlPatterns: ['https://x.com/*', 'https://twitter.com/*'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'save-tweet-to-arivu' && tab?.id) {
    chrome.tabs.sendMessage(tab.id, { action: 'scrapeTweet' }, (response) => {
      if (response?.success && response.tweet) {
        chrome.storage.session.set({ pendingTweet: response.tweet });
        chrome.action.openPopup();
      }
    });
  }
});

chrome.commands.onCommand.addListener((command) => {
  if (command === 'save-bookmark') {
    chrome.action.openPopup();
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveTokens') {
    chrome.storage.session.set({
      accessToken: request.accessToken,
      refreshToken: request.refreshToken,
    });
    sendResponse({ success: true });
  }
  return true;
});
