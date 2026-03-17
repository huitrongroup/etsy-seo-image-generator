#!/usr/bin/env python3
"""
Seasonal Content Generator & Analyzer
Powered by Claude (Anthropic)
"""

import argparse
import json
from dotenv import load_dotenv

from models import ContentRequest, ContentType, Season
from seasonal import get_current_season
from generators import generate_content, generate_variants, improve_content
from analyzer import analyze_content
from validators import validate_request

load_dotenv()


def cmd_generate(args: argparse.Namespace) -> None:
    season = Season(args.season) if args.season else get_current_season()
    req = ContentRequest(
        topic=args.topic,
        season=season,
        content_type=ContentType(args.type),
        tone=args.tone,
        keywords=args.keywords or [],
        max_length=args.max_length,
    )

    errors = validate_request(req)
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        return

    if args.variants:
        results = generate_variants(req, n=args.variants)
        for i, result in enumerate(results, 1):
            print(f"\n--- Variant {i} (score: {result.score}) ---")
            print(result.content)
            if result.issues:
                print("Issues:", result.issues)
    else:
        result = generate_content(req)
        print(f"\nGenerated content (score: {result.score}):\n")
        print(result.content)

        if result.issues:
            print(f"\nIssues found: {result.issues}")
            if args.auto_improve:
                print("\nAuto-improving...")
                improved = improve_content(result)
                print(f"\nImproved content (score: {improved.score}):\n")
                print(improved.content)


def cmd_analyze(args: argparse.Namespace) -> None:
    season = Season(args.season) if args.season else get_current_season()
    text = args.text or open(args.file).read()

    report = analyze_content(text, season, use_ai=not args.no_ai)

    if args.json:
        print(json.dumps({
            "score": report.score,
            "passed": report.passed,
            "season": report.season.value,
            "seasonal_keywords_found": report.seasonal_keywords_found,
            "rule_violations": report.rule_violations,
            "recommendations": report.recommendations,
        }, indent=2))
    else:
        print(f"\nAnalysis Report")
        print(f"  Season:   {report.season.value}")
        print(f"  Score:    {report.score}")
        print(f"  Passed:   {'YES' if report.passed else 'NO'}")
        print(f"  Keywords: {', '.join(report.seasonal_keywords_found) or 'none'}")
        if report.rule_violations:
            print(f"  Violations:")
            for v in report.rule_violations:
                print(f"    - {v}")
        if report.recommendations:
            print(f"  Recommendations:")
            for r in report.recommendations:
                print(f"    - {r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seasonal Content Generator & Analyzer")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate subcommand
    gen = sub.add_parser("generate", help="Generate seasonal content")
    gen.add_argument("topic", help="Content topic")
    gen.add_argument("--season", choices=[s.value for s in Season], help="Target season (default: current)")
    gen.add_argument("--type", default="blog", choices=[c.value for c in ContentType], dest="type")
    gen.add_argument("--tone", default="enthusiastic")
    gen.add_argument("--keywords", nargs="*")
    gen.add_argument("--max-length", type=int, default=500)
    gen.add_argument("--variants", type=int, metavar="N", help="Generate N variants")
    gen.add_argument("--auto-improve", action="store_true", help="Auto-improve if issues found")

    # analyze subcommand
    ana = sub.add_parser("analyze", help="Analyze content for seasonal fit")
    group = ana.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Text to analyze")
    group.add_argument("--file", help="Path to text file")
    ana.add_argument("--season", choices=[s.value for s in Season])
    ana.add_argument("--no-ai", action="store_true", help="Skip AI analysis (rules only)")
    ana.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "analyze":
        cmd_analyze(args)


if __name__ == "__main__":
    main()
