"""Streamlit entrypoint for the C.E.N.T.I.N.E.L. dashboard."""

from __future__ import annotations

import runpy


if __name__ == "__main__":
    runpy.run_path("dashboard/streamlit_app.py", run_name="__main__")
