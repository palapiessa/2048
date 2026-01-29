import pickle, numpy as np, matplotlib.pyplot as plt
with open("random_forest_2048.pkl", "rb") as f:
    clf = pickle.load(f)

heatmap = clf.feature_importances_.reshape(4, 4)
plt.imshow(heatmap, cmap="magma")
plt.colorbar(label="Importance")
plt.title("Random Forest Feature Importance")
plt.xticks(range(4), range(4))
plt.yticks(range(4), range(4))
plt.xlabel("Column index")
plt.ylabel("Row index")
plt.show()

from sklearn import tree

feature_names = [f"r{r}c{c}" for r in range(4) for c in range(4)]  # Label tiles by grid position
class_names = ["UP", "RIGHT", "DOWN", "LEFT"]  # Map classifier outputs back to moves
example = clf.estimators_[0]
plt.figure(figsize=(25, 15))  # Enlarge canvas so tree details are readable when rendered
tree.plot_tree(
    example,
    max_depth=3,
    filled=True,
    rounded=True,
    feature_names=feature_names,
    class_names=class_names,
)
plt.show()

# Map which board tiles this example tree splits on and how often.
usage_grid = np.zeros((4, 4), dtype=np.int32)
for feature_idx in example.tree_.feature:
    if feature_idx >= 0:  # -2 marks leaves
        row, col = divmod(feature_idx, 4)
        usage_grid[row, col] += 1

plt.figure(figsize=(6, 6))
plt.imshow(usage_grid, cmap="Purples", origin="upper")
for row in range(4):
    for col in range(4):
        idx = row * 4 + col
        label = feature_names[idx]
        count = usage_grid[row, col]
        text = f"{label}\n{count} split{'s' if count != 1 else ''}" if count else label
        color = "white" if count else "black"
        plt.text(col, row, text, ha="center", va="center", color=color, fontsize=10)

plt.xticks(range(4), range(4))
plt.yticks(range(4), range(4))
plt.xlabel("Column index")
plt.ylabel("Row index")
plt.title("Example tree feature usage across board")
plt.colorbar(label="Number of splits")
plt.tight_layout()
plt.show()
