// Wait till the browser is ready to render the game (avoids glitches)
window.requestAnimationFrame(function () {
  // Expose the game manager globally so helper scripts (e.g., autoplay)
  // can orchestrate moves programmatically.
  window.gameManager = new GameManager(4, KeyboardInputManager, HTMLActuator, LocalStorageManager);
});
