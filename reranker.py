"""Local query/profile pair scoring after structured filtering and retrieval."""

import math
from pathlib import Path

from semantic_search import labeled_profile_text

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"


def ranking_text(company):
    # Main activity comes before secondary offerings to reduce truncation damage.
    fields = ("description", "core_offerings", "business_model", "target_markets")
    return labeled_profile_text(company, fields)


class LocalReranker:
    def __init__(self, model=None):
        if model is not None:
            self.model = model
            return
        try:
            from sentence_transformers import CrossEncoder
            import torch

            self.model = CrossEncoder(
                MODEL_NAME,
                device="cpu",
                max_length=512,
                activation_fn=torch.nn.Identity(),
                trust_remote_code=False,
                cache_folder=str(
                    Path(__file__).resolve().parent / ".cache" / "reranker"
                ),
            )
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Could not load local reranker. Install requirements.txt; "
                "the first run needs Hugging Face access to download its model. "
                f"Details: {exc}"
            ) from exc

    def apply(self, output, query, top):
        if top < 1:
            raise ValueError("top must be positive")
        # Structured constraints have already been checked, leaving role/activity.
        activity = output["parsed_query"]["activity"].strip()
        result = dict(output)
        count = 0
        for group in ("results", "uncertain_results"):
            candidates = output[group]
            if not activity:
                result[group] = candidates[:top]
                continue
            scoreable_candidates = []
            pairs = []
            for candidate in candidates:
                text = ranking_text(candidate["company"])
                if text:
                    scoreable_candidates.append(candidate)
                    pairs.append((activity, text))
            scores = []
            if pairs:
                scores = self.model.predict(
                    pairs, batch_size=16, show_progress_bar=False
                )
            if len(scores) != len(scoreable_candidates):
                raise ValueError("Reranker returned the wrong score count")
            ranked = []
            for candidate, score in zip(scoreable_candidates, scores):
                score = float(score)
                if not math.isfinite(score):
                    raise ValueError("Reranker returned an invalid score")
                ranked.append(
                    dict(
                        candidate,
                        retrieval_score=candidate["score"],
                        score=score,
                        score_type="reranker_logit",
                    )
                )
            ranked.sort(key=lambda item: item["score"], reverse=True)
            result[group] = ranked[:top]
            count += len(ranked)
        result["reranked_count"] = count
        result["parsed_query"] = dict(
            output["parsed_query"],
            warnings=[
                w
                for w in output["parsed_query"]["warnings"]
                if not w.startswith("Semantic similarity")
            ]
            + [
                "Local reranker scores are not probabilities or verified qualification verdicts."
            ],
        )
        return result
