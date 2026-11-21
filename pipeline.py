"""Shared reusable pipeline: models are initialized once for a query batch."""

from time import perf_counter
import importlib.metadata

from filtered_search import search_with_filters
from keyword_search import search_companies


class SearchPipeline:
    def __init__(self, companies, method="rerank", profile="description", candidates=100,
                 rank_only=False, qualify=False):
        if method not in {"keyword", "filters", "semantic", "hybrid", "rerank"}:
            raise ValueError("Unknown search method")
        if candidates < 1 or (rank_only and method != "rerank") or (qualify and method != "hybrid"):
            raise ValueError("Invalid candidate count or method options")
        started = perf_counter()
        self.companies, self.method, self.candidates = companies, method, candidates
        self.rank_only, self.engine, self.reranker, self.qualifier = rank_only, None, None, None
        if qualify:
            from qualification import Qualifier
            self.qualifier = Qualifier()
        if method in ("semantic", "hybrid", "rerank"):
            from semantic_search import SemanticSearch
            self.engine = SemanticSearch(companies, profile_mode=profile)
        if method == "rerank":
            from reranker import LocalReranker
            self.reranker = LocalReranker()
        self.load_seconds = perf_counter() - started
        self.metadata = {"rule_version": "composed_role_rules_v2",
                         "embedding": self.engine.encoder.identity if self.engine else None}
        if self.reranker:
            from reranker import MODEL_NAME
            self.metadata["reranker_model"] = MODEL_NAME
        if self.engine:
            self.metadata["dependencies"] = {name: importlib.metadata.version(name)
                for name in ("sentence-transformers", "transformers", "torch", "numpy")}

    def search(self, query, top=10):
        if top < 1 or not query.strip():
            raise ValueError("A nonempty query and positive top are required")
        if (self.reranker or self.qualifier) and top > self.candidates:
            raise ValueError("top cannot exceed candidate count")
        started = perf_counter()
        if self.method == "keyword":
            output = {"results": search_companies(self.companies, query, top), "uncertain_results": [],
                      "parsed_query": {"activity": query, "filters": [], "warnings": ["Keyword baseline; not qualified."]},
                      "counts": {"pass": len(self.companies), "unknown": 0, "fail": 0}}
        elif self.method == "filters":
            output = search_with_filters(self.companies, query, top)
        else:
            output = self.engine.search(query, self.candidates if self.reranker or self.qualifier else top,
                                        hybrid=self.method in ("hybrid", "rerank"))
        retrieved = perf_counter()
        if self.reranker:
            output = self.reranker.apply(output, query, self.candidates)
        ranked = perf_counter()
        if self.reranker and not self.rank_only:
            from role_checks import apply_role_checks
            output = apply_role_checks(output, top)
        elif self.reranker:
            output["results"] = output["results"][:top]
            output["uncertain_results"] = output["uncertain_results"][:top]
        if self.qualifier:
            output = self.qualifier.apply(output, query, top)
        ended = perf_counter()
        output["timings_seconds"] = {"retrieval": retrieved-started, "rerank": ranked-retrieved,
                                     "qualification": ended-ranked, "total": ended-started}
        output["qualified"] = bool(self.qualifier or (self.reranker and not self.rank_only))
        return output
