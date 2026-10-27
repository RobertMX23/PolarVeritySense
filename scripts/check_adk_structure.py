from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sport_assistant_agent.agent import root_agent
from sport_assistant_agent.real_tools import fetch_real_exercise_tool


def main() -> int:
    print(f"root_agent={root_agent.name}")
    print(f"real_tool={fetch_real_exercise_tool.__name__}")
    print("ADK structure: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
