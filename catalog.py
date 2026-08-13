# --- catalog.py
# ...because hardcoding ~650 files takes time

import logging
from pathlib import Path

infinityLog = logging.getLogger("infinity")

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# main categories, obviously not including series, or game versions
CATEGORY_FOLDER_MAP = [
    ("power disc", "powerdisc"),
    ("toy box", "powerdisc"),
    ("play set", "playset"),
    ("playset", "playset"),
    ("character", "character"),
]


def _mapCategoryFolder(folderName: str) -> str | None:
    lowered = folderName.lower()
    for needle, category in CATEGORY_FOLDER_MAP:
        if needle in lowered:
            return category
    return None


def _pairsInDirectory(directory: Path) -> list[tuple[str, Path, Path]]:
    # finding pairs of bin and image files using 'stem' (name of the figure)
    binFiles = {p.stem: p for p in directory.glob("*.bin")}

    imageFiles: dict[str, Path] = {}
    for ext in IMAGE_EXTENSIONS:
        for p in directory.glob(f"*{ext}"):
            imageFiles[p.stem] = p

    pairs = []
    for stem, binPath in binFiles.items():
        imagePath = imageFiles.get(stem)
        if imagePath is None:
            infinityLog.warning(f"Item: '{binPath}' has no matching image, skipping..")
            continue
        pairs.append((stem, binPath, imagePath))

    for stem in imageFiles:
        if stem not in binFiles:
            infinityLog.warning(f"Item: '{imageFiles[stem]}' has no matching binary, skipping..")

    return pairs


def scanCatalog(resourcesRoot: Path, franchise: str = "infinity") -> list[dict]:
    # { name, category, subcategory, version, image, binPath }
    # name refers to the name of the file
    # category refers to the main category, ie powerdisc etc
    # extra unnecessary categories are subcategories like series 1 etc
    # version
    # image is a relative path to the image
    # binPath is an absolute path to the bin file

    franchiseRoot = resourcesRoot / "nfc" / franchise
    catalog = []

    if not franchiseRoot.is_dir():
        infinityLog.warning(f"Image: {franchiseRoot} does not exist..")
        return catalog

    for versionDir in sorted(p for p in franchiseRoot.iterdir() if p.is_dir()):
        version = versionDir.name

        for categoryDir in sorted(p for p in versionDir.iterdir() if p.is_dir()):
            category = _mapCategoryFolder(categoryDir.name)
            if category is None:
                infinityLog.warning(f"Item: unrecognized category '{categoryDir.name}', skipping")
                continue

            # pairs directly inside the category folder (no nesting)
            for stem, binPath, imagePath in _pairsInDirectory(categoryDir):
                catalog.append({
                    "name": stem,
                    "category": category,
                    "subcategory": None,
                    "version": version,
                    "image": str(imagePath.relative_to(resourcesRoot)).replace("\\", "/"),
                    "binPath": str(binPath),
                })

            # pairs inside any nested subfolder
            for subDir in sorted(p for p in categoryDir.rglob("*") if p.is_dir()):
                subcategory = subDir.relative_to(categoryDir).as_posix()

                for stem, binPath, imagePath in _pairsInDirectory(subDir):
                    catalog.append({
                        "name": stem,
                        "category": category,
                        "subcategory": subcategory,
                        "version": version,
                        "image": str(imagePath.relative_to(resourcesRoot)).replace("\\", "/"),
                        "binPath": str(binPath),
                    })

    return catalog