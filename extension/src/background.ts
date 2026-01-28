/**
 * ScriptorAI Background Service Worker
 */

import { api } from './utils/api';

// Initialize API on startup
api.init();

// Context menu setup
chrome.runtime.onInstalled.addListener(() => {
  // Create context menu for PDFs
  chrome.contextMenus.create({
    id: 'add-to-scriptor',
    title: 'Add to Scriptor',
    contexts: ['link', 'page'],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'add-to-scriptor') {
    const url = info.linkUrl || info.pageUrl;

    if (!url) return;

    // Check if it looks like a PDF
    const isPdf = url.toLowerCase().includes('.pdf') ||
                  info.linkUrl?.toLowerCase().includes('.pdf') ||
                  tab?.url?.toLowerCase().includes('.pdf');

    if (!isPdf) {
      // Notify user it might not be a PDF
      chrome.notifications?.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'ScriptorAI',
        message: 'This may not be a PDF. Attempting to add anyway...',
      });
    }

    try {
      await api.init();

      if (!api.isPaired()) {
        chrome.notifications?.create({
          type: 'basic',
          iconUrl: 'icons/icon48.png',
          title: 'ScriptorAI',
          message: 'Please pair with Scriptor Local first. Open the side panel to pair.',
        });
        return;
      }

      const result = await api.addPaper(url, tab?.title);

      chrome.notifications?.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'Added to Scriptor',
        message: `"${result.title}" added. Run batch to index.`,
      });

      // Notify side panel to refresh
      chrome.runtime.sendMessage({ type: 'PAPERS_UPDATED' }).catch(() => {});

    } catch (error) {
      chrome.notifications?.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: 'ScriptorAI Error',
        message: error instanceof Error ? error.message : 'Failed to add paper',
      });
    }
  }
});

// Handle keyboard shortcut
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'toggle-side-panel') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      chrome.sidePanel.open({ tabId: tab.id });
    }
  }
});

// Handle extension action click (open side panel)
chrome.action.onClicked.addListener(async (tab) => {
  if (tab.id) {
    chrome.sidePanel.open({ tabId: tab.id });
  }
});

// Handle messages from content scripts and side panel
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_CURRENT_TAB_INFO') {
    chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
      const isPdf = tab?.url?.toLowerCase().includes('.pdf') ||
                    tab?.url?.includes('reader.html');
      sendResponse({
        url: tab?.url,
        title: tab?.title,
        isPdf,
      });
    });
    return true; // Async response
  }

  if (message.type === 'OPEN_READER') {
    const readerUrl = chrome.runtime.getURL(`reader.html?paperId=${message.payload.paperId}`);
    chrome.tabs.create({ url: readerUrl });
    sendResponse({ success: true });
    return true;
  }

  if (message.type === 'CHECK_CONNECTION') {
    api.init().then(() => api.checkHealth())
      .then((health) => sendResponse({ connected: true, health }))
      .catch(() => sendResponse({ connected: false }));
    return true;
  }
});

// Set up side panel behavior
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});

console.log('ScriptorAI background service worker initialized');
