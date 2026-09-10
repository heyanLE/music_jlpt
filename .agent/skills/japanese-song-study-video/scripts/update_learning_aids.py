"""Change only learning-aid options in an existing project; preserve all other settings."""
import argparse
from pathlib import Path
from configure_layers import load, write
from foreground_options import configure_options


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--learning-assist", choices=("on", "off"))
    parser.add_argument("--neighbors", choices=("on", "off"))
    parser.add_argument("--countdown", choices=("on", "off"))
    parser.add_argument("--prelude-mode", choices=("first-line", "hidden"))
    args = parser.parse_args()
    if all(value is None for value in (args.learning_assist, args.neighbors, args.countdown, args.prelude_mode)):
        parser.error("Supply at least one explicit option; existing projects are never migrated implicitly")
    project = args.project_root / "project"; path = project / "presentation.json"
    presentation = load(path)
    foreground = presentation["foreground"]
    options = configure_options(foreground, args.neighbors or args.learning_assist, args.countdown or args.learning_assist, args.prelude_mode)
    foreground.update(options)
    presentation["schemaVersion"] = max(3, presentation.get("schemaVersion", 1))
    write(path, presentation)
    state_path = project / "build-state.json"
    if state_path.is_file():
        state = load(state_path); state["renderAuthorization"] = False
        state.setdefault("notes", []).append("Learning-aid settings explicitly updated; existing render authorization is stale. Content and source settings preserved.")
        write(state_path, state)
    print("Updated only learning-aid settings. Rebind render authorization after checking the requested layout.")


if __name__ == "__main__": main()
