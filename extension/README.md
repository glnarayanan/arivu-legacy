# Arivu Browser Extension

Quick save bookmarks to Arivu with AI-powered summaries.

## Installation

### Chrome
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `/app/extension` folder

### Firefox
1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `manifest.json` from `/app/extension` folder

## Setup

1. Log in to your Arivu account
2. The extension will automatically detect your deployment URL
3. Click the extension icon to save any webpage
4. Or use keyboard shortcut: `Ctrl+Shift+S` (Windows/Linux) or `Cmd+Shift+S` (Mac)

## Features

- **One-click bookmark saving**: Save any webpage instantly
- **Collection organization**: Choose which collection to save to
- **Keyboard shortcut**: Quick save with Ctrl/Cmd+Shift+S
- **Auto-sync**: Automatically syncs with your Arivu account
- **AI processing**: Generates summaries, highlights, and tags automatically

## Configuration

The extension automatically uses the same URL as your Arivu deployment. No manual configuration needed!

## Troubleshooting

If the extension isn't working:
1. Make sure you're logged in to Arivu in your browser
2. Check that the extension has permission to access the current site
3. Try reloading the extension from the extensions page

## Privacy

The extension only accesses webpage data when you explicitly save a bookmark. Your token is stored securely in the browser's local storage.
