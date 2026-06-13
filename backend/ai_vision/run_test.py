import json
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from ai_vision.cv_layer import analyze_board

TEST_PHOTOS_DIR = Path(__file__).parent / "test_photos"



def run(image_path: str):
    print(f"\nAnalyzing: {image_path}")
    print("=" * 60)

    result = analyze_board(image_path)

    print(f"\n[Description]\n{result['circuit_description']}\n")

    print(f"[Components] ({len(result['components'])} found)")
    for comp in result["components"]:
        print(f"  {comp['id']:20s} {comp['type']:30s} {comp.get('hardware_model', '')}")

    print(f"\n[Connections] ({len(result['connections'])} found)")
    for conn in result["connections"]:
        print(
            f"  {conn['from_comp']:20s}.{conn['from_pin']:4s}"
            f"  ->  {conn['to_comp']:20s} {conn['to_header']:5s} [{conn['to_pin_label']:10s}]"
            f"  wire={conn['wire_color']}"
        )

    print("\n[Full JSON]")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        photos = list(TEST_PHOTOS_DIR.glob("*.jpg")) + list(TEST_PHOTOS_DIR.glob("*.png"))
        if not photos:
            print(f"No test photos found in {TEST_PHOTOS_DIR}")
            print("Drop a photo in test_photos/ or pass a path as argument.")
            sys.exit(1)
        for photo in photos:
            run(str(photo))
