// Get API URL from environment or use the current deployment URL
const API_URL = window.location.hostname.includes('localhost') 
  ? 'http://localhost:8001/api'
  : `${window.location.protocol}//${window.location.hostname}/api`;

let currentTab = null;
let token = null;

async function init() {
  const result = await chrome.storage.local.get(['token', 'apiUrl']);
  token = result.token;
  const apiUrl = result.apiUrl || API_URL;

  if (!token) {
    document.getElementById('loginPrompt').style.display = 'block';
    // Update the link with current hostname
    const loginLink = document.querySelector('.login-link');
    if (loginLink) {
      loginLink.href = `${window.location.protocol}//${window.location.hostname}/auth`;
    }
    return;
  }

  document.getElementById('saveForm').style.display = 'block';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;

  document.getElementById('url').value = tab.url;
  document.getElementById('title').value = tab.title;

  loadCollections(apiUrl);
}

async function loadCollections(apiUrl) {
  try {
    const response = await fetch(`${apiUrl}/collections`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
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

document.getElementById('saveForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const btn = document.getElementById('saveBtn');
  const status = document.getElementById('status');
  
  btn.disabled = true;
  btn.textContent = 'Saving...';
  status.style.display = 'none';

  try {
    const result = await chrome.storage.local.get(['apiUrl']);
    const apiUrl = result.apiUrl || API_URL;
    const url = document.getElementById('url').value;
    const collectionId = document.getElementById('collection').value || null;

    const response = await fetch(`${apiUrl}/bookmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ url, collection_id: collectionId })
    });

    if (response.ok) {
      status.className = 'status success';
      status.textContent = '✓ Saved! AI is processing...';
      status.style.display = 'block';
      
      setTimeout(() => {
        window.close();
      }, 1500);
    } else {
      throw new Error('Failed to save bookmark');
    }
  } catch (error) {
    status.className = 'status error';
    status.textContent = '✗ Failed to save bookmark';
    status.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Bookmark';
  }
});

init();