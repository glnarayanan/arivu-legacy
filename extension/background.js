chrome.commands.onCommand.addListener((command) => {
  if (command === 'save-bookmark') {
    chrome.action.openPopup();
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveTokens') {
    chrome.storage.local.set({
      accessToken: request.accessToken,
      refreshToken: request.refreshToken
    });
    sendResponse({ success: true });
  }
  // Legacy support for old token format
  if (request.action === 'saveToken') {
    chrome.storage.local.set({
      accessToken: request.token,
      refreshToken: request.token  // Fallback
    });
    sendResponse({ success: true });
  }
  return true;
});