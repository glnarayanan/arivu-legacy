chrome.commands.onCommand.addListener((command) => {
  if (command === 'save-bookmark') {
    chrome.action.openPopup();
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveToken') {
    chrome.storage.local.set({ token: request.token });
    sendResponse({ success: true });
  }
  return true;
});