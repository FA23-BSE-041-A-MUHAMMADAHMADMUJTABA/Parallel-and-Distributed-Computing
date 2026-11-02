"""Safe, best-effort transfer of a complete CapCut Desktop draft between Windows PCs.

The module does not render video. It packages the draft folder and referenced local
assets, rewrites absolute filesystem references for the destination PC, restores the
folder into CapCut's local drafts root, and can launch CapCut Desktop.

CapCut's draft schema is undocumented and version-dependent. This deliberately keeps
all original project files intact except JSON string values that are confirmed to be
existing absolute filesystem paths and therefore need relocation.
"""
from __future__ import annotations

import hashlib
import json
import os
import ntpath
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Tuple

BUNDLE_VERSION = 1
PROJECT_TOKEN = "__DCPROJECT__/"
ASSET_TOKEN = "__DCASSET__/"
KNOWN_MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv", ".m4v", ".ts",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma",
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic", ".svg",
    ".srt", ".ass", ".lrc", ".ttf", ".otf", ".cube", ".lut", ".xml", ".json",
}


def capcut_drafts_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    return Path.home() / "AppData" / "Local" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_component(value: str, fallback: str = "CapCut_Project") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-")
    return (cleaned[:80] or fallback)


def _resolve_path_value(value: str) -> Path | None:
    """Return a real local path if a JSON string directly names an existing file."""
    raw = value.strip().strip('"').strip("'")
    if not raw:
        return None
    # CapCut JSON usually stores native paths. Also accept file:/// URLs.
    if raw.lower().startswith("file://"):
        from urllib.parse import urlparse, unquote
        parsed = urlparse(raw)
        raw = unquote(parsed.path)
        if os.name == "nt" and re.match(r"^/[A-Za-z]:", raw):
            raw = raw[1:]
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            raw = "\\\\" + parsed.netloc + raw.replace("/", "\\")
    try:
        candidate = Path(os.path.expandvars(os.path.expanduser(raw)))
        if candidate.is_absolute() and candidate.is_file():
            return candidate.resolve()
    except (OSError, ValueError):
        return None
    return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _walk_json_strings(value: Any, callback):
    if isinstance(value, dict):
        for key, child in list(value.items()):
            value[key] = _walk_json_strings(child, callback)
        return value
    if isinstance(value, list):
        return [_walk_json_strings(child, callback) for child in value]
    if isinstance(value, str):
        return callback(value)
    return value


def build_capcut_bundle(project_dir: str | os.PathLike, output_zip: str | os.PathLike) -> Dict[str, Any]:
    """Create a portable package containing the entire draft folder and local assets.

    The user should save and close CapCut before calling this function so the draft
    JSON and thumbnail/resource files are in a consistent state.
    """
    src = Path(project_dir).expanduser().resolve()
    out = Path(output_zip).expanduser().resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"CapCut project folder not found: {src}")
    if not ((src / "draft_content.json").is_file() or (src / "draft_info.json").is_file()):
        raise ValueError("This folder does not contain draft_content.json or draft_info.json.")
    out.parent.mkdir(parents=True, exist_ok=True)

    stage = Path(tempfile.mkdtemp(prefix="capcut_bundle_"))
    project_copy = stage / "project"
    external_dir = stage / "external_assets"
    external_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(src, project_copy, dirs_exist_ok=True, symlinks=False)
        asset_map: Dict[str, str] = {}
        missing_refs: List[str] = []
        total_assets_bytes = 0

        # Read the original JSON files (not the copies) to capture source absolute paths.
        json_files = list(src.rglob("*.json"))
        for original_json in json_files:
            rel = original_json.relative_to(src)
            copied_json = project_copy / rel
            try:
                with original_json.open("r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                # Preserve unknown/newer binary or non-JSON sidecar formats untouched.
                continue

            def relocate(raw: str) -> str:
                nonlocal total_assets_bytes
                candidate = _resolve_path_value(raw)
                if candidate is None:
                    is_absolute_ref = os.path.isabs(raw) or ntpath.isabs(raw) or raw.lower().startswith("file://")
                    if is_absolute_ref and Path(raw.replace("\\", "/")).suffix.lower() in KNOWN_MEDIA_EXTENSIONS:
                        if raw not in missing_refs:
                            missing_refs.append(raw)
                    return raw
                if _is_relative_to(candidate, src):
                    rel_path = candidate.relative_to(src).as_posix()
                    return PROJECT_TOKEN + rel_path
                token_key = None
                for existing_token, mapped_path in asset_map.items():
                    if mapped_path == str(candidate):
                        token_key = existing_token
                        break
                if token_key is None:
                    digest = _sha256(candidate)
                    stored_name = f"{digest[:16]}_{_safe_component(candidate.name, 'asset')}"
                    token_key = stored_name
                    asset_map[token_key] = str(candidate)
                    target = external_dir / stored_name
                    shutil.copy2(candidate, target)
                    total_assets_bytes += target.stat().st_size
                return ASSET_TOKEN + token_key

            rewritten = _walk_json_strings(data, relocate)
            copied_json.parent.mkdir(parents=True, exist_ok=True)
            with copied_json.open("w", encoding="utf-8") as f:
                json.dump(rewritten, f, ensure_ascii=False, indent=2)

        manifest = {
            "bundle_version": BUNDLE_VERSION,
            "project_folder_name": src.name,
            "project_name": src.name,
            "project_relative_path": "project",
            "external_assets": {k: k for k in asset_map},
            "asset_count": len(asset_map),
            "external_asset_bytes": total_assets_bytes,
            "missing_references": missing_refs,
            "created_unix": time.time(),
            "draft_files": len([p for p in project_copy.rglob("*") if p.is_file()]),
            "source_root_name": src.parent.name,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as zf:
            for file_path in stage.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(stage).as_posix())
        return {
            "bundle_path": str(out),
            "bundle_size": out.stat().st_size,
            "asset_count": len(asset_map),
            "asset_bytes": total_assets_bytes,
            "draft_file_count": manifest["draft_files"],
            "missing_refs": missing_refs,
        }
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _validate_zip_member(name: str) -> None:
    member = PurePosixPath(name.replace("\\", "/"))
    if member.is_absolute() or ".." in member.parts or not member.parts:
        raise ValueError(f"Unsafe path in project package: {name!r}")
    if re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"Absolute path in project package: {name!r}")


def _restore_tokens(value: Any, project_root: Path, asset_root: Path, manifest: Dict[str, Any]):
    if isinstance(value, dict):
        return {k: _restore_tokens(v, project_root, asset_root, manifest) for k, v in value.items()}
    if isinstance(value, list):
        return [_restore_tokens(v, project_root, asset_root, manifest) for v in value]
    if isinstance(value, str):
        if value.startswith(PROJECT_TOKEN):
            rel = PurePosixPath(value[len(PROJECT_TOKEN):])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Unsafe project-relative path in CapCut manifest.")
            return str((project_root / Path(*rel.parts)).resolve())
        if value.startswith(ASSET_TOKEN):
            key = value[len(ASSET_TOKEN):]
            asset_rel = manifest.get("external_assets", {}).get(key)
            if not asset_rel:
                raise ValueError(f"Missing asset mapping for {key!r}")
            safe_asset_rel = PurePosixPath(str(asset_rel))
            if safe_asset_rel.is_absolute() or ".." in safe_asset_rel.parts:
                raise ValueError("Unsafe external asset mapping in CapCut manifest.")
            return str((asset_root / Path(*safe_asset_rel.parts)).resolve())
    return value


def find_capcut_executable() -> str | None:
    """Best-effort locate CapCut Desktop on Windows."""
    candidates: List[Path] = []
    local = os.environ.get("LOCALAPPDATA")
    program_files = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
    if local:
        apps = Path(local) / "CapCut" / "Apps"
        if apps.is_dir():
            candidates.extend(apps.glob("*/CapCut.exe"))
            candidates.extend(apps.glob("*/*/CapCut.exe"))
    for root in program_files:
        if root:
            candidates.extend([
                Path(root) / "CapCut" / "CapCut.exe",
                Path(root) / "ByteDance" / "CapCut" / "CapCut.exe",
            ])
    # Registered uninstall locations are useful when CapCut's install folder moved.
    if os.name == "nt":
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for key_path in (
                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                ):
                    try:
                        root_key = winreg.OpenKey(hive, key_path)
                    except OSError:
                        continue
                    with root_key:
                        for i in range(winreg.QueryInfoKey(root_key)[0]):
                            try:
                                sub_name = winreg.EnumKey(root_key, i)
                                sub = winreg.OpenKey(root_key, sub_name)
                            except OSError:
                                continue
                            with sub:
                                try:
                                    display = winreg.QueryValueEx(sub, "DisplayName")[0]
                                    loc = winreg.QueryValueEx(sub, "InstallLocation")[0]
                                except OSError:
                                    continue
                                if "capcut" in str(display).lower() and loc:
                                    candidates.extend([Path(loc) / "CapCut.exe", Path(loc) / "CapCut" / "CapCut.exe"])
        except Exception:
            pass
    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate.resolve())
        except OSError:
            continue
    return None


def _atomic_json_write(path: Path, data: Dict[str, Any]) -> None:
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def _register_imported_draft(project_dir: Path, drafts_root: Path, project_name: str) -> Dict[str, Any]:
    """Register the transferred draft in CapCut's local root index when possible."""
    timeline_path = project_dir / "draft_content.json"
    if not timeline_path.is_file():
        timeline_path = project_dir / "draft_info.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
    duration = int(timeline.get("duration") or 0)
    now_us = int(time.time() * 1_000_000)
    new_draft_id = str(uuid.uuid4()).upper()
    sidecar_path = project_dir / "draft_meta_info.json"

    if sidecar_path.is_file():
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8-sig"))
    else:
        sidecar = {}
    sidecar.update({
        "draft_id": new_draft_id,
        "draft_fold_path": str(project_dir.resolve()),
        "draft_json_file": str(timeline_path.resolve()),
        "draft_name": str(timeline.get("name") or project_name),
        "draft_root_path": str(drafts_root.resolve()),
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": duration,
    })
    if not sidecar_path.exists():
        # Minimum sidecar metadata for installations that did not ship one in the draft.
        sidecar.setdefault("draft_materials", [])
    if sidecar_path.exists():
        shutil.copy2(sidecar_path, sidecar_path.with_suffix(sidecar_path.suffix + ".bak"))
    _atomic_json_write(sidecar_path, sidecar)

    root_index = drafts_root / "root_meta_info.json"
    if root_index.exists():
        root_data = json.loads(root_index.read_text(encoding="utf-8-sig"))
        store_key = next((k for k, v in root_data.items() if isinstance(v, list) and ("draft_store" in k or k == "all_draft_store")), "all_draft_store")
        store = root_data.setdefault(store_key, [])
        if not isinstance(store, list):
            raise ValueError("CapCut root_meta_info draft store is not a list.")
        template = next((x for x in store if isinstance(x, dict)), {})
        entry = dict(template)
    else:
        root_data = {"all_draft_store": []}
        store_key = "all_draft_store"
        store = root_data[store_key]
        entry = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": str((project_dir / "draft_cover.jpg").resolve()),
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_invisible": False,
            "draft_is_web_article_video": False,
            "draft_new_version": "",
            "draft_timeline_materials_size": 0,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "streaming_edit_draft_ready": True,
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
        }

    entry.update({
        "draft_fold_path": str(project_dir.resolve()),
        "draft_id": new_draft_id,
        "draft_json_file": str(timeline_path.resolve()),
        "draft_name": str(timeline.get("name") or project_name),
        "draft_root_path": str(drafts_root.resolve()),
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": duration,
    })
    cover = project_dir / "draft_cover.jpg"
    if cover.is_file():
        entry["draft_cover"] = str(cover.resolve())
    store[:] = [x for x in store if not isinstance(x, dict) or x.get("draft_fold_path") != str(project_dir.resolve())]
    store.insert(0, entry)
    if isinstance(root_data.get("draft_ids"), int):
        root_data["draft_ids"] += 1
    if root_index.exists():
        shutil.copy2(root_index, root_index.with_suffix(root_index.suffix + ".bak"))
    _atomic_json_write(root_index, root_data)
    return {"draft_id": new_draft_id, "registered": True, "root_index": str(root_index)}


def import_capcut_bundle(
    bundle_zip: str | os.PathLike,
    drafts_root: str | os.PathLike | None = None,
    launch_app: bool = True,
) -> Dict[str, Any]:
    """Safely restore a bundle under the target CapCut drafts folder and launch CapCut."""
    bundle = Path(bundle_zip).resolve()
    if not bundle.is_file() or not zipfile.is_zipfile(bundle):
        raise ValueError("Uploaded CapCut package is missing or is not a valid ZIP.")
    root = Path(drafts_root) if drafts_root else capcut_drafts_root()
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="capcut_import_", dir=str(root.parent)))
    try:
        with zipfile.ZipFile(bundle, "r") as zf:
            infos = zf.infolist()
            if len(infos) > 250000:
                raise ValueError("Project package contains an unreasonable number of files.")
            total_uncompressed = sum(i.file_size for i in infos)
            if total_uncompressed > 500 * 1024 * 1024 * 1024:
                raise ValueError("Project package exceeds the 500 GB safety limit.")
            for info in infos:
                _validate_zip_member(info.filename)
                # Reject Unix symlink entries; the bundle should contain regular files only.
                mode = (info.external_attr >> 16) & 0xFFFF
                if (mode & 0o170000) == 0o120000:
                    raise ValueError("Symbolic links are not allowed in CapCut project packages.")
            zf.extractall(stage)

        manifest_path = stage / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError("Package manifest is missing.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if int(manifest.get("bundle_version", 0)) != BUNDLE_VERSION:
            raise ValueError("Unsupported CapCut bundle version.")
        project_rel = PurePosixPath(str(manifest.get("project_relative_path", "project")))
        if project_rel.is_absolute() or ".." in project_rel.parts:
            raise ValueError("Invalid project path in package manifest.")
        staged_project = stage / Path(*project_rel.parts)
        if not staged_project.is_dir():
            raise ValueError("Draft folder is missing from package.")
        if not ((staged_project / "draft_content.json").is_file() or (staged_project / "draft_info.json").is_file()):
            raise ValueError("Restored folder does not contain a CapCut timeline JSON file.")

        original_name = _safe_component(manifest.get("project_folder_name", "CapCut_Project"))
        destination = root / original_name
        if destination.exists():
            destination = root / f"{original_name}_Transferred_{time.strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(staged_project, destination, dirs_exist_ok=False)

        staged_assets = stage / "external_assets"
        asset_root = destination / "__distributed_assets__"
        if staged_assets.is_dir():
            shutil.copytree(staged_assets, asset_root, dirs_exist_ok=True)
        else:
            asset_root.mkdir(parents=True, exist_ok=True)

        # Replace relocatable markers with final absolute paths on Computer B.
        for json_path in destination.rglob("*.json"):
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            restored = _restore_tokens(doc, destination, asset_root, manifest)
            json_path.write_text(json.dumps(restored, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            registration = _register_imported_draft(
                destination, root, str(manifest.get("project_name", original_name))
            )
        except Exception:
            # Do not leave a half-imported project if registration could not be committed.
            shutil.rmtree(destination, ignore_errors=True)
            raise

        capcut_exe = find_capcut_executable() if launch_app else None
        app_started = False
        if launch_app and capcut_exe:
            try:
                subprocess.Popen([capcut_exe], cwd=str(Path(capcut_exe).parent), close_fds=True)
                app_started = True
            except Exception as exc:
                launch_error = str(exc)
            else:
                launch_error = ""
        else:
            launch_error = "CapCut Desktop executable was not found on Computer B." if launch_app else ""

        return {
            "success": True,
            "project_name": manifest.get("project_name", original_name),
            "project_folder": str(destination),
            "drafts_root": str(root),
            "capcut_executable": capcut_exe or "",
            "capcut_started": app_started,
            "launch_error": launch_error,
            "asset_count": int(manifest.get("asset_count", 0)),
            "registration": registration,
            "note": (
                "The editable draft is restored on Computer B. CapCut was opened to its home screen; "
                "select the transferred project there and start Export on Computer B."
            ),
        }
    finally:
        shutil.rmtree(stage, ignore_errors=True)
