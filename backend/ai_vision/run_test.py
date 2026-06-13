import json
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from ai_vision.cv_layer import analyze_board

TEST_PHOTOS_DIR = Path(__file__).parent / "test_photos"


def run(project_folder: str):
    print(f"\nAnalyzing: {project_folder}")
    print("=" * 60)

    result = analyze_board(project_folder)

    print(f"\n[Description]\n{result['circuit_description']}\n")

    print(f"[Components] ({len(result['components'])} found)")
    for comp in result["components"]:
        print(f"  {comp['id']:20s} {comp['type']:30s} {comp.get('hardware_model', '')}")

    print(f"\n[Connections] ({len(result['connections'])} found)")
    for conn in result["connections"]:
        from_hdr = f" {conn.get('from_header', '')}" if conn.get('from_header') else ""
        to_hdr = f" {conn.get('to_header', '')}" if conn.get('to_header') else ""
        path = (
            f"  {conn['from_comp']}{from_hdr} [{conn['from_pin_label']}]"
            f"  ->  {conn['to_comp']}{to_hdr} [{conn['to_pin_label']}]"
            f"  wire={conn['wire_color']} (Type: {conn['signal_type']})"
        )
        print(path)

    print("\n[Full JSON]")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        projects = sorted(p for p in TEST_PHOTOS_DIR.iterdir() if p.is_dir())
        if not projects:
            print(f"No project folders found in {TEST_PHOTOS_DIR}")
            print("Create a subfolder (e.g. project1/) with side-view and top-view images.")
            sys.exit(1)
        for project in projects:
            run(str(project))
