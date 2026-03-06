"""
LSTM for technical trend prediction (paper §4, §7: temporal dependencies in financial time series).
Input: sequences of [ma_10, ma_30, rsi, volatility] over SEQUENCE_LEN days.
Output: BUY/HOLD/SELL probabilities.
"""
import os
import numpy as np
import pandas as pd

SEQUENCE_LEN = 20
FEATURES = ["ma_10", "ma_30", "rsi", "volatility"]
LSTM_MODEL_PATH = os.path.join(os.path.dirname(__file__), "lstm_model.keras")
LSTM_META_PATH = os.path.join(os.path.dirname(__file__), "lstm_meta.joblib")


def build_sequences(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build (X, y) where X is (n_samples, SEQUENCE_LEN, n_features) and y is class 0/1/2."""
    df = df.dropna(subset=FEATURES + ["y"]).sort_values("date").reset_index(drop=True)
    if "y" not in df.columns or len(df) < SEQUENCE_LEN + 1:
        return np.array([]), np.array([])
    X_list, y_list = [], []
    for i in range(len(df) - SEQUENCE_LEN):
        window = df.iloc[i : i + SEQUENCE_LEN][FEATURES].values.astype(np.float32)
        label = int(df.iloc[i + SEQUENCE_LEN]["y"])
        X_list.append(window)
        y_list.append(label)
    if not X_list:
        return np.array([]), np.array([])
    X = np.array(X_list)
    y = np.array(y_list)
    return X, y


def train_lstm(df: pd.DataFrame, epochs: int = 30, batch_size: int = 32) -> str:
    """Train LSTM and save to LSTM_MODEL_PATH. Returns path or error message."""
    try:
        import joblib
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError:
        return "tensorflow not installed; pip install tensorflow"

    X, y = build_sequences(df)
    if len(X) < 50:
        return "Not enough sequences; need more price history"

    n_features = len(FEATURES)
    model = keras.Sequential([
        layers.Input(shape=(SEQUENCE_LEN, n_features)),
        layers.LSTM(32, return_sequences=False),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(3, activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(X, y, epochs=epochs, batch_size=batch_size, validation_split=0.1, verbose=0)
    model.save(LSTM_MODEL_PATH)
    joblib.dump({"n_features": n_features, "sequence_len": SEQUENCE_LEN}, LSTM_META_PATH)
    return LSTM_MODEL_PATH


def predict_lstm(feats_sequence: np.ndarray) -> tuple[str, float, list] | None:
    """
    feats_sequence: shape (SEQUENCE_LEN, 4) for [ma_10, ma_30, rsi, volatility].
    Returns (signal, confidence, probs) or None if model missing.
    """
    if not os.path.isfile(LSTM_MODEL_PATH):
        return None
    try:
        from tensorflow import keras
        import joblib
        model = keras.models.load_model(LSTM_MODEL_PATH)
        meta = joblib.load(LSTM_META_PATH)
        seq_len = meta.get("sequence_len", SEQUENCE_LEN)
        if feats_sequence.shape[0] != seq_len or feats_sequence.shape[1] != len(FEATURES):
            return None
        X = np.expand_dims(feats_sequence.astype(np.float32), axis=0)
        probs = model.predict(X, verbose=0)[0].tolist()
        idx = int(np.argmax(probs))
        labels = ["SELL", "HOLD", "BUY"]
        return labels[idx], float(probs[idx]), probs
    except Exception:
        return None
