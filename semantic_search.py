"""Local embedding retrieval with a content-addressed profile cache."""

import hashlib
import json
import math
from pathlib import Path

from filters import check_filters
from query_parser import parse_query


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "semantic"


def profile_text(company, mode="full"):
    if mode == "description":
        value = company.get("description")
        return value.strip() if isinstance(value, str) else ""
    if mode != "full":
        raise ValueError("Profile mode must be full or description")
    parts = []
    for field in ("core_offerings", "description", "business_model", "target_markets"):
        value = company.get(field)
        if isinstance(value, list):
            value = "; ".join(item for item in value if isinstance(item, str))
        if isinstance(value, str) and value.strip():
            parts.append(f"{field}: {value.strip()}")
    return "\n".join(parts)


def unit_vector(vector):
    values = [float(value) for value in vector]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("Invalid embedding values")
    length = math.sqrt(sum(value * value for value in values))
    if not length:
        raise ValueError("Zero embedding")
    return [value / length for value in values]


class LocalEncoder:
    def __init__(self):
        try:
            import sentence_transformers
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("Install semantic dependencies with: python -m pip install -r requirements.txt") from error
        try:
            self.model = SentenceTransformer(MODEL_NAME, device="cpu",
                                             cache_folder=str(CACHE_DIR / "models"),
                                             trust_remote_code=False)
        except ImportError as error:
            raise RuntimeError(f"Missing model-loading dependency: {error}. Run: python -m pip install -r requirements.txt") from error
        except OSError as error:
            raise RuntimeError("Could not load the embedding model. The first run needs access to Hugging Face; later runs can use the downloaded model.") from error
        revision = getattr(self.model[0].auto_model.config, "_commit_hash", None)
        self.identity = {"model": MODEL_NAME, "revision": revision,
                         "library_version": sentence_transformers.__version__,
                         "max_seq_length": self.model.max_seq_length}

    def encode(self, texts):
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                 show_progress_bar=False, convert_to_numpy=True).tolist()


class SemanticSearch:
    def __init__(self, companies, encoder=None, cache_dir=CACHE_DIR, profile_mode="full"):
        if profile_mode not in ("full", "description"):
            raise ValueError("Profile mode must be full or description")
        self.companies = companies
        self.encoder = encoder if encoder is not None else LocalEncoder()
        self.texts = [profile_text(company, profile_mode) for company in companies]
        self.indices = [i for i, text in enumerate(self.texts) if text]
        texts = [self.texts[i] for i in self.indices]
        identity = {"encoder": self.encoder.identity, "text_format": 2,
                    "profile_mode": profile_mode, "texts": texts}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
        cache_path = Path(cache_dir) / f"{key}.json"
        self.cache_hit = False
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            vectors = cached["vectors"]
            if cached["key"] != key or len(vectors) != len(texts):
                raise ValueError("Cache mismatch")
            self.vectors = [unit_vector(vector) for vector in vectors]
            if len({len(vector) for vector in self.vectors}) > 1:
                raise ValueError("Inconsistent embedding dimensions")
            self.cache_hit = True
        except (OSError, ValueError, KeyError, TypeError):
            self.vectors = [unit_vector(vector) for vector in self.encoder.encode(texts)] if texts else []
            if len(self.vectors) != len(texts) or len({len(v) for v in self.vectors}) > 1:
                raise ValueError("Encoder returned invalid embedding dimensions/count")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"key": key, "vectors": self.vectors}), encoding="utf-8")
            temporary.replace(cache_path)

    def search(self, query, top=10, hybrid=False):
        if not query.strip() or top < 1:
            raise ValueError("Provide a nonempty query and positive top")
        parsed = parse_query(query) if hybrid else {"activity": query, "filters": [], "warnings": []}
        activity = parsed["activity"].strip()
        query_vector = unit_vector(self.encoder.encode([activity])[0]) if activity else None
        groups = {"pass": [], "unknown": []}
        counts = {"pass": 0, "unknown": 0, "fail": 0}
        vectors_by_index = dict(zip(self.indices, self.vectors))
        for i, company in enumerate(self.companies):
            check = check_filters(company, parsed["filters"])
            counts[check["status"]] += 1
            if check["status"] == "fail":
                continue
            if query_vector is not None:
                vector = vectors_by_index.get(i)
                if vector is None:
                    continue
                if len(vector) != len(query_vector):
                    raise ValueError("Query/profile embedding dimensions differ; rebuild the cache")
                score = sum(a * b for a, b in zip(query_vector, vector))
            else:
                score = 0.0
            groups[check["status"]].append({"company": company, "score": score,
                                            "filter_check": check, "score_type": "cosine_similarity"})
        for group in groups.values():
            group.sort(key=lambda result: result["score"], reverse=True)
        # Parser warnings describe the old keyword stage; keep actual parser limitations.
        parsed["warnings"] = [w for w in parsed["warnings"] if not w.startswith("Activity and business role")]
        parsed["warnings"].append("Semantic similarity ranks candidates; it does not confirm their business role or full intent match.")
        return {"parsed_query": parsed, "results": groups["pass"][:top],
                "uncertain_results": groups["unknown"][:top], "counts": counts}
