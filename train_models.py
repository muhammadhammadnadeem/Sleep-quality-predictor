"""
Sleep Quality Predictor - Model Training Script
-------------------------------------------------
Trains a small ensemble of classic ML classifiers on the sleep lifestyle
features and saves them (along with the label encoder) as pickle files
that main_app.py loads at runtime.

Features used (6):
    Age, Sleep Hours, Screen Time, Caffeine Intake, Physical Activity

NOTE: Stress Level and Blood Pressure have been removed from the feature
set per product requirements. If you retrain on a real dataset, keep the
feature order below in sync with FEATURE_KEYS in main_app.py.
"""

import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB

# --- Dummy dataset (replace with a real, labeled dataset for production use) ---
# 5 features: Age, Sleep Hours, Screen Time, Caffeine Intake, Physical Activity
np.random.seed(42)
n_samples = 300

age = np.random.randint(16, 70, size=n_samples)
sleep_hours = np.round(np.random.uniform(3, 10, size=n_samples), 1)
screen_time = np.round(np.random.uniform(0, 12, size=n_samples), 1)
caffeine = np.round(np.random.uniform(0, 6, size=n_samples), 1)
physical = np.round(np.random.uniform(0, 14, size=n_samples), 1)

X = np.column_stack([age, sleep_hours, screen_time, caffeine, physical])


def label_row(row):
    """Simple heuristic labeling so the demo dataset is not pure noise."""
    _, sleep, screen, caff, activity = row
    score = 0
    score += 2 if 7 <= sleep <= 9 else (1 if 6 <= sleep < 7 or 9 < sleep <= 10 else -1)
    score += 1 if screen <= 4 else (0 if screen <= 7 else -1)
    score += 1 if caff <= 2 else (0 if caff <= 4 else -1)
    score += 1 if 2 <= activity <= 10 else 0
    if score >= 3:
        return "Good"
    if score >= 1:
        return "Average"
    return "Poor"


y = np.array([label_row(row) for row in X])

# Encode labels
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42
)

# Train models
models = {}
models["LogisticRegression"] = LogisticRegression(max_iter=1000).fit(X_train, y_train)
models["DecisionTree"] = DecisionTreeClassifier(max_depth=6, random_state=42).fit(X_train, y_train)
models["RandomForest"] = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42).fit(X_train, y_train)
models["KNN"] = KNeighborsClassifier(n_neighbors=5).fit(X_train, y_train)
models["NaiveBayes"] = GaussianNB().fit(X_train, y_train)

# Report quick accuracy for visibility
for name, model in models.items():
    acc = model.score(X_test, y_test)
    print(f"{name}: test accuracy = {acc:.2f}")

# Save models
with open("sleep_models_v3.pkl", "wb") as f:
    pickle.dump(models, f)

# Save label encoder
with open("label_encoder_v3.pkl", "wb") as f:
    pickle.dump(encoder, f)

print("Models trained and PKL files created successfully (5-feature schema).")
