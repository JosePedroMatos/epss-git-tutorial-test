"""Tutorial progress check. Needs only Python and git.

    python tools/check_progress.py            table in the terminal
    python tools/check_progress.py --serve    guide + live status on a local page
    python tools/check_progress.py --json     status as JSON
    python tools/check_progress.py --ci       GitHub Actions: status.json, run summary, exit 1 if broken

Checkpoints describe what is on GitHub's main branch (origin/main after a fetch).
"Problems" describe the files in this folder.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = "FORESIGHT-ULisboa/epss-git-tutorial"
PAGE = "https://foresight-ulisboa.github.io/epss-git-tutorial/"
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OFFLINE = os.environ.get("TUTORIAL_OFFLINE") == "1"
CACHE = ROOT / ".git" / "tutorial-progress.json"

MODULES = {"A": ("weather/stats.py", "monthly_summary"),
           "B": ("weather/temperature.py", "add_tmean"),
           "C": ("weather/plots.py", "plot_temperature")}
NOTEBOOK = "analysis.ipynb"
NOTEBOOK_CALLS = ("monthly_summary", "add_tmean")
MARKER = re.compile(r"^(<{7}|>{7}) ", re.M)


# ---------------------------------------------------------------- git helpers
def run_git(*args, timeout=30):
    """(succeeded, stdout) of a git command run in the repository."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return r.returncode == 0, r.stdout.strip()


def git(*args, timeout=30):
    """stdout of a git command, '' if it fails."""
    ok, out = run_git(*args, timeout=timeout)
    return out if ok else ""


def slug():
    """owner/name of the GitHub repository, or ''."""
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", git("remote", "get-url", "origin"))
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def main_ref():
    return "origin/main" if git("rev-parse", "--verify", "--quiet", "origin/main") else "HEAD"


def show(ref, path):
    """Text of a file at a commit, or None if it is not there."""
    ok, out = run_git("show", f"{ref}:{path}")
    return out if ok else None


def api(path, anonymous_ok=False):
    """Parsed JSON from the GitHub API, or None (no token, offline, error)."""
    if OFFLINE or not (TOKEN or anonymous_ok):
        return None
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": "tutorial-progress-check"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None


# ---------------------------------------------------------------- checkpoints
def team_sections(text):
    """{'A': filled?, 'B': ..., 'C': ...} and the team name from TEAM.md."""
    filled, name = {}, ""
    for letter in "ABC":
        m = re.search(rf"^## Member {letter}\s*$(.*?)(?=^## |\Z)", text or "", re.M | re.S)
        lines = [l for l in (m.group(1) if m else "").splitlines() if l.strip().startswith("-")]
        filled[letter] = bool(lines) and all(
            l.split(":", 1)[-1].strip() not in ("", "...") for l in lines)
    m = re.search(r"^Team name:\s*(.*)$", text or "", re.M)
    if m and m.group(1).strip() not in ("", "(to be decided)"):
        name = m.group(1).strip()
    return filled, name


def authors(ref, repo):
    """Distinct commit authors on main: GitHub logins when the API is available, else emails."""
    commits = api(f"/repos/{repo}/commits?sha=main&per_page=100") if repo else None
    if commits:
        logins = {c["author"]["login"] for c in commits if c.get("author")
                  and not c["author"]["login"].endswith("[bot]")}
        unlinked = {c["commit"]["author"]["email"] for c in commits if not c.get("author")}
        return logins, unlinked
    emails = {e.lower() for e in git("log", ref, "--format=%ae").splitlines()
              if e and "[bot]" not in e}
    return emails, set()


def protection(repo):
    """True/False when GitHub answers, None when it cannot be asked from here."""
    if not TOKEN and CACHE.exists():
        return True, "pull request required before merging"
    rules = api(f"/repos/{repo}/rules/branches/main", anonymous_ok=True)
    if rules is None:
        return None, "checked on GitHub: see the Actions tab or the progress page"
    pr = [r for r in rules if r.get("type") == "pull_request"]
    if not pr:
        branch = api(f"/repos/{repo}/branches/main", anonymous_ok=True) or {}
        if branch.get("protected"):
            pr = [{"parameters": branch.get("protection", {})}]
    if not pr:
        return False, "no rule yet: member A adds the ruleset (step 2.1)"
    approvals = (pr[0].get("parameters") or {}).get("required_approving_review_count")
    if approvals == 0:
        return False, "the rule exists, but Required approvals is 0: set it to 1"
    if not TOKEN:
        try:
            CACHE.write_text(json.dumps({"protected": True}))
        except OSError:
            pass
    return True, "pull request required before merging"


def pull_requests(ref, repo):
    pulls = api(f"/repos/{repo}/pulls?state=closed&base=main&per_page=50") if repo else None
    if pulls is None:  # no API: read the merge commits
        subjects = git("log", ref, "--format=%s").splitlines()
        numbers = {m.group(1) for s in subjects
                   for m in [re.match(r"Merge pull request #(\d+)", s) or re.search(r"\(#(\d+)\)$", s)] if m}
        ok = len(numbers) >= 3
        return ok, f"{len(numbers)} merged" + (" (approvals are checked on GitHub)" if numbers else "")
    good, waiting = {}, []
    for p in (p for p in pulls if p.get("merged_at")):
        author = p["user"]["login"]
        reviews = api(f"/repos/{repo}/pulls/{p['number']}/reviews") or []
        if any(r["state"] == "APPROVED" and r["user"]["login"] != author for r in reviews):
            good.setdefault(author, p["number"])
        else:
            waiting.append(f"#{p['number']} merged without a teammate's approval")
    detail = ", ".join(f"#{n} by {a}" for a, n in sorted(good.items(), key=lambda x: x[1])) or "none yet"
    if len(good) < 3:
        detail += f" ({len(good)} of 3 members)"
    return len(good) >= 3, "; ".join([detail] + waiting[:2])


def wired(ref):
    todo = [f"member {m}'s function" for m, (path, _) in MODULES.items()
            if "NotImplementedError" in (show(ref, path) or "NotImplementedError")]
    report = show(ref, "report.py") or ""
    unused = sum(f"{fn}(" not in report for _, fn in MODULES.values())
    if unused:
        todo.append(f"{unused} of the 3 calls in report.py")
    if todo:
        return False, "not on main yet: " + ", ".join(todo)
    return True, "all three functions are on main and used in report.py"


def notebook(ref):
    text = show(ref, NOTEBOOK)
    try:
        cells = json.loads(text)["cells"]
    except (TypeError, ValueError, KeyError):
        return False, f"{NOTEBOOK} on main is not a valid notebook"
    code = [c for c in cells if c.get("cell_type") == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code)
    missing = [fn for fn in NOTEBOOK_CALLS if f"{fn}(" not in source]
    if missing:
        return False, "no cell on main calls " + " or ".join(missing) + " yet"
    if any(c.get("outputs") or c.get("execution_count") for c in code):
        return False, "both cells are there; outputs are not cleared yet (Clear All Outputs, commit)"
    return True, "both new cells are on main, outputs cleared"


def checkpoints():
    ref, repo = main_ref(), slug()
    filled, team_name = team_sections(show(ref, "TEAM.md"))
    who, unlinked = authors(ref, repo)
    merges = int(git("rev-list", "--merges", "--count", ref) or 0)

    out = []

    def add(cid, part, title, ok, detail=""):
        out.append({"id": cid, "part": part, "title": title, "ok": ok, "detail": detail})

    is_copy = bool(repo) and repo.lower() != TEMPLATE.lower()
    add("repo", 0, "Group repository created from the template", is_copy,
        f"github.com/{repo}" if is_copy else "this is still the template: member A creates the group's copy")

    add("first-push", 1, "Member A's first commit is on GitHub", filled["A"],
        "" if filled["A"] else "Member A's section of TEAM.md is not filled in on GitHub yet")

    waiting = [f"member {m}'s section" for m in "ABC" if not filled[m]]
    if len(who) < 3:
        waiting.append(f"commits from 3 people (now {len(who)})")
    if not merges:
        waiting.append("a merge commit (comes from the pull after a rejected push)")
    detail = "waiting for: " + ", ".join(waiting) if waiting else f"{len(who)} authors, {merges} merge(s)"
    if unlinked:
        detail += f"; not linked to a GitHub account: {', '.join(sorted(unlinked))} (check user.email)"
    add("everyone", 1, "All three members have pushed to main", not waiting, detail)

    add("conflict", 1, "Team name agreed after the conflict", bool(team_name),
        f'"{team_name}"' if team_name else "TEAM.md on GitHub still says (to be decided)")

    ok, detail = protection(repo) if is_copy and (team_name or TOKEN) else (False, "comes in step 2.1")
    add("protected", 2, "main is protected: changes arrive by pull request", ok, detail)

    add("prs", 2, "Three pull requests merged, each approved by a teammate", *pull_requests(ref, repo))
    add("wired", 2, "Three functions written and used in report.py", *wired(ref))
    add("notebook", 3, "Notebook has both new cells and no outputs", *notebook(ref))
    return out


# ------------------------------------------------------------------ problems
def problems():
    """Things that are broken in the files of this folder."""
    found = []
    for path in git("ls-files").splitlines():
        if path.startswith(("docs/", "tools/")) or not path.endswith((".py", ".md", ".ipynb", ".txt", ".csv")):
            continue
        try:
            text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if MARKER.search(text):
            found.append(f"{path} still contains conflict markers (<<<<<<< or >>>>>>>)")
        elif path.endswith(".py"):
            try:
                compile(text, path, "exec")
            except SyntaxError as e:
                found.append(f"{path} has a syntax error on line {e.lineno}")
        elif path.endswith(".ipynb"):
            try:
                json.loads(text)
            except ValueError:
                found.append(f"{path} is not a valid notebook any more")
    return found


def local_state():
    """What a newcomer needs to know about their own clone."""
    name, email = git("config", "user.name"), git("config", "user.email")
    branch = git("branch", "--show-current") or "(no branch)"
    changed = len(git("status", "--porcelain").splitlines())
    counts = git("rev-list", "--left-right", "--count", "@{upstream}...HEAD").split()
    lines = [("you are", f"{name} <{email}>" if name and email
              else "NOT SET: run the git config lines of step 0.1")]
    if len(counts) == 2:
        behind, ahead = counts
        lines.append(("branch", f"{branch}  ({ahead} commit(s) to push, {behind} to pull)"))
    else:
        lines.append(("branch", f"{branch}  (not on GitHub yet: Publish Branch)"))
    lines.append(("changes", f"{changed} file(s) changed and not committed" if changed else "nothing uncommitted"))
    return lines


def status(source, fetch=True):
    if fetch and not OFFLINE and source != "github-actions":
        git("fetch", "--quiet", "origin", timeout=20)
    cps = checkpoints()
    return {"schema": 1, "repo": slug(), "source": source,
            "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "done": sum(c["ok"] is True for c in cps), "total": len(cps),
            "checkpoints": cps, "problems": problems()}


# -------------------------------------------------------------------- output
def print_table(st):
    box = {True: "[x]", False: "[ ]", None: "[?]"}
    print(f"\nTutorial progress  -  {st['repo'] or 'no GitHub repository found'}  (what is on GitHub's main)\n")
    for n, c in enumerate(st["checkpoints"], 1):
        print(f" {box[c['ok']]} {n}  {c['title']}")
        if c["detail"] and c["ok"] is not True:
            print(f"        -> {c['detail']}")
    print(f"\n {st['done']} of {st['total']} done.\n\nYour computer")
    for key, value in local_state():
        print(f"  {key:<9}{value}")
    if st["problems"]:
        print("\nProblems to fix")
        for p in st["problems"]:
            print(f"  ! {p}")
    if st["repo"] and st["repo"].lower() != TEMPLATE.lower():
        print(f"\nProgress page: {PAGE}?repo={st['repo']}")
    print()


def write_summary(st):
    icon = {True: ":white_check_mark:", False: ":white_large_square:", None: ":grey_question:"}
    rows = [f"## Tutorial progress: {st['done']} of {st['total']}", "", "| | Checkpoint | Note |", "|---|---|---|"]
    rows += [f"| {icon[c['ok']]} | {c['title']} | {c['detail']} |" for c in st["checkpoints"]]
    if st["problems"]:
        rows += ["", "### Problems in this commit", ""] + [f"- :x: {p}" for p in st["problems"]]
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")


def serve(port):
    """Serve docs/ plus /api/status computed from this clone."""
    last = {"time": None, "data": None}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT / "docs"), **kw)

        def do_GET(self):
            if self.path.split("?")[0] != "/api/status":
                return super().do_GET()
            now = datetime.datetime.now()
            fetch = last["time"] is None or (now - last["time"]).total_seconds() > 20
            if fetch:
                last["time"] = now
            body = json.dumps(dict(status("local", fetch=fetch), local=dict(local_state()))).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *a):
            pass

    for p in range(port, port + 30):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit("No free port found.")
    print(f"Progress page:  http://127.0.0.1:{p}/\n(Ctrl+click the link. Stop with Ctrl+C or by closing this terminal.)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ci", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="replace")
    if not git("rev-parse", "--git-dir"):
        sys.exit("This folder is not a git repository. Open the folder you cloned (File > Open Folder).")
    if args.serve:
        return serve(args.port)
    st = status("github-actions" if args.ci else "local")
    if args.json:
        print(json.dumps(st, indent=1))
        return
    if args.ci:
        Path("status.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
        write_summary(st)
    print_table(st)
    if args.ci and st["problems"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
