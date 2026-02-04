# Training a model to play a game 
- source for the the game forked of https://github.com/gabrielecirulli/2048
- experiment how to train AI to play the game
- read more from my blog: https://palapiessa.github.io/testing-with-ai-blog/

## License
2048 is licensed under the [MIT license](https://github.com/gabrielecirulli/2048/blob/master/LICENSE.txt).

## Setup

### 1. Clone the repo
- Clone this game repo (`2048`). Keep them side-by-side so the relative paths referenced in blog posts continue to work.

### 2. Prepare the Python tooling with `uv`
- From the `2048` repo root create a virtual environment and install the shared dependencies for both the training script and the Flask service:
  ```bash
  cd 2048
  uv venv
  source .venv/bin/activate
  uv pip install numpy scikit-learn flask flask-cors
  uv pip install stable-baselines3
  ```
### 3. Open the 2048 game
- Open `2048/index.html` directly in your browser (double-click the file or drag it into the browser window). Because the project is a pure JS application, no extra server is required unless you prefer one.

### 4. How to train the model
- play the game < 10 times
  - load index.html with Chrome browser
- store logs in training_data-folder
- train the model:
  -  python3 train_offline.py
  -  random_forest_2048.pkl 

The script trains a RandomForestClassifier on the collected 2048 move logs, then pickles the fitted model so it can be reloaded later without retraining.

#### Visualize model
- install matplot
  - uv pip install matplotlib
- ./visualize/load_2048_pkl.py
- 
### 5. Watch the model play

- Start the Flask service (still from the repo root):
  ```bash
  RF_ALLOWED_ORIGINS=http://127.0.0.1:5500 PORT=5050 python service/model_server.py
  ```
  When loading the game from the local file system most browsers send a `null` origin; keeping `RF_ALLOWED_ORIGINS` set to `*` (the default) allows that. If you host the game on a specific origin, tighten the value accordingly.

- With the Flask service running and the game page open, launch the browser console and run `autoplay.start()`. The autoplay script will send board states to the Flask service, get back moves, and drive the game automatically.

### 6. More Info

Background and detailed info to the code base:
https://palapiessa.github.io/testing-with-ai-blog/