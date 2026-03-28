"""
NLP model pipeline for Amazon Review Sentiment Classification.

Pipeline steps match the source notebook exactly:
1. clean_text          — regex: HTML, URLs, special chars, lowercase
2. remove_stopwords    — NLTK stopwords minus negation words
3. lemmatize_text      — spaCy en_core_web_sm lemmatiser
4. TF-IDF              — max_features=5000, ngram_range=(1,2)
5. Train/test split    — 80/20, stratified
6. SMOTE               — minority oversampling on training data only
7. t-SNE visualisation — before and after SMOTE
8. Logistic Regression — C=1.0, solver='lbfgs', max_iter=1000
"""

import os
import re
import pickle
import logging
from typing import List, Tuple, Dict

import numpy as np
import spacy
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.manifold import TSNE
from imblearn.over_sampling import SMOTE
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
SMOTE_DIST_PATH = os.path.join(MODEL_DIR, "smote_distribution.pkl")

NEGATION_WORDS = {
    "not", "no", "never", "neither", "nor", "nothing", "nobody", "nowhere",
    "none", "cannot", "can't", "won't", "didn't", "doesn't", "isn't",
    "wasn't", "aren't", "wouldn't", "couldn't", "shouldn't",
}

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Text Pre-processing
# ---------------------------------------------------------------------------
class TextPreprocessor:
    """Handles cleaning, stopword removal and lemmatisation."""

    def __init__(self):
        # Download NLTK stopwords
        nltk.download("stopwords", quiet=True)
        self.stop_words = set(stopwords.words("english")) - NEGATION_WORDS
        # Load spaCy model for lemmatisation
        self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])

    # Step 1
    @staticmethod
    def clean_text(text: str) -> str:
        """Remove HTML tags, URLs, special chars; lowercase."""
        text = re.sub(r"<[^>]+>", " ", text)             # HTML tags
        text = re.sub(r"http\S+|www\.\S+", " ", text)    # URLs
        text = re.sub(r"[^a-zA-Z\s]", " ", text)         # special chars
        text = text.lower().strip()
        return re.sub(r"\s+", " ", text)

    # Step 2
    def remove_stopwords(self, text: str) -> str:
        """Remove NLTK stopwords while keeping negation words."""
        return " ".join(w for w in text.split() if w not in self.stop_words)

    # Step 3
    def lemmatize_text(self, text: str) -> str:
        """Lemmatise using spaCy en_core_web_sm."""
        doc = self.nlp(text)
        return " ".join(token.lemma_ for token in doc)

    def preprocess(self, text: str) -> str:
        """Run the full preprocessing pipeline."""
        text = self.clean_text(text)
        text = self.remove_stopwords(text)
        text = self.lemmatize_text(text)
        return text

    def preprocess_batch(self, texts: List[str], batch_size: int = 500) -> List[str]:
        """Batch preprocessing: clean + stopwords in a list-comp, then
        lemmatise *all* texts at once with nlp.pipe()."""
        # Steps 1-2 are pure Python string ops → list comprehension
        cleaned = [
            self.remove_stopwords(self.clean_text(t)) for t in texts
        ]
        # Step 3: batch lemmatisation via spaCy pipe
        lemmatized = [
            " ".join(token.lemma_ for token in doc)
            for doc in self.nlp.pipe(cleaned, batch_size=batch_size)
        ]
        return lemmatized


# ---------------------------------------------------------------------------
# NLP Analyser (POS tagging + dependency parsing)
# ---------------------------------------------------------------------------
class NLPAnalyzer:
    """Extracts nouns, adjectives and feature→sentiment pairs."""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def analyze(self, text: str) -> dict:
        doc = self.nlp(text)
        return self._extract(doc)

    def analyze_batch(self, texts: List[str], batch_size: int = 500) -> List[dict]:
        """Batch NLP analysis using nlp.pipe()."""
        return [
            self._extract(doc)
            for doc in self.nlp.pipe(texts, batch_size=batch_size)
        ]

    @staticmethod
    def _extract(doc) -> dict:
        """Extract nouns, adjectives and feature→sentiment pairs from a spaCy Doc."""
        # POS tagging: NN/NNS → product features, JJ → sentiment descriptors
        nouns = list({token.text for token in doc if token.tag_ in ("NN", "NNS")})
        adjectives = list({token.text for token in doc if token.tag_ == "JJ"})

        # Dependency parsing: (noun, adjective) via amod and nsubj+acomp
        pairs: List[List[str]] = []
        for token in doc:
            if token.dep_ == "amod" and token.head.tag_ in ("NN", "NNS"):
                pairs.append([token.head.text, token.text])
            if token.dep_ == "acomp":
                for child in token.head.children:
                    if child.dep_ == "nsubj" and child.tag_ in ("NN", "NNS"):
                        pairs.append([child.text, token.text])

        return {
            "nouns": nouns,
            "adjectives": adjectives,
            "featureSentimentPairs": pairs,
        }


# ---------------------------------------------------------------------------
# Sentiment Model (TF-IDF + Logistic Regression + SMOTE)
# ---------------------------------------------------------------------------
class SentimentModel:
    """Train, persist and predict with TF-IDF + Logistic Regression."""

    def __init__(self, preprocessor: TextPreprocessor):
        self.preprocessor = preprocessor
        self.vectorizer: TfidfVectorizer | None = None
        self.classifier: LogisticRegression | None = None
        self.smote_distribution: dict = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self):
        with open(CLASSIFIER_PATH, "wb") as f:
            pickle.dump(self.classifier, f)
        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)
        with open(SMOTE_DIST_PATH, "wb") as f:
            pickle.dump(self.smote_distribution, f)
        logger.info("Model artefacts saved.")

    def load(self) -> bool:
        if os.path.exists(CLASSIFIER_PATH) and os.path.exists(VECTORIZER_PATH):
            with open(CLASSIFIER_PATH, "rb") as f:
                self.classifier = pickle.load(f)
            with open(VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)
            if os.path.exists(SMOTE_DIST_PATH):
                with open(SMOTE_DIST_PATH, "rb") as f:
                    self.smote_distribution = pickle.load(f)
            logger.info("Model loaded from disk.")
            return True
        return False

    # ------------------------------------------------------------------
    # Synthetic training data (fallback when no real dataset is present)
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_synthetic_data() -> Tuple[List[str], List[int]]:
        positive_reviews = [
            "This product is absolutely amazing and works perfectly",
            "Excellent quality and fast shipping, very happy with purchase",
            "Best purchase I have made, highly recommend to everyone",
            "Love this item, it exceeded all my expectations completely",
            "Great value for money, works exactly as described perfectly",
            "Outstanding product with premium build quality throughout",
            "Fantastic item arrived quickly and works like a charm",
            "Very pleased with this purchase will definitely buy again",
            "Superb quality and excellent customer service experience",
            "Perfect fit and finish, exactly what I was looking for",
            "This is wonderful, my family loves using it every day",
            "Incredible quality for the price, could not be happier",
            "Amazing product that delivers on every promise made",
            "Very satisfied customer here, top notch product overall",
            "Brilliant design and flawless execution, five stars",
            "Happy with purchase, good quality product delivered fast",
            "Impressive build and great functionality for daily use",
            "Terrific product, easy to set up and works great",
            "Really enjoy using this product, well worth the money",
            "This is a gem, outstanding in every way possible",
            "Delighted with this purchase, quality is top notch here",
            "Great product that works well and looks beautiful too",
            "Pleasantly surprised by the quality at this price point",
            "Wonderful item that makes life so much easier daily",
            "The best product I have purchased in a long time",
            "Solid construction and elegant design, very impressed",
            "Exceptional product quality, exceeded all my expectations",
            "This product deserves more than five stars honestly",
            "Reliable, sturdy and well-made, absolutely love it",
            "Top quality product, fast delivery, very happy customer",
            "Love the design and the performance is outstanding too",
            "Highly impressed with the quality and attention to detail",
            "My favorite purchase this year, wonderful product overall",
            "Well crafted and functional, could not ask for more",
            "Awesome product, works as described, would buy again",
            "Simply the best product in its category, hands down",
            "Very well made, durable and performs exactly as expected",
            "This made my day, perfect product for my needs exactly",
            "Premium quality at a reasonable price, highly recommend",
            "A truly excellent product, five stars from me always",
            "Beautifully designed and works flawlessly every time",
            "Such a great find, quality exceeds the price significantly",
            "Could not be happier with this fantastic purchase decision",
            "Exactly what I needed, great quality and fast shipping",
            "Nice quality build and solid performance, very satisfied",
            "I am thoroughly impressed with this wonderful product",
            "Smooth operation and premium feel, very happy customer",
            "Did not expect such high quality, pleasantly surprised",
            "Stellar product, will recommend to friends and family",
            "An absolute joy to use, makes everything so much easier",
        ]

        negative_reviews = [
            "Terrible product, broke after one day of use completely",
            "Worst purchase ever, do not waste your money on this",
            "Very disappointed with the quality, feels very cheap",
            "Product arrived damaged and customer service was unhelpful",
            "Does not work as described, total waste of money here",
            "Poor quality materials, fell apart within a week easily",
            "Horrible experience, would never buy from here again",
            "Not worth the price at all, extremely overpriced product",
            "Defective product and impossible to get a refund back",
            "Completely useless, does not function as advertised badly",
            "Awful product, regret buying it so much right now",
            "Cheap materials and poor craftsmanship throughout product",
            "This product is a scam, avoid at all costs please",
            "Very unhappy with this purchase, not what I expected",
            "Product stopped working after just two uses completely",
            "Junk product, not even worth the shipping cost paid",
            "Terrible quality control, received a broken item again",
            "Waste of money, looks nothing like the pictures shown",
            "Extremely frustrating product that never works properly",
            "Do not buy this product, you will regret it deeply",
            "Flimsy and poorly made, broke almost immediately sadly",
            "Not functional at all, had to throw it away fast",
            "Bad quality and misleading description, very frustrated",
            "Returned this product because it was completely useless",
            "Never buying from this brand again, total disappointment",
            "The worst product I have ever purchased without doubt",
            "Falls apart easily, not durable at all unfortunately",
            "Poorly designed and impossible to use, so frustrating",
            "Not satisfied at all, very poor quality and design",
            "This product is garbage, save your money for better",
            "Defective right out of the box, not acceptable really",
            "Disappointed that this product is so poorly constructed",
            "Could not get this to work no matter what I tried",
            "Broke on first use, absolutely terrible build quality",
            "Overpriced and underperforming product, very let down",
            "Not as described at all, feels like a knockoff product",
            "Horrible quality, wish I had read reviews before buying",
            "Product is a disaster, nothing works as it should here",
            "Terrible experience from start to finish with this item",
            "Very poorly packaged and arrived completely destroyed fast",
            "Save your money, this product is not worth a penny",
            "Unusable product, complete waste of time and money here",
            "I regret this purchase deeply, absolutely awful product",
            "Nothing good about this product, everything is wrong",
            "Unacceptable quality for the price they are charging now",
            "Stopped working within hours of first use unfortunately",
            "Poorly made with cheap components, not worth it at all",
            "Total rip off, avoid this product at all costs please",
            "Broken and defective, worst online shopping experience",
            "Do yourself a favor and skip this terrible product now",
        ]

        texts = positive_reviews + negative_reviews
        labels = [1] * len(positive_reviews) + [0] * len(negative_reviews)
        return texts, labels

    # ------------------------------------------------------------------
    # t-SNE visualisation
    # ------------------------------------------------------------------
    @staticmethod
    def _plot_tsne(X, y, filename: str, title: str):
        """Generate a t-SNE 2-D scatter plot and save to static/."""
        n_samples = min(800, X.shape[0])
        idx = np.random.RandomState(42).choice(X.shape[0], n_samples, replace=False)
        X_sub = X[idx]
        y_sub = np.array(y)[idx]

        if hasattr(X_sub, "toarray"):
            X_sub = X_sub.toarray()

        tsne = TSNE(
            n_components=2,
            perplexity=min(30, n_samples - 1),
            n_iter=1000,
            init="pca",
            random_state=42,
        )
        X_2d = tsne.fit_transform(X_sub)

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = {0: "#ef4444", 1: "#22c55e"}
        labels_map = {0: "Negative", 1: "Positive"}
        for cls in [0, 1]:
            mask = y_sub == cls
            ax.scatter(
                X_2d[mask, 0], X_2d[mask, 1],
                c=colors[cls], label=labels_map[cls],
                alpha=0.6, s=30, edgecolors="w", linewidth=0.5,
            )
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(fontsize=12)
        ax.set_xlabel("t-SNE 1")
        ax.set_ylabel("t-SNE 2")
        plt.tight_layout()
        filepath = os.path.join(STATIC_DIR, filename)
        fig.savefig(filepath, dpi=150)
        plt.close(fig)
        logger.info("t-SNE plot saved → %s", filepath)

    # ------------------------------------------------------------------
    # Training pipeline
    # ------------------------------------------------------------------
    def train(self):
        """Full training pipeline (Steps 1–8)."""
        # ── Data ──────────────────────────────────────────────────────
        texts, labels = self._generate_synthetic_data()
        logger.info("Synthetic dataset: %d samples", len(texts))

        # ── Steps 1-3: preprocess ─────────────────────────────────────
        processed = [self.preprocessor.preprocess(t) for t in texts]

        # ── Step 4: TF-IDF ────────────────────────────────────────────
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
        )
        X = self.vectorizer.fit_transform(processed)
        y = np.array(labels)

        # ── Step 5: train/test split ──────────────────────────────────
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        # ── Log class distribution before SMOTE ─────────────────────
        unique, counts = np.unique(y_train, return_counts=True)
        before_dist = dict(zip([str(u) for u in unique], [int(c) for c in counts]))
        logger.info("Class distribution BEFORE SMOTE: %s", before_dist)

        # ── t-SNE before SMOTE ────────────────────────────────────────
        self._plot_tsne(X_train, y_train, "tsne_before.png", "t-SNE Before SMOTE")

        # ── Step 6: SMOTE ─────────────────────────────────────────────
        smote = SMOTE(
            sampling_strategy="minority",
            k_neighbors=min(5, min(counts) - 1) if min(counts) > 1 else 1,
            random_state=42,
        )
        X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

        unique_a, counts_a = np.unique(y_resampled, return_counts=True)
        after_dist = dict(zip([str(u) for u in unique_a], [int(c) for c in counts_a]))
        logger.info("Class distribution AFTER SMOTE:  %s", after_dist)

        self.smote_distribution = {"before": before_dist, "after": after_dist}

        # ── t-SNE after SMOTE ─────────────────────────────────────────
        self._plot_tsne(
            X_resampled, y_resampled,
            "tsne_after.png", "t-SNE After SMOTE",
        )

        # ── Step 8: Logistic Regression ───────────────────────────────
        self.classifier = LogisticRegression(
            C=1.0, max_iter=1000, solver="lbfgs",
        )
        self.classifier.fit(X_resampled, y_resampled)

        # Evaluate on test set (informational)
        acc = self.classifier.score(X_test, y_test)
        logger.info("Test accuracy: %.4f", acc)

        self.save()
        logger.info("Training complete.")

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict(self, text: str) -> Tuple[str, float, str]:
        """Return (label, confidence, processed_text) for a single review."""
        processed = self.preprocessor.preprocess(text)
        X = self.vectorizer.transform([processed])
        proba = self.classifier.predict_proba(X)[0]
        pred_idx = int(np.argmax(proba))
        label = "positive" if pred_idx == 1 else "negative"
        confidence = float(round(proba[pred_idx], 4))
        return label, confidence, processed

    def predict_batch(
        self, texts: List[str], batch_size: int = 500,
    ) -> List[Tuple[str, float, str]]:
        """Vectorised batch prediction.

        1. preprocess_batch  → one spaCy nlp.pipe() call
        2. vectorizer.transform(list) → one sparse-matrix TF-IDF
        3. predict_proba(matrix) → one sklearn call
        """
        processed = self.preprocessor.preprocess_batch(texts, batch_size=batch_size)
        X = self.vectorizer.transform(processed)           # single sparse matrix
        proba = self.classifier.predict_proba(X)           # (N, 2) array
        pred_indices = np.argmax(proba, axis=1)            # (N,)
        labels = ["positive" if idx == 1 else "negative" for idx in pred_indices]
        confidences = [
            float(round(proba[i, pred_indices[i]], 4)) for i in range(len(texts))
        ]
        return list(zip(labels, confidences, processed))
