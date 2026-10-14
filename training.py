"""Reusable model training and validation for the helpdesk app."""

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


def build_tiny_pipeline(ngram_range: tuple[int, int], regularization_c: float) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=ngram_range, lowercase=True)),
        ("classifier", LogisticRegression(
            C=regularization_c, max_iter=1000, random_state=42,
        )),
    ])


@st.cache_resource(show_spinner="Fitting the selected model...")
def train_model(
    texts: tuple[str, ...],
    categories: tuple[str, ...],
    ngram_range: tuple[int, int],
    regularization_c: float,
) -> Pipeline:
    """Reuse fits for identical training rows and settings across reruns/sessions.

    The returned pipeline is shared: callers must only predict, never mutate it.
    """
    model = build_tiny_pipeline(ngram_range, regularization_c)
    model.fit(texts, categories)
    return model


def evaluate_model(model: Pipeline, validation_df: pd.DataFrame, training_categories) -> tuple[dict, dict]:
    predictions = model.predict(validation_df["query"])
    labels = sorted(set(training_categories) | set(validation_df["expected_category"]))
    true_labels = validation_df["expected_category"]
    report = classification_report(
        true_labels, predictions, labels=labels, output_dict=True, zero_division=0,
    )
    scores = {
        "validation_accuracy": float(accuracy_score(true_labels, predictions)),
        "validation_precision_macro": float(report["macro avg"]["precision"]),
        "validation_recall_macro": float(report["macro avg"]["recall"]),
        "validation_f1_macro": float(report["macro avg"]["f1-score"]),
    }
    # predictions preserves query/label alignment; confusion is ready for a student heatmap.
    results = {
        "per_category": pd.DataFrame([
            {"Category": label, "Precision": report[label]["precision"],
             "Recall": report[label]["recall"], "F1": report[label]["f1-score"],
             "Support": int(report[label]["support"])} for label in labels
        ]),
        "predictions": validation_df.assign(
            predicted_category=predictions,
            correct=(true_labels.to_numpy() == predictions),
        ),
        "confusion": pd.DataFrame(
            confusion_matrix(true_labels, predictions, labels=labels),
            index=pd.Index(labels, name="Actual"),
            columns=pd.Index(labels, name="Predicted"),
        ),
    }
    return scores, results
