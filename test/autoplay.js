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
