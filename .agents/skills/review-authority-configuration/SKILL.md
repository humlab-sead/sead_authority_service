---
name: review-authority-configuration
description: Review, validate, repair, or author SEAD Authority Service YAML configuration, including runtime settings, entity definitions, prompts, and identity policy.
---

# Review Authority Service Configuration

Use this skill for YAML configuration in `config/`, especially `config/config.yml`, `config/entities.yml`, `config/prompts.yml`, and `config/identity_policy.yml`.

Read the repository root [AGENTS.md](../../../AGENTS.md) first. Check the relevant configuration loader and service code under `src/` before deciding how a field behaves. Use `docs/DEVELOPMENT.md`, `docs/DESIGN.md`, or the SIMS documentation when they cover the affected setting.

## Workflow

1. Identify the exact configuration file and whether the user wants a review, an edit, or both. If the file is ambiguous, ask for its path.
2. Read the raw YAML and the code that loads or consumes the affected fields. Preserve environment placeholders and include directives as written unless the requested change requires editing them.
3. Check the relevant configuration roles: `config/config.yml` contains runtime settings and includes entity definitions and prompts; `config/identity_policy.yml` controls identity behavior. Confirm these roles in current code if they have changed.
4. Check related entity definitions, strategy registrations, identity types, and API behavior only where the setting depends on them. Do not infer deployed values from repository defaults; environment variables and mounted configuration can override them.
5. Use existing targeted validation or tests when the request calls for verification. Do not invent a configuration command. Report any database, model-provider, or other external dependency that prevents a check from running.
6. For a review, report findings without editing files. For a requested repair or authoring task, make the smallest change that matches current code and validate it with available checks.

## Output

Report the affected file, the behavior or validation result, any remaining uncertainty, and the checks performed. Distinguish configuration defaults from effective deployment values.
