"""Single entry point. MARK code stays in mark_app; ULTRON stays isolated."""
from integration.launcher import main

if __name__ == '__main__':
    raise SystemExit(main())
