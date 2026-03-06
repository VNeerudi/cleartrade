"""
Explainability (paper §4, §6.4, §7): SHAP values and feature importance.
"""
import numpy as np
import joblib
from typing import List

FEATURE_NAMES = ["ma_10", "ma_30", "rsi", "volatility"]


def get_feature_importance(model_path: str, feats: dict, probs: List[float]) -> dict | None:
    """Coefficients or tree feature_importances_ for the predicted class."""
    try:
        model = joblib.load(model_path)
        idx = probs.index(max(probs)) if probs else 0
        if hasattr(model, "coef_"):
            row = model.coef_[idx] if getattr(model.coef_, "ndim", 1) > 1 else model.coef_
            try:
                imp = [float(abs(c)) for c in row]
            except TypeError:
                imp = [float(abs(row))] if isinstance(row, (int, float)) else []
        elif hasattr(model, "feature_importances_"):
            imp = model.feature_importances_.tolist()
        else:
            imp = []
        if imp:
            return dict(zip(FEATURE_NAMES, imp))
    except Exception:
        pass
    return None


def get_shap_values(model_path: str, feats: dict, feature_names: List[str] | None = None) -> dict | None:
    """
    SHAP values for the current prediction (paper §4, §7).
    TreeExplainer for Random Forest only (requires shap package).
    """
    feature_names = feature_names or FEATURE_NAMES
    try:
        import shap
    except ImportError:
        return None
    try:
        model = joblib.load(model_path)
        if not hasattr(model, "feature_importances_"):
            return None
        x = np.array([[feats.get(f, 0) for f in feature_names]])
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(x)
        if isinstance(shap_vals, list):
            pred_idx = int(np.argmax(model.predict_proba(x)[0]))
            shap_vals = shap_vals[pred_idx][0]
        else:
            shap_vals = shap_vals[0]
        if shap_vals is not None and len(shap_vals) == len(feature_names):
            return dict(zip(feature_names, [float(v) for v in shap_vals]))
    except Exception:
        pass
    return None
