(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function formatLogs(logs) {
    return logs.length ? JSON.stringify(logs, null, 2) : "No logs captured yet.";
  }

  function downloadLogs(logs) {
    if (!logs.length) {
      return;
    }

    var blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "2048-logs.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function initPanel(panel) {
    var output = panel.querySelector("[data-log-output]");
    var refreshBtn = panel.querySelector("[data-log-action=refresh]");
    var exportBtn = panel.querySelector("[data-log-action=export]");
    var clearBtn = panel.querySelector("[data-log-action=clear]");
    var status = panel.querySelector("[data-log-status]");

    function currentLogs() {
      if (typeof window.getGameLogs === "function") {
        return window.getGameLogs();
      }
      return (window._gameLogs || []).slice();
    }

    function render() {
      var logs = currentLogs();
      if (output) {
        output.textContent = formatLogs(logs);
      }
      if (status) {
        status.textContent = logs.length ? logs.length + " event(s)" : "Empty";
      }
      return logs;
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        render();
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        if (typeof window.clearGameLogs === "function") {
          window.clearGameLogs();
        } else {
          window._gameLogs = [];
        }
        render();
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        downloadLogs(render());
      });
    }

    render();

    if (typeof window.addGameLogListener === "function") {
      window.addGameLogListener(render);
    }
  }

  ready(function () {
    var panel = document.querySelector("[data-log-panel]");
    if (!panel) {
      return;
    }
    initPanel(panel);
  });
})();
