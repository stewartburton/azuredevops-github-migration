import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# We'll import interactive and call _paginated_picker with controlled questionary


def test_paginated_picker_fuzzy_and_jump(monkeypatch):
    import azuredevops_github_migration.interactive as inter

    items = ["AlphaProject", "BetaSample", "GammaTool", "DeltaService"]

    # Sequence: search/filter -> provide 'gt' -> select 'GammaTool'
    answers = iter(
        [
            "Search / filter",  # initial navigation choice
            "GammaTool",  # final selection after filter narrows
        ]
    )

    class FakeSelect:
        def __init__(self, *a, **k):
            pass

        def ask(self):
            try:
                return next(answers)
            except StopIteration:
                return None

    class FakeText:
        def __init__(self, *a, **k):
            pass

        def ask(self):
            return "gt"

    class FakeQ:
        def select(self, *a, **k):
            return FakeSelect()

        def text(self, *a, **k):
            return FakeText()

        def Choice(self, **k):
            return k.get("value")

    monkeypatch.setattr(inter, "questionary", FakeQ())

    chosen = inter._paginated_picker("Select project", items, page_size=2)
    assert chosen == "GammaTool"


def test_paginated_picker_jump(monkeypatch):
    import azuredevops_github_migration.interactive as inter

    items = ["AlphaProject", "BetaSample", "GammaTool", "DeltaService"]

    # Sequence: jump to letter -> DeltaService
    answers = iter(["Jump to letter", "DeltaService"])

    class FakeSelect:
        def __init__(self, *a, **k):
            pass

        def ask(self):
            try:
                return next(answers)
            except StopIteration:
                return None

    class FakeText:
        def ask(self):
            return "D"

    class FakeQ:
        def select(self, *a, **k):
            return FakeSelect()

        def text(self, *a, **k):
            return FakeText()

        def Choice(self, **k):
            return k.get("value")

    monkeypatch.setattr(inter, "questionary", FakeQ())
    chosen = inter._paginated_picker("Select project", items, page_size=2)
    assert chosen == "DeltaService"
