// Content script for Arivu extension
// Can be used to extract additional page metadata if needed

window.addEventListener('message', (event) => {
  if (event.data.type === 'ARIVU_SAVE_TOKEN') {
    chrome.runtime.sendMessage({
      action: 'saveToken',
      token: event.data.token
    });
  }
});