#!/usr/bin/env python
"""Django CLI entry point."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bluemetrics.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django não está instalado. Execute: pip install -e .[dev]"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
