"""Show all extracted templates in a grid."""

import cv2
import numpy as np
from pathlib import Path

def create_template_grid(templates_dir: Path, output_path: str = "templates_grid.png"):
    """Create a grid showing all templates."""

    templates = []
    for f in sorted(templates_dir.glob("*.png")):
        img = cv2.imread(str(f))
        if img is not None:
            name = f.stem
            templates.append((name, img))

    if not templates:
        print("No templates found")
        return

    print(f"Found {len(templates)} templates")

    # Create grid
    cols = 10
    rows = (len(templates) + cols - 1) // cols

    # Find max dimensions
    max_w = max(t[1].shape[1] for t in templates)
    max_h = max(t[1].shape[0] for t in templates)

    # Add padding and label space
    cell_w = max_w + 4
    cell_h = max_h + 20  # Space for label

    # Create canvas
    grid = np.ones((rows * cell_h, cols * cell_w, 3), dtype=np.uint8) * 240

    for idx, (name, img) in enumerate(templates):
        row = idx // cols
        col = idx % cols

        x = col * cell_w + 2
        y = row * cell_h + 2

        # Place template
        h, w = img.shape[:2]
        grid[y:y+h, x:x+w] = img

        # Add label (truncated)
        label = name[:8]
        cv2.putText(grid, label, (x, y + max_h + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    # Save
    cv2.imwrite(output_path, grid)

    # Also create enlarged version
    enlarged = cv2.resize(grid, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(output_path.replace(".png", "_4x.png"), enlarged)

    print(f"Saved: {output_path}")
    print(f"Saved: {output_path.replace('.png', '_4x.png')}")


if __name__ == "__main__":
    import sys
    templates_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("templates/western")
    create_template_grid(templates_dir)
