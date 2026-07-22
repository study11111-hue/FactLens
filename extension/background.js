/**
 * FactLens — Background Service Worker
 * Manages extension lifecycle and connection state.
 */

// Default settings
const DEFAULT_SETTINGS = {
  backendUrl: 'wss://factlens-production-8178.up.railway.app/ws/factcheck',
  enabled: true,
  sessionId: null,
};

// Initialize settings on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set(DEFAULT_SETTINGS);
  console.log('FactLens installed — default settings applied');
});

// Handle messages from content script and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_SETTINGS') {
    chrome.storage.local.get(
      ['backendUrl', 'enabled', 'sessionId'],
      (settings) => {
        sendResponse({
          backendUrl: settings.backendUrl || DEFAULT_SETTINGS.backendUrl,
          enabled: settings.enabled !== undefined ? settings.enabled : true,
          sessionId: settings.sessionId,
        });
      }
    );
    return true; // Keep channel open for async response
  }

  if (message.type === 'UPDATE_SETTINGS') {
    chrome.storage.local.set(message.settings, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (message.type === 'GET_STATUS') {
    sendResponse({ status: 'active' });
    return true;
  }
});
