# Training a model to play a game 
- source for the the game forked of https://github.com/gabrielecirulli/2048
- experiment how to train AI to play the game
- read more from my blog: https://palapiessa.github.io/testing-with-ai-blog/

## License
2048 is licensed under the [MIT license](https://github.com/gabrielecirulli/2048/blob/master/LICENSE.txt).

## Install instructions
- install uv
- install venv:
  - uv venv
  - source .venv/bin/activate
  - uv pip install scikit-learn numpy stable-baselines3

## How to run
- play the game < 10 times
  - load index.html with Chrome browser
- store logs in training_data-folder
- train the model:
  -  python3 train_offline.py
  -  random_forest_2048.pkl 

The script trains a RandomForestClassifier on the collected 2048 move logs, then pickles the fitted model so it can be reloaded later without retraining.

## Visualize model
- install matplot
  - uv pip install matplotlib
- ./visualize/load_2048_pkl.py