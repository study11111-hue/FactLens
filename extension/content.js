/**
 * FactLens — Content Script
 * Captures Google Meet captions via MutationObserver,
 * sends to backend via WebSocket, and renders fact-check
 * verdicts in a floating overlay panel.
 */

(function () {
  'use strict';

  // ── State ────────────────────────────────────────────────
  let ws = null;
  let isEnabled = true;
  let backendUrl = 'ws://localhost:8000/ws/factcheck';
  let sessionId = null;
  let captionBuffer = '';
  let captionTimer = null;
  let reconnectTimer = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 10;
  const RECONNECT_DELAY = 3000;
  const CAPTION_DEBOUNCE = 3000;
  let verdictHistory = [];
  let panelMinimized = false;

  // ── Initialize ───────────────────────────────────────────

  async function init() {
    console.log('🔍 FactLens content script loaded');

    // Load settings
    try {
      const settings = await getSettings();
      backendUrl = settings.backendUrl || backendUrl;
      isEnabled = settings.enabled !== undefined ? settings.enabled : true;
    } catch (e) {
      console.log('FactLens: Using default settings');
    }

    if (!isEnabled) {
      console.log('FactLens: Disabled by user');
      return;
    }

    // Create the overlay panel
    createOverlayPanel();

    // Connect to backend
    connectWebSocket();

    // Start observing captions
    waitForCaptions();
  }

  function getSettings() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }, (response) => {
        resolve(response || {});
      });
    });
  }

  // ── WebSocket Connection ─────────────────────────────────

  function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    try {
      ws = new WebSocket(backendUrl);

      ws.onopen = () => {
        console.log('🔌 FactLens: Connected to backend');
        reconnectAttempts = 0;
        updateConnectionStatus(true);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleServerMessage(message);
        } catch (e) {
          console.error('FactLens: Error parsing message', e);
        }
      };

      ws.onclose = () => {
        console.log('🔌 FactLens: Disconnected');
        updateConnectionStatus(false);
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('FactLens: WebSocket error', error);
        updateConnectionStatus(false);
      };
    } catch (e) {
      console.error('FactLens: Failed to connect', e);
      updateConnectionStatus(false);
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.log('FactLens: Max reconnect attempts reached');
      return;
    }
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
      reconnectAttempts++;
      console.log(
        `FactLens: Reconnecting (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
      );
      connectWebSocket();
    }, RECONNECT_DELAY);
  }

  function sendToBackend(text, speaker) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(
      JSON.stringify({
        type: 'transcript',
        text: text,
        speaker: speaker,
        session_id: sessionId || 'default',
      })
    );
  }

  // ── Caption Observation ──────────────────────────────────

  function waitForCaptions() {
    // Google Meet renders captions in a container.
    // We poll for it since it appears dynamically when captions are turned on.
    const checkInterval = setInterval(() => {
      const captionContainer = findCaptionContainer();
      if (captionContainer) {
        clearInterval(checkInterval);
        observeCaptions(captionContainer);
        console.log('🎙️ FactLens: Caption container found, observing...');
        addStatusMessage('Caption detection active — listening for claims');
      }
    }, 2000);

    // Also observe for the container appearing later
    const bodyObserver = new MutationObserver(() => {
      const container = findCaptionContainer();
      if (container) {
        bodyObserver.disconnect();
        clearInterval(checkInterval);
        observeCaptions(container);
        console.log('🎙️ FactLens: Caption container detected via observer');
        addStatusMessage('Caption detection active — listening for claims');
      }
    });

    bodyObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  function findCaptionContainer() {
    // Try multiple selectors for resilience
    const selectors = [
      '[aria-label="Captions"]',
      '[aria-label="captions"]',
      'div[jscontroller][data-is-persistent-cc]',
      '.a4cQT', // Google Meet caption class (may change)
      '[role="region"][aria-live]',
    ];

    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) return el;
    }

    return null;
  }

  function observeCaptions(container) {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'childList' || mutation.type === 'characterData') {
          processCaptionUpdate(container);
        }
      }
    });

    observer.observe(container, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  function processCaptionUpdate(container) {
    // Extract text and speaker from the caption container
    const captionElements = container.querySelectorAll(
      'span, div[class]'
    );
    let currentText = '';
    let currentSpeaker = 'Unknown';

    // Try to find speaker name and caption text
    const allText = container.innerText.trim();
    if (!allText) return;

    // Google Meet typically shows "Speaker Name\nCaption text"
    const lines = allText.split('\n').filter((l) => l.trim());
    if (lines.length >= 2) {
      currentSpeaker = lines[0].trim();
      currentText = lines.slice(1).join(' ').trim();
    } else if (lines.length === 1) {
      currentText = lines[0].trim();
    }

    if (!currentText) return;

    // Buffer captions and debounce
    captionBuffer = currentText;

    clearTimeout(captionTimer);
    captionTimer = setTimeout(() => {
      if (captionBuffer.length >= 10) {
        sendToBackend(captionBuffer, currentSpeaker);
        captionBuffer = '';
      }
    }, CAPTION_DEBOUNCE);
  }

  // ── Server Message Handler ───────────────────────────────

  function handleServerMessage(message) {
    switch (message.type) {
      case 'status':
        if (message.data.session_id) {
          sessionId = message.data.session_id;
        }
        if (message.data.processing) {
          showProcessingIndicator();
        } else {
          hideProcessingIndicator();
        }
        if (message.data.message) {
          addStatusMessage(message.data.message);
        }
        break;

      case 'verdict':
        hideProcessingIndicator();
        if (message.data.verdicts) {
          message.data.verdicts.forEach((v) => addVerdict(v));
        }
        break;

      case 'error':
        hideProcessingIndicator();
        addStatusMessage(`Error: ${message.data.message}`, true);
        break;

      case 'pong':
        break;
    }
  }

  // ── Overlay Panel UI ─────────────────────────────────────

  function createOverlayPanel() {
    // Remove existing panel if any
    const existing = document.getElementById('factlens-panel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'factlens-panel';
    panel.innerHTML = `
      <div class="factlens-header" id="factlens-header">
        <div class="factlens-logo">
          <span class="factlens-icon">🔍</span>
          <span class="factlens-title">FactLens</span>
          <span class="factlens-badge" id="factlens-connection-badge">●</span>
        </div>
        <div class="factlens-controls">
          <span class="factlens-counter" id="factlens-counter">0 claims</span>
          <button class="factlens-btn" id="factlens-minimize" title="Minimize">─</button>
          <button class="factlens-btn" id="factlens-close" title="Close">✕</button>
        </div>
      </div>
      <div class="factlens-body" id="factlens-body">
        <div class="factlens-processing" id="factlens-processing" style="display:none">
          <div class="factlens-spinner"></div>
          <span>Analyzing claims...</span>
        </div>
        <div class="factlens-verdicts" id="factlens-verdicts">
          <div class="factlens-empty" id="factlens-empty">
            <span class="factlens-empty-icon">🎙️</span>
            <p>Waiting for captions...</p>
            <p class="factlens-hint">Enable captions in Google Meet to start fact-checking</p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(panel);

    // Make panel draggable
    makeDraggable(panel, document.getElementById('factlens-header'));

    // Minimize button
    document.getElementById('factlens-minimize').addEventListener('click', () => {
      panelMinimized = !panelMinimized;
      const body = document.getElementById('factlens-body');
      body.style.display = panelMinimized ? 'none' : 'block';
      document.getElementById('factlens-minimize').textContent = panelMinimized
        ? '□'
        : '─';
    });

    // Close button
    document.getElementById('factlens-close').addEventListener('click', () => {
      panel.style.display = 'none';
    });
  }

  function makeDraggable(panel, handle) {
    let isDragging = false;
    let startX, startY, startLeft, startTop;

    handle.addEventListener('mousedown', (e) => {
      if (e.target.classList.contains('factlens-btn')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      startLeft = panel.offsetLeft;
      startTop = panel.offsetTop;
      handle.style.cursor = 'grabbing';
      e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      panel.style.left = `${startLeft + dx}px`;
      panel.style.top = `${startTop + dy}px`;
      panel.style.right = 'auto';
    });

    document.addEventListener('mouseup', () => {
      isDragging = false;
      handle.style.cursor = 'grab';
    });
  }

  function updateConnectionStatus(connected) {
    const badge = document.getElementById('factlens-connection-badge');
    if (!badge) return;
    badge.style.color = connected ? '#4ade80' : '#f87171';
    badge.title = connected ? 'Connected' : 'Disconnected';
  }

  function showProcessingIndicator() {
    const el = document.getElementById('factlens-processing');
    if (el) el.style.display = 'flex';
  }

  function hideProcessingIndicator() {
    const el = document.getElementById('factlens-processing');
    if (el) el.style.display = 'none';
  }

  function addStatusMessage(text, isError = false) {
    const empty = document.getElementById('factlens-empty');
    if (empty) empty.style.display = 'none';

    const container = document.getElementById('factlens-verdicts');
    if (!container) return;

    const msg = document.createElement('div');
    msg.className = `factlens-status-msg ${isError ? 'factlens-error' : ''}`;
    msg.textContent = text;

    container.insertBefore(msg, container.firstChild);

    // Remove after 5 seconds
    setTimeout(() => {
      msg.style.opacity = '0';
      setTimeout(() => msg.remove(), 300);
    }, 5000);
  }

  function addVerdict(verdict) {
    const empty = document.getElementById('factlens-empty');
    if (empty) empty.style.display = 'none';

    const container = document.getElementById('factlens-verdicts');
    if (!container) return;

    verdictHistory.unshift(verdict);
    updateCounter();

    const card = document.createElement('div');
    card.className = 'factlens-verdict-card factlens-slide-in';

    const verdictClass = getVerdictClass(verdict.verdict);
    const verdictEmoji = getVerdictEmoji(verdict.verdict);
    const confidencePercent = Math.round((verdict.confidence || 0) * 100);

    card.innerHTML = `
      <div class="factlens-verdict-header">
        <span class="factlens-verdict-badge ${verdictClass}">
          ${verdictEmoji} ${verdict.verdict}
        </span>
        <span class="factlens-confidence">${confidencePercent}%</span>
      </div>
      <div class="factlens-claim-text">"${escapeHtml(verdict.claim_text)}"</div>
      ${verdict.speaker && verdict.speaker !== 'Unknown' ? `<div class="factlens-speaker">— ${escapeHtml(verdict.speaker)}</div>` : ''}
      <div class="factlens-explanation">${escapeHtml(verdict.explanation || '')}</div>
      ${
        verdict.sources && verdict.sources.length > 0
          ? `<div class="factlens-sources">
              <span class="factlens-sources-label">Sources:</span>
              ${verdict.sources
                .map(
                  (url) =>
                    `<a href="${escapeHtml(url)}" target="_blank" class="factlens-source-link" title="${escapeHtml(url)}">${getDomain(url)}</a>`
                )
                .join('')}
            </div>`
          : ''
      }
      <div class="factlens-confidence-bar">
        <div class="factlens-confidence-fill ${verdictClass}" style="width: ${confidencePercent}%"></div>
      </div>
    `;

    container.insertBefore(card, container.firstChild);

    // Trigger animation
    requestAnimationFrame(() => {
      card.classList.add('factlens-visible');
    });
  }

  function updateCounter() {
    const counter = document.getElementById('factlens-counter');
    if (counter) {
      counter.textContent = `${verdictHistory.length} claim${verdictHistory.length !== 1 ? 's' : ''}`;
    }
  }

  function getVerdictClass(verdict) {
    switch (verdict) {
      case 'TRUE':
        return 'factlens-true';
      case 'FALSE':
        return 'factlens-false';
      case 'MISLEADING':
        return 'factlens-misleading';
      default:
        return 'factlens-unverified';
    }
  }

  function getVerdictEmoji(verdict) {
    switch (verdict) {
      case 'TRUE':
        return '✅';
      case 'FALSE':
        return '❌';
      case 'MISLEADING':
        return '⚠️';
      default:
        return '❓';
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getDomain(url) {
    try {
      return new URL(url).hostname.replace('www.', '');
    } catch {
      return url.substring(0, 30);
    }
  }

  // ── Keepalive ────────────────────────────────────────────

  setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 30000);

  // ── Start ────────────────────────────────────────────────

  // Wait for page to be fully loaded
  if (document.readyState === 'complete') {
    init();
  } else {
    window.addEventListener('load', init);
  }
})();
