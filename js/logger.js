(function () {
  "use strict";

  var store = window._gameLogs || [];
  var listeners = [];
  window._gameLogs = store;

  function notify(entry) {
    listeners.slice().forEach(function (listener) {
      try {
        listener(entry, store);
      } catch (err) {
        if (window && window.console && typeof window.console.error === "function") {
          console.error("log listener failed", err);
        }
      }
    });
  }

  function logEvent(evt) {
    var entry = Object.assign({ ts: Date.now() }, evt);
    store.push(entry);
    notify(entry);
  }

  function getGameLogs() {
    return store.slice();
  }

  function clearGameLogs() {
    store.length = 0;
    notify(null);
    return store;
  }

  function exportGameLogs() {
    return JSON.stringify(store, null, 2);
  }

  function addGameLogListener(listener) {
    if (typeof listener !== "function") {
      return function () {};
    }
    listeners.push(listener);
    return function () {
      removeGameLogListener(listener);
    };
  }

  function removeGameLogListener(listener) {
    var idx = listeners.indexOf(listener);
    if (idx !== -1) {
      listeners.splice(idx, 1);
    }
  }

  window.logEvent = logEvent;
  window.getGameLogs = getGameLogs;
  window.clearGameLogs = clearGameLogs;
  window.exportGameLogs = exportGameLogs;
  window.addGameLogListener = addGameLogListener;
  window.removeGameLogListener = removeGameLogListener;
})();