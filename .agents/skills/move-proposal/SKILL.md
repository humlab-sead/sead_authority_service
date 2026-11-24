---
name: move-proposal
description: Move a proposal file or topic folder under docs/proposals, updating affected index entries and relative links. Use when asked to move, archive, defer, shelve, or group a proposal. Do not use for creating, reviewing, or implementing proposals.
---

# Move a Proposal

Move one proposal file or topic folder within `docs/proposals/`, keep affected links and index entries valid, and verify the result.

## Resolve the move

- Use an explicit source and destination supplied by the user or current conversation.
- For a status request without a destination, inspect the target's existing proposal layout and choose a matching location only when it is clear. Ask one concise question when it is not.
- Preserve a file or folder's shape unless the user asks to group a standalone file.
- Treat user-supplied paths as exact. If both `<TOPIC>.md` and `<TOPIC>/` exist, identify which one the request means before moving either.
- Check `git status --short` before editing and leave unrelated changes untouched.

## Move and update links

1. Read the source document's status and outbound Markdown links. Search for inbound links by its old path and topic name, and identify the nearest README that lists or tracks it. Do not assume every proposal belongs only in `docs/proposals/README.md`.
2. Move the requested file or folder, preserving repository history when practical.
3. Update relative links inside moved documents based on the new directory depth. Update links and backticked paths in other documents that point to the old location. Change an index entry only if it lists the moved item.
4. Use the destination repository's existing index format. Do not add status tables or rows that are not part of its current format.
5. Do not rewrite proposal content beyond link changes and a status update explicitly requested by the user. Do not invent completion, validation, branch, or PR details.

## Verify

Run the bundled checker on the moved Markdown files when relative links changed:

```bash
bash .agents/skills/move-proposal/scripts/check_relative_links.sh <MOVED_FILES>
```

Then confirm the old path is gone and inspect `git status --short`. Leave changes unstaged and uncommitted unless the user asks for staging or a commit. Report the destination, changed links or index entries, and checker result.

## Limits

- Move only the requested proposal file or folder and the related link, index, and status text changes.
- Do not create a new proposal or reorganize unrelated proposal documents.
- Do not follow external links or infer that linked GitHub work is complete.
- If repository instructions conflict with the requested move, report the specific conflict and path.
