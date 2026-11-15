# Part 4 · When things go wrong (5 min, then keep for reference)

Read the first recipe together now. Keep the rest for the day you need it.

Before anything else, two questions tell you where you are: **which branch?** (bottom-left corner) and **what changed?** (Source Control view). The task **Tutorial: check progress** answers both.

## Recipes

**I committed on `main` by mistake, and the push is refused** (*protected branch*, or *changes must be made through a pull request*)

1. Click `main` in the bottom-left corner, **Create new branch…**, give it a name. Your commit comes with you.
2. **Publish Branch**, then open a pull request as usual.
3. Put your local `main` back in line with GitHub: switch to `main`, open a terminal and type `git reset --hard origin/main`.

**I want to undo my last commit** (not pushed yet)

**`···` › Commit › Undo Last Commit**. The commit disappears; its changes are back under Staged Changes.

**A merged pull request broke `main`**

Open that pull request on GitHub and click **Revert**. It creates a new pull request that undoes it. Nothing is erased from the history.

**I am in the middle of a merge and lost**

**Ctrl+Shift+P**, `Git: Abort Merge`. Everything is as before the merge.

**VS Code will not switch branch or pull: "your local changes would be overwritten"**

You have changes that are not committed. Commit them. Or park them: **`···` › Stash › Stash**, and later **`···` › Stash › Pop Stash**.

**Pull says "need to specify how to reconcile divergent branches"**

The third line of step 0.1 is missing on this computer: `git config --global pull.rebase false`.

**Push is refused with 403 or asks me to sign in again**

You are signed in with another GitHub account, or you never accepted the invitation to the repository.

**Some commits show a grey face on GitHub instead of my picture**

The email in `git config --global user.email` is not one of the emails of your GitHub account. Fix it (step 0.1); new commits will be linked.

**Nothing works any more** (the last resort, which always works)

Everything you pushed is safe on GitHub. Rename your folder (for example add `-broken`), clone again (step 0.3), and copy over any file you had not committed. Keep the broken folder until the end of the day.

**Never**

Do not use `git push --force` on a branch you share. It erases your teammates' work on GitHub. If something seems to need it, ask first.

## Five habits

1. **Pull before you start, push before you stop.**
2. **One task, one branch, one pull request.** `main` always works.
3. **Read the diff before every commit.**
4. **Small commits, with a message that says what and why.**
5. **Notebooks: one owner at a time, outputs cleared.**

## Words

| Word | Meaning |
|---|---|
| repository (repo) | the project folder with its whole history |
| commit | a saved snapshot, with an author, a date and a message |
| stage | choose which changes go into the next commit |
| push / pull | send your commits to GitHub / bring the others' commits to you |
| clone | copy a repository from GitHub to your computer, once |
| branch | a separate line of commits; `main` is the shared one |
| merge | combine two lines of commits |
| conflict | both sides changed the same lines; people decide the result |
| pull request (PR) | a GitHub page proposing to merge a branch into `main` |
| review | a teammate reads the pull request and approves it |
| origin | the name Git gives to the repository on GitHub |

## For your real project

Do the same, for real: one person creates the repository and invites the others (0.2), protects `main` (2.1), and from then on everybody works as in Part 2. A branch called `tutorial-status` exists in this practice repository: it belongs to the progress check, and you can ignore it.
