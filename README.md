# Git and GitHub in VS Code: a group tutorial

A 90-minute hands-on exercise for a group of three (members **A**, **B** and **C**), for the EPSS course at IST, University of Lisbon. Together you build a tiny weather-station toolkit, and on the way you meet and solve what usually goes wrong when a group shares code: a rejected push, a conflict, a notebook that no longer opens.

Everything is done from **VS Code** and **github.com**.

## Start here

**Open the guide: <https://foresight-ulisboa.github.io/epss-git-tutorial/>**

It is a checklist: choose your role, tick the steps as you go, and see which checkpoints your group has reached. The same text is in this repository, to read on GitHub or offline:

| Part | Topic | Time |
|---|---|---|
| [0](docs/guide/0-setup.md) | Getting ready: identity, the group repository, clone | 15 min |
| [1](docs/guide/1-warm-up-on-main.md) | Warm-up on `main`: commit, push, pull, a rejected push, a conflict | 25 min |
| [2](docs/guide/2-branches-and-pull-requests.md) | Branches and pull requests: the way groups really work | 30 min |
| [3](docs/guide/3-notebooks.md) | Jupyter notebooks in a group | 12 min |
| [4](docs/guide/4-when-things-go-wrong.md) | When things go wrong: recipes, habits, words | 5 min + reference |

Member A starts by pressing **Use this template** on this page. Do not clone this repository itself.

## What is in here

| Path | What |
|---|---|
| `TEAM.md` | the file you edit in Part 1 |
| `weather/` | three small functions to write, one per member (Part 2) |
| `report.py` | the script that uses the three functions |
| `analysis.ipynb` | the shared notebook (Part 3) |
| `data/station.csv` | one year of synthetic daily weather data |
| `tools/check_progress.py` | checks how far the group is: **Terminal › Run Task… › Tutorial: check progress** |
| `docs/` | the guide |

You need what the course installation guide lists: Anaconda with the `epss` environment, VS Code with the Python and Jupyter extensions, Git, and a GitHub account.
