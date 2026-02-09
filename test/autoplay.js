/*
 * Simple autoplay controller that polls the Python model server for moves
 * and feeds them into the existing GameManager. Toggle the controller by
 * calling `window.autoplay.start()` or `window.autoplay.stop()` in the
 * browser console.
 */
(function () {
  var POLL_INTERVAL_MS = 250;
  var SERVER_URL = (window.AUTOPLAY_SERVER_URL || "http://localhost:5050/predict");

  var directionToIndex = {
    "UP": 0,
    "RIGHT": 1,
    "DOWN": 2,
    "LEFT": 3
  };

  function fetchMove(gameManager) {
    var state = gameManager.captureSimpleState();

    return fetch(SERVER_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        grid: state.grid,
        score: state.score
      })
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Model server returned status " + response.status);
        }
        return response.json();
      })
      .then(function (payload) {
        if (!payload.move) {
          throw new Error("Model server response missing 'move'");
        }
        return payload;
      });
  }

  function AutoplayController(gameManager) {
    this.gameManager = gameManager;
    this.timer = null;
    this.running = false;
  }

  AutoplayController.prototype.start = function () {
    if (this.running) {
      return;
    }
    this.running = true;
    this.scheduleNext();
  };

  AutoplayController.prototype.stop = function () {
    this.running = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  };

  AutoplayController.prototype.scheduleNext = function () {
    var self = this;
    if (!this.running) {
      return;
    }
    this.timer = setTimeout(function () {
      self.step();
    }, POLL_INTERVAL_MS);
  };

  AutoplayController.prototype.step = function () {
    var self = this;
    if (this.gameManager.isGameTerminated()) {
      this.stop();
      return;
    }

    fetchMove(this.gameManager)
      .then(function (result) {
        var moveIndex = directionToIndex[result.move];
        if (typeof moveIndex !== "number") {
          throw new Error("Unknown move returned: " + result.move);
        }

        if (self.gameManager.grid) {
          self.gameManager.move(moveIndex);
        }

        if (result.predicted_invalid) {
          console.warn("Model predicted invalid move, fallback used.", result);
        }
      })
      .catch(function (err) {
        console.error("Autoplay error:", err);
        self.stop();
      })
      .finally(function () {
        self.scheduleNext();
      });
  };

  function initializeAutoplay() {
    if (!window.gameManager) {
      window.requestAnimationFrame(initializeAutoplay);
      return;
    }
    window.autoplay = new AutoplayController(window.gameManager);
  }

  initializeAutoplay();
})();

(function () {
  if (!window.__ENABLE_TEST_HOOKS__) {
    return;
  }

  var busyState = { busy: false };
  var predictEvents = [];

  function ensureActuatorHook() {
    if (!window.HTMLActuator || !window.HTMLActuator.prototype) {
      return false;
    }
    var proto = window.HTMLActuator.prototype;
    if (proto.__testHooked) {
      return true;
    }

    var originalActuate = proto.actuate;
    if (typeof originalActuate !== "function") {
      return false;
    }

    proto.actuate = function () {
      busyState.busy = true;
      return originalActuate.apply(this, arguments);
    };

    proto.__testHooked = true;
    return true;
  }

  function ensureRafHook() {
    if (window.__testHooksPatchedRAF) {
      return true;
    }

    var originalRAF = window.requestAnimationFrame;
    if (typeof originalRAF !== "function") {
      return false;
    }

    var boundRAF = originalRAF.bind(window);
    window.requestAnimationFrame = function (callback) {
      return boundRAF(function (timestamp) {
        try {
          callback(timestamp);
        } finally {
          window.setTimeout(function () {
            busyState.busy = false;
          }, 0);
        }
      });
    };

    window.__testHooksPatchedRAF = true;
    return true;
  }

  function ensureFetchHook() {
    if (window.__testHookedFetch) {
      return true;
    }

    if (typeof window.fetch !== "function") {
      return false;
    }

    var originalFetch = window.fetch.bind(window);
    predictEvents = window.__predictEvents = [];

    window.fetch = function (input, init) {
      var url = "";
      if (typeof input === "string") {
        url = input;
      } else if (input && typeof input.url === "string") {
        url = input.url;
      }

      var isPredict = url.indexOf("/predict") !== -1;
      var result = originalFetch(input, init);

      if (!isPredict) {
        return result;
      }

      return result
        .then(function (response) {
          try {
            var clone = response.clone();
            return clone
              .json()
              .then(function (payload) {
                predictEvents.push({ payload: payload, status: response.status });
                return response;
              })
              .catch(function () {
                predictEvents.push({ payload: null, status: response.status });
                return response;
              });
          } catch (err) {
            predictEvents.push({ payload: null, status: response && response.status });
            return response;
          }
        })
        .catch(function (error) {
          predictEvents.push({ payload: null, status: null, error: error && error.message });
          throw error;
        });
    };

    window.__testHookedFetch = true;
    return true;
  }

  function ensureSnapshot() {
    if (window.__snapshotBoard && window.__snapshotBoard.__testHooked) {
      return true;
    }

    window.__snapshotBoard = function () {
      if (!window.gameManager) {
        return { ready: false, busy: busyState.busy };
      }

      var simple = window.gameManager.captureSimpleState();
      var overlay = document.querySelector(".game-message");
      var gameOver = overlay && overlay.classList.contains("game-over");

      return {
        ready: true,
        busy: !!busyState.busy,
        grid: simple.grid,
        score: simple.score,
        gameOver: !!gameOver
      };
    };

    window.__snapshotBoard.__testHooked = true;
    return true;
  }

  function poll() {
    ensureActuatorHook();
    ensureFetchHook();
    ensureRafHook();
    ensureSnapshot();
    window.requestAnimationFrame(poll);
  }

  poll();
})();
