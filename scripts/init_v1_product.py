"""Initialize the explicitly configured local database for AQuantAI V1."""

from __future__ import annotations

from alembic import command
from alembic.config import Config


def main() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    print("AQuantAI V1 local database is at the latest migration.")


if __name__ == "__main__":
    main()
