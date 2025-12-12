// preview-site-logger.js
(function() {
  const parentOrigin = '*';

  function sendToParent(type, data, severity = 'info') {
    window.parent.postMessage({
      source: 'preview-logger',
      type: type,
      category: getCategoryFromType(type),
      severity: severity,
      data: data,
      timestamp: new Date().toISOString()
    }, parentOrigin);
  }

  function getCategoryFromType(type) {
    const categoryMap = {
      'buildError': 'build',
      'runtimeError': 'runtime',
      'promiseRejection': 'runtime',
      'resourceError': 'resource',
      'networkError': 'network',
      'console': 'console'
    };
    return categoryMap[type] || 'other';
  }

  // Intercept console methods
  const originalConsole = {
    log: console.log,
    error: console.error,
    warn: console.warn,
    info: console.info,
    debug: console.debug
  };

  ['log', 'error', 'warn', 'info', 'debug'].forEach(method => {
    console[method] = function(...args) {
      originalConsole[method].apply(console, args);

      const severity = method === 'error' ? 'error' : method === 'warn' ? 'warning' : 'info';

      sendToParent('console', {
        level: method,
        message: args.map(arg => {
          try {
            return typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg);
          } catch (e) {
            return String(arg);
          }
        })
      }, severity);
    };
  });

  // Enhanced build error detection with detailed extraction
  function detectBuildError() {
    let errorDetails = null;

    // 1. Vite Error Overlay (most detailed)
    const viteOverlay = document.querySelector('vite-error-overlay');
    if (viteOverlay && viteOverlay.shadowRoot) {
      const shadowRoot = viteOverlay.shadowRoot;

      // Extract error message
      const messageEl = shadowRoot.querySelector('.message-body') ||
                       shadowRoot.querySelector('.message') ||
                       shadowRoot.querySelector('pre');

      // Extract stack trace
      const stackEl = shadowRoot.querySelector('.stack') ||
                     shadowRoot.querySelector('.file');

      // Extract file info
      const fileEl = shadowRoot.querySelector('.file');

      if (messageEl) {
        errorDetails = {
          message: messageEl.textContent.trim(),
          stack: stackEl ? stackEl.textContent.trim() : '',
          file: fileEl ? fileEl.textContent.trim() : '',
          tool: 'Vite',
          rawHTML: shadowRoot.innerHTML.substring(0, 5000) // Capture full error for debugging
        };
      }
    }

    // 2. Webpack Error Overlay
    if (!errorDetails) {
      const webpackOverlay = document.querySelector('iframe[id*="webpack"]') ||
                            document.querySelector('[data-reactroot]'); // React error overlay

      if (webpackOverlay) {
        try {
          let errorText = '';

          // Try to access iframe content
          if (webpackOverlay.tagName === 'IFRAME') {
            const iframeDoc = webpackOverlay.contentDocument || webpackOverlay.contentWindow?.document;
            if (iframeDoc) {
              errorText = iframeDoc.body.textContent;
            }
          } else {
            errorText = webpackOverlay.textContent;
          }

          if (errorText) {
            errorDetails = {
              message: errorText.substring(0, 1000),
              tool: 'Webpack',
              rawText: errorText.substring(0, 5000)
            };
          }
        } catch (e) {
          errorDetails = {
            message: 'Webpack build error detected (unable to extract details due to iframe restrictions)',
            tool: 'Webpack',
            error: e.message
          };
        }
      }
    }

    // 3. Check for error text in body (Next.js, Create React App, etc.)
    if (!errorDetails) {
      const bodyText = document.body?.textContent || '';
      const bodyHTML = document.body?.innerHTML || '';

      const errorIndicators = [
        'Failed to compile',
        'Compilation failed',
        'Build failed',
        'Module not found',
        'Cannot find module',
        'Syntax error',
        'Module parse failed',
        'You may need an appropriate loader',
        'ERROR in',
        'Module build failed'
      ];

      const hasError = errorIndicators.some(indicator =>
        bodyText.includes(indicator) || bodyHTML.includes(indicator)
      );

      if (hasError) {
        // Extract the error block
        const pre = document.querySelector('pre');
        const errorDiv = document.querySelector('[class*="error"]') ||
                        document.querySelector('[id*="error"]');

        let errorMessage = '';
        if (pre) {
          errorMessage = pre.textContent;
        } else if (errorDiv) {
          errorMessage = errorDiv.textContent;
        } else {
          // Try to extract error context from body text
          const lines = bodyText.split('\n');
          const errorLineIndex = lines.findIndex(line =>
            errorIndicators.some(indicator => line.includes(indicator))
          );

          if (errorLineIndex !== -1) {
            // Get surrounding lines for context
            errorMessage = lines.slice(
              Math.max(0, errorLineIndex - 2),
              Math.min(lines.length, errorLineIndex + 15)
            ).join('\n');
          }
        }

        errorDetails = {
          message: errorMessage.trim().substring(0, 2000),
          tool: 'Build Tool',
          fullBody: bodyText.substring(0, 3000)
        };
      }
    }

    // 4. Check for React error boundary
    const reactError = document.querySelector('[data-test-id="error-boundary"]') ||
                      document.querySelector('.react-error-overlay');

    if (!errorDetails && reactError) {
      errorDetails = {
        message: reactError.textContent.trim(),
        tool: 'React',
        stack: reactError.querySelector('.stack-trace')?.textContent || ''
      };
    }

    // Send the error if found
    if (errorDetails) {
      sendToParent('buildError', errorDetails, 'critical');
      return true;
    }

    return false;
  }

  // Capture runtime errors with full details
  window.addEventListener('error', (event) => {
    if (event.target !== window) return;

    sendToParent('runtimeError', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || '',
      errorType: event.error?.name || 'Error',
      errorObject: event.error ? {
        name: event.error.name,
        message: event.error.message,
        stack: event.error.stack
      } : null
    }, 'error');
  });

  // Capture unhandled promise rejections with details
  window.addEventListener('unhandledrejection', (event) => {
    let reason = event.reason;
    let reasonDetails = {};

    if (reason instanceof Error) {
      reasonDetails = {
        name: reason.name,
        message: reason.message,
        stack: reason.stack
      };
    } else if (typeof reason === 'object') {
      try {
        reasonDetails = JSON.parse(JSON.stringify(reason));
      } catch (e) {
        reasonDetails = { toString: String(reason) };
      }
    } else {
      reasonDetails = { value: String(reason) };
    }

    sendToParent('promiseRejection', {
      reason: String(reason),
      reasonDetails: reasonDetails,
      stack: reason?.stack || '',
      promise: String(event.promise)
    }, 'error');
  });

  // Capture resource loading errors
  window.addEventListener('error', (event) => {
    if (event.target !== window) {
      const tagName = event.target.tagName;
      const severity = (tagName === 'SCRIPT' || tagName === 'LINK') ? 'error' : 'warning';

      sendToParent('resourceError', {
        tagName: tagName,
        src: event.target.src || event.target.href,
        type: 'Resource failed to load',
        outerHTML: event.target.outerHTML
      }, severity);
    }
  }, true);

  // Enhanced network error monitoring
  const originalFetch = window.fetch;
  window.fetch = function(...args) {
    const url = args[0];
    const startTime = Date.now();

    return originalFetch.apply(this, args)
      .then(response => {
        if (!response.ok) {
          return response.text().then(body => {
            sendToParent('networkError', {
              url: url,
              status: response.status,
              statusText: response.statusText,
              responseBody: body.substring(0, 1000),
              headers: Object.fromEntries(response.headers.entries()),
              duration: Date.now() - startTime,
              type: 'API Error'
            }, 'error');

            // Return original response
            return response;
          }).catch(() => response); // If can't read body, return response as-is
        }
        return response;
      })
      .catch(error => {
        sendToParent('networkError', {
          url: url,
          message: error.message,
          stack: error.stack,
          type: 'Network Error',
          duration: Date.now() - startTime
        }, 'error');
        throw error;
      });
  };

  // Monitor XHR requests
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url) {
    this._url = url;
    this._method = method;
    return originalXHROpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function() {
    this.addEventListener('error', function() {
      sendToParent('networkError', {
        url: this._url,
        method: this._method,
        type: 'XHR Error',
        message: 'Request failed'
      }, 'error');
    });

    this.addEventListener('load', function() {
      if (this.status >= 400) {
        sendToParent('networkError', {
          url: this._url,
          method: this._method,
          status: this.status,
          statusText: this.statusText,
          responseText: this.responseText?.substring(0, 1000),
          type: 'XHR Error'
        }, 'error');
      }
    });

    return originalXHRSend.apply(this, arguments);
  };

  // Check for build errors on load
  window.addEventListener('load', () => {
    setTimeout(() => {
      const hasError = detectBuildError();
      if (!hasError) {
        sendToParent('ready', {
          url: window.location.href,
          userAgent: navigator.userAgent,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          }
        }, 'info');
      }
    }, 100);
  });

  // Periodically check for build errors (for HMR)
  let lastErrorCheck = '';
  setInterval(() => {
    const currentBodyText = document.body?.textContent || '';
    // Only check if body content changed
    if (currentBodyText !== lastErrorCheck) {
      detectBuildError();
      lastErrorCheck = currentBodyText;
    }
  }, 2000);

  // Initial check
  setTimeout(detectBuildError, 100);
})();
