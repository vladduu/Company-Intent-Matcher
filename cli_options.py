"""Shared search options for the application and evaluation commands."""


def add_options(parser, default_method):
    parser.add_argument(
        "--method",
        choices=("keyword", "filters", "semantic", "hybrid", "rerank"),
        default=default_method,
        help=f"Search method (default: {default_method})",
    )
    parser.add_argument(
        "--rank-only", action="store_true", help="Skip local qualification with rerank"
    )
    profile_help = "Text used for embeddings (default: full)"
    if default_method == "rerank":
        profile_help = "Text used for embeddings (default: description with rerank, full otherwise)"
    parser.add_argument("--profile", choices=("full", "description"), help=profile_help)
    parser.add_argument(
        "--qualify",
        action="store_true",
        help="Send hybrid shortlist to OpenAI for qualification",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=100,
        help="Shortlist size per filter group (default: 100)",
    )


def check_options(parser, args, top):
    if top < 1:
        parser.error("--top must be positive")
    if args.rank_only and args.method != "rerank":
        parser.error("--rank-only requires --method rerank")
    if args.qualify and args.method != "hybrid":
        parser.error("--qualify requires --method hybrid")
    if args.candidates < 1 or (
        (args.qualify or args.method == "rerank") and args.candidates < top
    ):
        parser.error(
            "--candidates must be positive and at least --top when qualifying or reranking"
        )
    if args.profile == "description" and args.method not in (
        "semantic",
        "hybrid",
        "rerank",
    ):
        parser.error("--profile description requires semantic, hybrid or rerank")
    if args.profile is None:
        args.profile = (
            "description"
            if args.method == "rerank" and parser.get_default("method") == "rerank"
            else "full"
        )
