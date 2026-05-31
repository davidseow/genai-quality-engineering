"""Run this script to verify your local environment is ready for the course."""

import sys


def check_python() -> bool:
    ok = sys.version_info >= (3, 10)
    status = "✓" if ok else "✗"
    print(f"{status} Python {sys.version.split()[0]} (need 3.10+)")
    return ok


def check_credentials() -> bool:
    try:
        import google.auth
        credentials, project = google.auth.default()
        ok = credentials is not None
        status = "✓" if ok else "✗"
        print(f"{status} Google credentials found (project: {project or 'not set'})")
        return ok
    except Exception as exc:
        print(f"✗ Google credentials not found: {exc}")
        return False


def check_vertex_ai() -> bool:
    try:
        import vertexai  # noqa: F401
        print("✓ Vertex AI SDK importable")
        return True
    except ImportError:
        print("✗ google-cloud-aiplatform not installed — run: pip install -r shared/requirements.txt")
        return False


def main() -> None:
    results = [check_python(), check_credentials(), check_vertex_ai()]
    if all(results):
        print("\nReady to go!")
    else:
        print("\nSome checks failed — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
