# Semantic Release for Python Projects

This project uses semantic-release for automated versioning and releases, configured for Python projects.

## How It Works

When you push to the `main` branch, the GitHub Actions workflow:

1. **Analyzes commits** since the last release using conventional commit messages
2. **Determines the next version** based on commit types:
   - `fix:` → patch version (0.1.0 → 0.1.1)
   - `feat:` → minor version (0.1.0 → 0.2.0)
   - `BREAKING CHANGE:` → major version (0.1.0 → 1.0.0)
3. **Updates version** in `pyproject.toml`
4. **Generates CHANGELOG.md** with all changes
5. **Creates a git tag** and GitHub release
6. **Commits changes** back to the repository

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Common Types

- `feat:` - A new feature (minor version bump)
- `fix:` - A bug fix (patch version bump)
- `docs:` - Documentation changes (patch version bump)
- `style:` - Code style changes (formatting, missing semicolons, etc.) (patch version bump)
- `refactor:` - Code refactoring (patch version bump)
- `perf:` - Performance improvements (patch version bump)
- `test:` - Adding or updating tests (no version bump)
- `chore:` - Maintenance tasks (no version bump)
- `ci:` - CI/CD changes (no version bump)
- `build:` - Build system changes (no version bump)

### Examples

**Patch Release (0.1.0 → 0.1.1):**
```bash
git commit -m "fix: correct database connection timeout"
git commit -m "docs: update README with deployment instructions"
git commit -m "refactor: simplify reconciliation strategy"
```

**Minor Release (0.1.0 → 0.2.0):**
```bash
git commit -m "feat: add support for GeoNames reconciliation"
git commit -m "feat(api): implement batch reconciliation endpoint"
```

**Major Release (0.1.0 → 1.0.0):**
```bash
git commit -m "feat!: redesign API with breaking changes

BREAKING CHANGE: The reconciliation endpoint now requires authentication.
All previous API calls must be updated to include an API key."
```

Or:
```bash
git commit -m "feat: redesign API

BREAKING CHANGE: The reconciliation endpoint now requires authentication."
```

## Configuration

The semantic-release configuration is in `.releaserc.json`:

```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",  // Analyzes commits
    "@semantic-release/release-notes-generator",  // Generates release notes
    "@semantic-release/changelog",  // Updates CHANGELOG.md
    "@semantic-release/exec",  // Updates pyproject.toml version
    "@semantic-release/git",  // Commits changes back
    "@semantic-release/github"  // Creates GitHub release
  ]
}
```

### Key Plugin: @semantic-release/exec

Since this is a Python project (not Node.js), we use `@semantic-release/exec` to update the version in `pyproject.toml`:

```json
{
  "prepareCmd": "sed -i 's/^version = \".*\"/version = \"${nextRelease.version}\"/' pyproject.toml"
}
```

This replaces the version line in `pyproject.toml` with the new version.

## Workflow

### Standard Development Flow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/add-new-strategy
   ```

2. **Make changes and commit with conventional commit messages:**
   ```bash
   git add .
   git commit -m "feat: add new reconciliation strategy for species"
   ```

3. **Push to GitHub and create PR:**
   ```bash
   git push origin feature/add-new-strategy
   # Create PR on GitHub
   ```

4. **Merge PR to main:**
   - Use "Squash and merge" or "Rebase and merge"
   - Ensure the commit message follows conventional format
   - The semantic-release workflow will automatically run

5. **Automatic release:**
   - semantic-release analyzes commits
   - Creates new version tag
   - Updates `pyproject.toml` and `CHANGELOG.md`
   - Creates GitHub release with notes

### Manual Release Trigger

You can also trigger releases manually:

1. Go to GitHub Actions: `https://github.com/humlab-sead/sead_authority_service/actions`
2. Select "Release" workflow
3. Click "Run workflow"
4. Select branch (usually `main`)
5. Click "Run workflow"

## Troubleshooting

### No Release Created

**Problem:** Pushed to main but no release was created.

**Causes:**
- No commits with release-triggering types (`feat`, `fix`, etc.)
- Only commits with `chore`, `ci`, `test`, `build` types
- No changes since last release

**Solution:**
- Check commit messages follow conventional format
- Ensure at least one commit has `feat:`, `fix:`, or breaking change

### Version Not Updated in pyproject.toml

**Problem:** Release created but version in `pyproject.toml` not updated.

**Causes:**
- `sed` command syntax error
- File encoding issues
- Git configuration preventing commits

**Solution:**
- Check workflow logs for errors
- Verify `pyproject.toml` format: `version = "x.y.z"`
- Ensure GitHub Actions has write permissions

### ENOPKG Error (Missing package.json)

**Problem:** Error about missing `package.json` file.

**Causes:**
- `@semantic-release/npm` plugin is included
- Default semantic-release configuration tries to publish to npm

**Solution:**
- Ensure `.releaserc.json` exists and doesn't include `@semantic-release/npm`
- Our configuration uses `@semantic-release/exec` instead for Python projects

### Authentication Errors

**Problem:** GitHub API authentication fails.

**Causes:**
- `GITHUB_TOKEN` not set
- Insufficient permissions

**Solution:**
```yaml
- name: Run semantic-release
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Fallback
  run: semantic-release
```

## Best Practices

### 1. Write Good Commit Messages

**Bad:**
```bash
git commit -m "updated stuff"
git commit -m "fix"
git commit -m "changes"
```

**Good:**
```bash
git commit -m "feat(api): add batch reconciliation endpoint"
git commit -m "fix(database): resolve connection pool timeout"
git commit -m "docs: update Docker deployment guide"
```

### 2. Use Scopes for Clarity

Scopes help organize changes:
```bash
git commit -m "feat(geonames): add support for alternate names"
git commit -m "fix(api): correct error handling in reconciliation"
git commit -m "refactor(database): optimize query performance"
git commit -m "docs(deployment): add CI/CD documentation"
```

### 3. Include Body and Footer When Needed

For complex changes:
```bash
git commit -m "feat(llm): add support for Claude API

This adds support for Anthropic's Claude models as an alternative
to OpenAI. Configuration is done through environment variables.

Closes #42"
```

### 4. Mark Breaking Changes Clearly

Always use `BREAKING CHANGE:` in footer for major versions:
```bash
git commit -m "refactor(api)!: redesign reconciliation response format

BREAKING CHANGE: The reconciliation response now uses a different
JSON structure. All API clients must be updated."
```

### 5. Squash Feature Branch Commits

When merging PRs, squash commits and write a good final message:
```bash
# Instead of:
- WIP: start feature
- fix typo
- more changes
- fix tests

# Squash to:
feat(auth): implement API key authentication

Added support for API key authentication with configurable
key storage and validation.

Closes #123
```

## Testing Locally

To test semantic-release locally without creating a release:

```bash
# Install semantic-release CLI
npm install -g semantic-release \
  @semantic-release/commit-analyzer \
  @semantic-release/release-notes-generator \
  @semantic-release/changelog \
  @semantic-release/git \
  @semantic-release/github \
  @semantic-release/exec

# Run in dry-run mode
semantic-release --dry-run
```

This will show what version would be created without actually creating it.

## Release History

Releases are visible in:
- **GitHub Releases:** https://github.com/humlab-sead/sead_authority_service/releases
- **CHANGELOG.md:** In the repository root
- **Git Tags:** `git tag -l`

## CI/CD Integration

The semantic-release workflow integrates with the Docker build workflow:

1. semantic-release creates a new version tag (e.g., `v1.2.3`)
2. Git tag push triggers the Docker build workflow
3. Docker images are built and pushed to GHCR with version tags
4. Production can deploy the new versioned image

See [DEPLOYMENT.md](DEPLOYMENT.md) for details on the complete CI/CD pipeline.

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [semantic-release Documentation](https://semantic-release.gitbook.io/)
- [Commit Analyzer Rules](https://github.com/semantic-release/commit-analyzer#releaserules)
