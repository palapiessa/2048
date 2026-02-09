function GameManager(size, InputManager, Actuator, StorageManager) {
  this.size           = size; // Size of the grid
  this.inputManager   = new InputManager;
  this.storageManager = new StorageManager;
  this.actuator       = new Actuator;

  this.startTiles     = 2;
  this.turn           = 0;
  this.gameEndLogged  = false;

  this.inputManager.on("move", this.move.bind(this));
  this.inputManager.on("restart", this.restart.bind(this));
  this.inputManager.on("keepPlaying", this.keepPlaying.bind(this));

  this.setup();
}

var DIRECTION_NAMES = ["UP", "RIGHT", "DOWN", "LEFT"];

// Restart the game
GameManager.prototype.restart = function () {
  this.storageManager.clearGameState();
  this.actuator.continueGame(); // Clear the game won/lost message
  this.setup();
};

// Keep playing after winning (allows going over 2048)
GameManager.prototype.keepPlaying = function () {
  this.keepPlaying = true;
  this.gameEndLogged = false;
  this.actuator.continueGame(); // Clear the game won/lost message
};

// Return true if the game is lost, or has won and the user hasn't kept playing
GameManager.prototype.isGameTerminated = function () {
  return this.over || (this.won && !this.keepPlaying);
};

// Set up the game
GameManager.prototype.setup = function () {
  var previousState = this.storageManager.getGameState();

  // Reload the game from a previous game if present
  if (previousState) {
    this.grid        = new Grid(previousState.grid.size,
                                previousState.grid.cells); // Reload grid
    this.score       = previousState.score;
    this.over        = previousState.over;
    this.won         = previousState.won;
    this.keepPlaying = previousState.keepPlaying;
    this.turn        = typeof previousState.turn === "number" ? previousState.turn : 0;
    this.gameEndLogged = !!previousState.gameEndLogged;
  } else {
    this.grid        = new Grid(this.size);
    this.score       = 0;
    this.over        = false;
    this.won         = false;
    this.keepPlaying = false;
    this.turn        = 0;
    this.gameEndLogged = false;

    // Add the initial tiles
    this.addStartTiles();
  }

  // Update the actuator
  this.actuate();
};

// Set up the initial tiles to start the game with
GameManager.prototype.addStartTiles = function () {
  for (var i = 0; i < this.startTiles; i++) {
    this.addRandomTile();
  }
};

// Adds a tile in a random position
GameManager.prototype.addRandomTile = function () {
  if (this.grid.cellsAvailable()) {
    var value = Math.random() < 0.9 ? 2 : 4;
    var tile = new Tile(this.grid.randomAvailableCell(), value);

    this.grid.insertTile(tile);
    return tile;
  }

  return null;
};

// Sends the updated grid to the actuator
GameManager.prototype.actuate = function () {
  if (this.storageManager.getBestScore() < this.score) {
    this.storageManager.setBestScore(this.score);
  }

  // Clear the state when the game is over (game over only, not win)
  if (this.over) {
    this.storageManager.clearGameState();
  } else {
    this.storageManager.setGameState(this.serialize());
  }

  this.actuator.actuate(this.grid, {
    score:      this.score,
    over:       this.over,
    won:        this.won,
    bestScore:  this.storageManager.getBestScore(),
    terminated: this.isGameTerminated()
  });

};

// Represent the current game as an object
GameManager.prototype.serialize = function () {
  return {
    grid:        this.grid.serialize(),
    score:       this.score,
    over:        this.over,
    won:         this.won,
    keepPlaying: this.keepPlaying,
    turn:        this.turn,
    gameEndLogged: this.gameEndLogged
  };
};

GameManager.prototype.captureSimpleState = function () {
  var rows = [];

  for (var y = 0; y < this.size; y++) {
    var row = [];

    for (var x = 0; x < this.size; x++) {
      var cell = this.grid.cells[x][y];
      row.push(cell ? cell.value : 0);
    }

    rows.push(row);
  }

  return {
    grid: rows,
    score: this.score
  };
};

// Save all tile positions and remove merger info
GameManager.prototype.prepareTiles = function () {
  this.grid.eachCell(function (x, y, tile) {
    if (tile) {
      tile.mergedFrom = null;
      tile.savePosition();
    }
  });
};

// Move a tile and its representation
GameManager.prototype.moveTile = function (tile, cell) {
  var from = { x: tile.x, y: tile.y };

  this.grid.cells[tile.x][tile.y] = null;
  this.grid.cells[cell.x][cell.y] = tile;
  tile.updatePosition(cell);

  if (typeof logEvent === "function") {
    logEvent({
      type: "moveTile",
      turn: this.turn,
      value: tile.value,
      from: from,
      to: { x: cell.x, y: cell.y }
    });
  }
};

// Move tiles on the grid in the specified direction
GameManager.prototype.move = function (direction) {
  // 0: up, 1: right, 2: down, 3: left
  var self = this;

  if (this.isGameTerminated()) return; // Don't do anything if the game's over

  this.turn += 1;
  var turnIndex = this.turn;

  // Artificial regression: declare the game over after 10 moves regardless of board state
  if (this.turn >= 10 && !this.over) {
    this.over = true;
    // Immediately pop the game-over overlay so it is visible during the failure
    if (this.actuator && typeof this.actuator.message === "function") {
      this.actuator.message(false);
    }
    this.actuate();
    if (typeof logEvent === "function") {
      logEvent({
        type: "forcedGameOver",
        turn: turnIndex,
        reason: "artificial_bug"
      });
    }
    return;
  }

  var prevState = this.captureSimpleState();
  var mergeEvents = [];
  var spawnedTile = null;
  var directionName = DIRECTION_NAMES[direction] || direction;

  var cell, tile;

  var vector     = this.getVector(direction);
  var traversals = this.buildTraversals(vector);
  var moved      = false;

  // Save the current tile positions and remove merger information
  this.prepareTiles();

  // Traverse the grid in the right direction and move tiles
  traversals.x.forEach(function (x) {
    traversals.y.forEach(function (y) {
      cell = { x: x, y: y };
      tile = self.grid.cellContent(cell);

      if (tile) {
        var positions = self.findFarthestPosition(cell, vector);
        var next      = self.grid.cellContent(positions.next);

        // Only one merger per row traversal?
        if (next && next.value === tile.value && !next.mergedFrom) {
          var mergeFromRow = tile.y;
          var mergeFromCol = tile.x;
          var mergeIntoRow = positions.next.y;
          var mergeIntoCol = positions.next.x;
          var merged = new Tile(positions.next, tile.value * 2);
          merged.mergedFrom = [tile, next];

          self.grid.insertTile(merged);
          self.grid.removeTile(tile);

          // Converge the two tiles' positions
          tile.updatePosition(positions.next);

          mergeEvents.push({
            from: [mergeFromRow, mergeFromCol],
            into: [mergeIntoRow, mergeIntoCol],
            value: tile.value,
            result: merged.value
          });

          // Update the score
          self.score += merged.value;

          // The mighty 2048 tile
          if (merged.value === 2048) self.won = true;
        } else {
          self.moveTile(tile, positions.farthest);
        }

        if (!self.positionsEqual(cell, tile)) {
          moved = true; // The tile moved from its original cell!
        }
      }
    });
  });

  if (moved) {
    spawnedTile = this.addRandomTile();

    if (!this.movesAvailable()) {
      this.over = true; // Game over!
    }

    this.actuate();
  }

  if (typeof logEvent === "function") {
    var nextState = this.captureSimpleState();

    logEvent({
      type: "move",
      turn: turnIndex,
      direction: directionName,
      prev: prevState,
      next: nextState,
      merges: mergeEvents,
      spawnedTile: spawnedTile ? { row: spawnedTile.y, col: spawnedTile.x, value: spawnedTile.value } : null,
      valid: moved
    });

    if (!this.gameEndLogged && this.isGameTerminated()) {
      this.gameEndLogged = true;
      logEvent({
        type: "gameEnd",
        turn: turnIndex,
        reason: this.over ? "loss" : "win",
        score: this.score,
        highestTile: this.getHighestTileValue(),
        state: nextState,
        over: this.over,
        won: this.won,
        keepPlaying: this.keepPlaying
      });
    }
  }
};

GameManager.prototype.getVector = function (direction) {
  // Vectors representing tile movement
  var map = {
    0: { x: 0,  y: -1 }, // Up
    1: { x: 1,  y: 0 },  // Right
    2: { x: 0,  y: 1 },  // Down
    3: { x: -1, y: 0 }   // Left

  };

  return map[direction];
};

// Build a list of positions to traverse in the right order
GameManager.prototype.buildTraversals = function (vector) {
  var traversals = { x: [], y: [] };

  for (var pos = 0; pos < this.size; pos++) {
    traversals.x.push(pos);
    traversals.y.push(pos);
  }

  // Always traverse from the farthest cell in the chosen direction
  if (vector.x === 1) traversals.x = traversals.x.reverse();
  if (vector.y === 1) traversals.y = traversals.y.reverse();

  return traversals;
};

GameManager.prototype.findFarthestPosition = function (cell, vector) {
  var previous;

  // Progress towards the vector direction until an obstacle is found
  do {
    previous = cell;
    cell     = { x: previous.x + vector.x, y: previous.y + vector.y };
  } while (this.grid.withinBounds(cell) &&
           this.grid.cellAvailable(cell));

  return {
    farthest: previous,
    next: cell // Used to check if a merge is required
  };
};

GameManager.prototype.movesAvailable = function () {
  return this.grid.cellsAvailable() || this.tileMatchesAvailable();
};

// Check for available matches between tiles (more expensive check)
GameManager.prototype.tileMatchesAvailable = function () {
  var self = this;

  var tile;

  for (var x = 0; x < this.size; x++) {
    for (var y = 0; y < this.size; y++) {
      tile = this.grid.cellContent({ x: x, y: y });

      if (tile) {
        for (var direction = 0; direction < 4; direction++) {
          var vector = self.getVector(direction);
          var cell   = { x: x + vector.x, y: y + vector.y };

          var other  = self.grid.cellContent(cell);

          if (other && other.value === tile.value) {
            return true; // These two tiles can be merged
          }
        }
      }
    }
  }

  return false;
};

GameManager.prototype.getHighestTileValue = function () {
  var max = 0;

  this.grid.eachCell(function (x, y, tile) {
    if (tile && tile.value > max) {
      max = tile.value;
    }
  });

  return max;
};

GameManager.prototype.positionsEqual = function (first, second) {
  return first.x === second.x && first.y === second.y;
};
