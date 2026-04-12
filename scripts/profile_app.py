# ruff: noqa: D103
"""Profile the application with various backends.

Wraps py-spy, cProfile, VizTracer, and Scalene into a single entry point
so you don't have to remember each tool's CLI flags.

Usage:
    # cProfile (built-in, no extra deps):
    uv run python -m scripts.profile_app cprofile

    # py-spy sampling (install: pip install py-spy):
    uv run python -m scripts.profile_app pyspy

    # VizTracer timeline (install: pip install viztracer):
    uv run python -m scripts.profile_app viztracer

    # Scalene line-level profiling (install: pip install scalene):
    uv run python -m scripts.profile_app scalene

    Outputs are written to ./profiling_output/ by default.
"""

from __future__ import annotations

import argparse
import cProfile
import os
import pstats
import shutil
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path("profiling_output")


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def run_cprofile(sort_by: str = "cumulative", top_n: int = 40) -> None:
    """Run the app under cProfile and print stats on exit."""
    out = ensure_output_dir() / "cprofile.prof"

    print(f"Starting app under cProfile (output: {out})")
    print("Interact with the GUI, then close it to see results.\n")

    profiler = cProfile.Profile()
    profiler.enable()

    from pymmcore_gui import create_mmgui

    create_mmgui(exec_app=True)

    profiler.disable()
    profiler.dump_stats(str(out))

    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats(sort_by)
    print(f"\n{'=' * 70}")
    print(f"cProfile results (top {top_n}, sorted by {sort_by})")
    print(f"{'=' * 70}")
    stats.print_stats(top_n)
    print(f"\nFull profile saved to: {out}")
    print("View interactively:  python -m pstats profiling_output/cprofile.prof")
    print("Or with snakeviz:    snakeviz profiling_output/cprofile.prof")


def run_pyspy() -> None:
    """Launch the app under py-spy for sampling-based profiling."""
    if not shutil.which("py-spy"):
        print("py-spy not found. Install with: pip install py-spy")
        sys.exit(1)

    out = ensure_output_dir()
    svg_out = out / "pyspy_flamegraph.svg"
    speedscope_out = out / "pyspy_speedscope.json"

    print("Launching app under py-spy...")
    print(f"  Flame graph:  {svg_out}")
    print(f"  Speedscope:   {speedscope_out}")
    print("Interact with the GUI. Close it or Ctrl+C to stop recording.\n")

    app_cmd = [
        sys.executable,
        "-c",
        "from pymmcore_gui import create_mmgui; create_mmgui()",
    ]

    # SVG flame graph
    cmd = [
        "sudo" if os.name != "nt" else "",  # py-spy may require sudo on Linux
        "py-spy",
        "record",
        "-o",
        str(svg_out),
        "--format",
        "flamegraph",
        "--",
        *app_cmd,
    ]

    # Add --native on supported platforms (Linux x86_64 / Windows)
    if sys.platform == "linux" or sys.platform == "win32":
        cmd.insert(2, "--native")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass

    print(f"\nFlame graph saved to: {svg_out}")
    print("Open in browser to explore.")

    # Also suggest live top mode
    print("\nTip: for live monitoring, run:")
    print("  py-spy top --pid <PID>")


def run_viztracer() -> None:
    """Launch the app under VizTracer for timeline analysis."""
    try:
        from viztracer import VizTracer  # type: ignore
    except ImportError:
        print(
            "VizTracer not found. Install with: uv run --with viztracer python -m "
            "scripts.profile_app viztracer"
        )
        sys.exit(1)

    out = ensure_output_dir() / "viztracer.json"

    print(f"Starting app under VizTracer (output: {out})")
    print("Interact with the GUI, then close it.\n")

    tracer = VizTracer(
        max_stack_depth=15,
        output_file=str(out),
    )
    tracer.start()

    from pymmcore_gui import create_mmgui

    create_mmgui(exec_app=True)

    tracer.stop()
    tracer.save()

    print(f"\nTrace saved to: {out}")
    print(f"View with:  vizviewer {out}")
    print("Or open in Perfetto UI: https://ui.perfetto.dev")


def run_scalene() -> None:
    """Launch the app under Scalene for line-level Python-vs-native profiling."""
    if not shutil.which("scalene"):
        print("Scalene not found. Install with: pip install scalene")
        sys.exit(1)

    print("Launching app under Scalene...")
    print("Interact with the GUI, then close it.\n")

    cmd = [
        "scalene",
        "--cpu",
        "--memory",
        "--reduced-profile",
        "--",
        sys.executable,
        "-c",
        "from pymmcore_gui import create_mmgui; create_mmgui()",
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile pymmcore-gui with various backends.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  uv run python -m scripts.profile_app cprofile
  uv run python -m scripts.profile_app cprofile --sort tottime --top 60
  uv run python -m scripts.profile_app pyspy
  uv run python -m scripts.profile_app viztracer
  uv run python -m scripts.profile_app scalene
""",
    )
    parser.add_argument(
        "backend",
        choices=["cprofile", "pyspy", "viztracer", "scalene"],
        help="Profiling backend to use.",
    )
    parser.add_argument(
        "--sort",
        default="cumulative",
        help="Sort key for cProfile (default: cumulative).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=40,
        help="Number of top entries to show for cProfile (default: 40).",
    )
    args = parser.parse_args()

    os.chdir(Path(__file__).resolve().parent.parent)

    if args.backend == "cprofile":
        run_cprofile(sort_by=args.sort, top_n=args.top)
    elif args.backend == "pyspy":
        run_pyspy()
    elif args.backend == "viztracer":
        run_viztracer()
    elif args.backend == "scalene":
        run_scalene()


if __name__ == "__main__":
    main()
