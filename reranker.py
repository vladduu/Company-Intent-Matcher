"""Local query/profile pair scoring after structured filtering and retrieval."""

import math
from pathlib import Path

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"


def ranking_text(company):
    # Main activity comes before secondary offerings to reduce truncation damage.
    parts = []
    for field in ("description", "core_offerings", "business_model", "target_markets"):
        value = company.get(field)
        if isinstance(value, list):
            value = "; ".join(v for v in value if isinstance(v, str))
        if isinstance(value, str) and value.strip():
            parts.append(f"{field}: {value.strip()}")
    return "\n".join(parts)


class LocalReranker:
    def __init__(self, model=None):
        if model is not None:
            self.model = model
            return
        try:
            from sentence_transformers import CrossEncoder
            import torch
            self.model = CrossEncoder(
                MODEL_NAME, device="cpu", max_length=512,
                activation_fn=torch.nn.Identity(), trust_remote_code=False,
                cache_folder=str(Path(__file__).resolve().parent / ".cache" / "reranker"))
        except (ImportError, OSError) as exc:
            raise RuntimeError("Could not load local reranker. Install requirements.txt; "
                               "the first run needs Hugging Face access to download its model. "
                               f"Details: {exc}") from exc

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
            candidates = [r for r in candidates if ranking_text(r["company"])]
            pairs = [(activity, ranking_text(r["company"])) for r in candidates]
            scores = self.model.predict(pairs, batch_size=16, show_progress_bar=False) if pairs else []
            if len(scores) != len(candidates):
                raise ValueError("Reranker returned the wrong score count")
            ranked = []
            for candidate, score in zip(candidates, scores):
                score = float(score)
                if not math.isfinite(score):
                    raise ValueError("Reranker returned an invalid score")
                ranked.append(dict(candidate, retrieval_score=candidate["score"], score=score,
                                   score_type="reranker_logit"))
            ranked.sort(key=lambda item: item["score"], reverse=True)
            result[group] = ranked[:top]
            count += len(ranked)
        result["reranked_count"] = count
        result["parsed_query"] = dict(output["parsed_query"], warnings=[
            w for w in output["parsed_query"]["warnings"] if not w.startswith("Semantic similarity")
        ] + ["Local reranker scores are not probabilities or verified qualification verdicts."])
        return result
