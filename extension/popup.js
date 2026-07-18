/**
 * FactLens — Popup Script
 * Manages extension settings and displays session stats.
 */

document.addEventListener('DOMContentLoaded', () => {
  const backendUrlInput = document.getElementById('backend-url');
  const railwayUrlInput = document.getElementById('railway-url');
  const toggleEnabled  = document.getElementById('toggle-enabled');
  const saveBtn        = document.getElementById('save-btn');
  const statusDot      = document.getElementById('status-dot');
  const statusText     = document.getElementById('status-text');
  const statClaims     = document.getElementById('stat-claims');
  const statSession    = document.getElementById('stat-session');
  const btnLocal       = document.getElementById('btn-local');
  const btnProd        = document.getElementById('btn-prod');

  const LOCAL_URL = 'ws://localhost:8000/ws/factcheck';

  // ── Load current settings ──────────────────────────────────
  chrome.storage.local.get(
    ['backendUrl', 'railwayUrl', 'enabled', 'sessionId'],
    (settings) => {
      const currentUrl = settings.backendUrl || LOCAL_URL;
      backendUrlInput.value = currentUrl;

      if (settings.railwayUrl) {
        railwayUrlInput.value = settings.railwayUrl;
      }

      toggleEnabled.checked =
        settings.enabled !== undefined ? settings.enabled : true;

      if (settings.sessionId) {
        statSession.textContent = settings.sessionId;
      }

      // Mark active button
      if (currentUrl === LOCAL_URL) {
        setActiveBtn('local');
      } else {
        setActiveBtn('prod');
        railwayUrlInput.style.display = 'block';
        railwayUrlInput.value = currentUrl;
      }
    }
  );

  // ── Quick URL toggle helpers ───────────────────────────────
  function setActiveBtn(which) {
    btnLocal.classList.toggle('active', which === 'local');
    btnProd.classList.toggle('active', which === 'prod');
  }

  btnLocal.addEventListener('click', () => {
    backendUrlInput.value = LOCAL_URL;
    railwayUrlInput.style.display = 'none';
    setActiveBtn('local');
  });

  btnProd.addEventListener('click', () => {
    // Show the Railway URL input field for editing
    railwayUrlInput.style.display = 'block';
    railwayUrlInput.focus();
    if (railwayUrlInput.value) {
      backendUrlInput.value = railwayUrlInput.value;
    }
    setActiveBtn('prod');
  });

  railwayUrlInput.addEventListener('input', () => {
    if (railwayUrlInput.value.trim()) {
      backendUrlInput.value = railwayUrlInput.value.trim();
    }
  });

  // ── Check backend health ──────────────────────────────────
  async function checkHealth() {
    const wsUrl = backendUrlInput.value || LOCAL_URL;
    const httpUrl = wsUrl
      .replace('ws://', 'http://')
      .replace('wss://', 'https://')
      .replace('/ws/factcheck', '/health');

    try {
      const response = await fetch(httpUrl, { method: 'GET' });
      const data = await response.json();

      if (data.status === 'healthy') {
        statusDot.classList.add('connected');
        statusText.textContent = '✓ Backend connected';

        if (data.active_sessions > 0) {
          statClaims.textContent = data.active_sessions;
        }
      } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Backend unhealthy';
      }
    } catch (e) {
      statusDot.classList.remove('connected');
      statusText.textContent = 'Backend not reachable';
    }
  }

  checkHealth();

  // ── Save settings ─────────────────────────────────────────
  saveBtn.addEventListener('click', () => {
    const settings = {
      backendUrl: backendUrlInput.value.trim(),
      railwayUrl: railwayUrlInput.value.trim(),
      enabled: toggleEnabled.checked,
    };

    chrome.runtime.sendMessage(
      { type: 'UPDATE_SETTINGS', settings },
      (response) => {
        if (response && response.success) {
          saveBtn.textContent = '✓ Saved!';
          saveBtn.classList.add('saved');
          setTimeout(() => {
            saveBtn.textContent = 'Save Settings';
            saveBtn.classList.remove('saved');
          }, 2000);
        }
      }
    );

    // Also save directly to storage
    chrome.storage.local.set(settings);

    // Re-check health with new URL
    setTimeout(checkHealth, 500);
  });

  // ── Toggle handler ────────────────────────────────────────
  toggleEnabled.addEventListener('change', () => {
    chrome.storage.local.set({ enabled: toggleEnabled.checked });
  });
});
