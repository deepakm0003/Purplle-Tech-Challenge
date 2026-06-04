"""Allow: python -m detector.process_video (via python -m detector)."""

from detector.process_video import run_cli
import sys

if __name__ == "__main__":
    sys.exit(run_cli())
