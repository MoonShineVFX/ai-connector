from pathlib import Path


def get_latest_animate_diff(path: Path):
    files = list(path.glob("*.gif"))
    if not files:
        return None

    file = max(
        files,
        key=lambda x: x.stat().st_ctime,
    )

    # check if txt exists
    txt = file.with_suffix(".txt")

    return {"gif": file, "txt": txt if txt.exists() else None}
