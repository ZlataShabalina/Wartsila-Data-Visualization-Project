# Introduction 
This is a data visualization application, the project’s goal is to visually represent data from a csv file in the beginning and later from a database. The data should be in a form of a tree structure where nodes are parts of a ship’s engine or any other complex object.

This project is being developed using React with typescript to create a user interface, and the backend will be developed using python.

---

# Getting Started

## Git workflow
### Canonical Git Workflow (Feature Branches + PRs into `dev`)

This project uses a **protected `dev` branch**. You **cannot push to `dev` directly**. All changes must go through **feature branches** and **Pull Requests** (PRs).

---

### 0) Make sure local `dev` matches remote

```bash
git fetch origin
git switch dev
git reset --hard origin/dev
```

- This avoids creating new commits on a stale local `dev`.

---

### 1) Create a feature branch from `dev`

```bash
git switch -c feature/my-change
```

> Name your branch clearly, e.g., `feature/db-interface`, `fix/child-node-sorting`.

---

### 2) Work, stage, commit

```bash
git add <files>
git commit -m "Implement XYZ"
```

Repeat as needed.

---

### 3) Push the feature branch

```bash
git push -u origin feature/my-change
```

- `-u` sets upstream so future `git push` is shorter.

---

### 4) Open a Pull Request (PR) into `dev`

- In Azure DevOps: Repos → Branches → your `feature/my-change` → **Create pull request** → Target: **dev**.
- Add a clear title & description.

---

### 5) Keep your branch up to date (rebasing or merging)

Occasionally sync with `origin/dev` to avoid conflicts:

```bash
git fetch origin
git switch feature/my-change

# Option A: rebase (clean history)
git rebase origin/dev
# resolve conflicts if any, then:
git rebase --continue
git push --force-with-lease

# Option B: merge (simpler)
# git merge origin/dev
# git push
```

> Prefer **rebase** for a linear history. Use **--force-with-lease** (safer than --force).

---

### 6) After PR is merged, update local `dev`

```bash
git fetch origin
git switch dev
git reset --hard origin/dev
```

- This makes local `dev` exactly match the remote protected branch.

(Optional) delete the feature branch:

```bash
git branch -d feature/my-change
git push origin --delete feature/my-change
```

---

# Build and Test
TODO: Describe and show how to build your code and run the tests. 
