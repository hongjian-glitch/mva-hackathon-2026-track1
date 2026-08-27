from __future__ import annotations

import argparse
import json

from .pipeline import analyze, write_analysis
from .submission import preflight, write_submission


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mva-solver")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--vcf", required=True)
    analyze_parser.add_argument("--transcript-config", required=True)
    analyze_parser.add_argument("--transcript-fasta", required=True)
    analyze_parser.add_argument("--clinvar-vcf", required=True)
    analyze_parser.add_argument("--output", required=True)

    build_parser = subparsers.add_parser("build-submission")
    build_parser.add_argument("--analysis", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--proband-id", default="PROBAND01")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--submission", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "analyze":
        result = analyze(
            vcf_path=args.vcf,
            transcript_config=args.transcript_config,
            transcript_fasta=args.transcript_fasta,
            clinvar_vcf=args.clinvar_vcf,
        )
        write_analysis(result, args.output)
        print(json.dumps(result["counts"], sort_keys=True))
        return 0
    if args.command == "build-submission":
        write_submission(args.analysis, args.output, proband_id=args.proband_id)
        errors = preflight(args.output)
        if errors:
            for error in errors:
                print(error)
            return 2
        print(f"preflight_ok={args.output}")
        return 0
    if args.command == "preflight":
        errors = preflight(args.submission)
        if errors:
            for error in errors:
                print(error)
            return 2
        print(f"preflight_ok={args.submission}")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
