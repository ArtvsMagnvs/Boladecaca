# backend/app/tools/git_tool.py
#
# V0.4 (Fase 2 AgentManager + ToolSystem) + V0.5 (Fase 2):
# Wrapper seguro de Git con division clara entre acciones de solo-lectura
# (sin confirmacion) y acciones que modifican el repo (requieren confirmacion).
#
# Solo-lectura: status, log, diff, branch_list, show_file
# Modificacion: commit, add
#
# El cwd se valida: debe ser un repositorio git (contenga .git/) o un
# subdirectorio del mismo.

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseTool


READ_ONLY_ACTIONS = {"status", "log", "diff", "branch_list", "show_file"}
MUTATION_ACTIONS = {"add", "commit"}


class GitTool(BaseTool):
    tool_id = "git"
    name = "Git Tool"
    description = (
        "Wrapper seguro de Git. Acciones de solo lectura (status, log, diff, "
        "branch_list, show_file) no requieren confirmacion. Las que modifican "
        "el repo (add, commit) requieren confirmacion. Push/clone/fetch NO "
        "estan permitidos en V0.5."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if action not in READ_ONLY_ACTIONS and action not in MUTATION_ACTIONS:
                return {
                    "success": False,
                    "result": None,
                    "error": (
                        f"Accion desconocida: {action}. "
                        f"Disponibles: {', '.join(sorted(READ_ONLY_ACTIONS | MUTATION_ACTIONS))}"
                    ),
                }

            repo_path_str = params.get("repo_path", ".")
            repo_path = Path(os.path.expandvars(os.path.expanduser(repo_path_str))).resolve()

            # Seguridad: el repo debe estar dentro de HOME.
            home = Path.home().resolve()
            try:
                repo_path.relative_to(home)
            except ValueError:
                return {
                    "success": False,
                    "result": None,
                    "error": f"repo fuera de HOME: {repo_path}",
                }

            if not (repo_path / ".git").exists() and not (repo_path / ".git").is_dir():
                return {
                    "success": False,
                    "result": None,
                    "error": f"no es un repositorio git (falta .git/): {repo_path}",
                }

            handler = {
                "status": self._status,
                "log": self._log,
                "diff": self._diff,
                "branch_list": self._branch_list,
                "show_file": self._show_file,
                "add": self._add,
                "commit": self._commit,
            }.get(action)
            return await handler(repo_path, params)

        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "status", "description": "git status (formato porcelain)",
             "requires_confirmation": False, "params": {"repo_path": "string"}},
            {"id": "log", "description": "git log (ultimos N commits)",
             "requires_confirmation": False, "params": {"repo_path": "string", "limit": "int opcional (default 10)"}},
            {"id": "diff", "description": "git diff (cambios no commiteados)",
             "requires_confirmation": False, "params": {"repo_path": "string", "staged": "bool opcional"}},
            {"id": "branch_list", "description": "Lista las ramas locales",
             "requires_confirmation": False, "params": {"repo_path": "string"}},
            {"id": "show_file", "description": "Muestra el contenido tracked de un archivo",
             "requires_confirmation": False, "params": {"repo_path": "string", "path": "string"}},
            {"id": "add", "description": "git add <pathspec> (anade cambios al staging)",
             "requires_confirmation": True, "params": {"repo_path": "string", "pathspec": "string ('.' para todo)"}},
            {"id": "commit", "description": "git commit -m <msg>",
             "requires_confirmation": True, "params": {"repo_path": "string", "message": "string"}},
        ]

    # --- Acciones read-only ---

    async def _run_git(self, repo_path: Path, *args: str, timeout: int = 15) -> Dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"ok": False, "stdout": "", "stderr": f"timeout tras {timeout}s"}
        return {
            "ok": proc.returncode == 0,
            "stdout": (stdout or b"").decode("utf-8", errors="replace"),
            "stderr": (stderr or b"").decode("utf-8", errors="replace"),
            "returncode": proc.returncode,
        }

    async def _status(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._run_git(repo_path, "status", "--porcelain")
        return {
            "success": result["ok"],
            "result": {"porcelain": result["stdout"].strip().splitlines() if result["stdout"].strip() else []},
            "error": None if result["ok"] else result["stderr"].strip(),
        }

    async def _log(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get("limit", 10))
        limit = max(1, min(limit, 100))
        result = await self._run_git(
            repo_path, "log", f"-n{limit}", "--pretty=format:%h%x09%an%x09%ad%x09%s", "--date=short"
        )
        if not result["ok"]:
            return {"success": False, "result": None, "error": result["stderr"].strip()}
        commits = []
        for line in result["stdout"].splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 3)
            if len(parts) == 4:
                commits.append({"hash": parts[0], "author": parts[1], "date": parts[2], "message": parts[3]})
        return {"success": True, "result": {"commits": commits, "count": len(commits)}, "error": None}

    async def _diff(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        staged = bool(params.get("staged", False))
        args = ["diff", "--stat"]
        if staged:
            args.append("--staged")
        result = await self._run_git(repo_path, *args)
        return {
            "success": result["ok"],
            "result": {"diff_stat": result["stdout"]},
            "error": None if result["ok"] else result["stderr"].strip(),
        }

    async def _branch_list(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._run_git(repo_path, "branch", "--format=%(refname:short)")
        if not result["ok"]:
            return {"success": False, "result": None, "error": result["stderr"].strip()}
        branches = [b.strip() for b in result["stdout"].splitlines() if b.strip()]
        return {"success": True, "result": {"branches": branches, "count": len(branches)}, "error": None}

    async def _show_file(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params.get("path")
        if not path:
            return {"success": False, "result": None, "error": "falta parametro: path"}
        if ".." in Path(path).parts:
            return {"success": False, "result": None, "error": "path invalido (..)"}
        result = await self._run_git(repo_path, "show", f"HEAD:{path}")
        return {
            "success": result["ok"],
            "result": {"path": path, "content": result["stdout"]} if result["ok"] else None,
            "error": None if result["ok"] else result["stderr"].strip(),
        }

    # --- Acciones de modificacion ---

    async def _add(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        pathspec = params.get("pathspec", ".")
        if ".." in Path(pathspec).parts:
            return {"success": False, "result": None, "error": "pathspec invalido (..)"}
        result = await self._run_git(repo_path, "add", "--", pathspec)
        return {
            "success": result["ok"],
            "result": {"pathspec": pathspec, "stderr": result["stderr"].strip()},
            "error": None if result["ok"] else result["stderr"].strip(),
        }

    async def _commit(self, repo_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "").strip()
        if not message:
            return {"success": False, "result": None, "error": "falta parametro: message"}
        result = await self._run_git(repo_path, "commit", "-m", message)
        return {
            "success": result["ok"],
            "result": {"stdout": result["stdout"].strip(), "stderr": result["stderr"].strip()},
            "error": None if result["ok"] else result["stderr"].strip(),
        }