# SEAD Authority Service - Release Checklist

Short operator checklist for deploying or updating a SEAD Authority Service environment. Use it with [OPERATIONS.md](OPERATIONS.md) and the [deployment bundle README](../deployment/container/README.md), which describe the same steps in more detail.

Run every command as the deployment user unless a step names the developer account. Do not run deployment commands as root.

---

## 1. Before you start

- [ ] The image tag you intend to deploy is published to `ghcr.io/humlab-sead/sead_authority_service`.
- [ ] The database schema for that image is deployed. Classifier reconciliation needs `authority.<key>` and `authority.fuzzy_<key>` for every registered classifier key.
- [ ] The mounted `entities.yml` configures every classifier registered by the image tag being deployed (see section 5).
- [ ] You know the previous image tag. That is the rollback target.

Release order is schema, then mounted configuration, then image. An image deployed before its configuration fails startup with a named classifier configuration error.

---

## 2. Host prerequisites

One-time per host.

- [ ] Dedicated non-root Linux account with rootless Podman.
- [ ] GHCR pull access for the deployment account.
- [ ] PostgreSQL reachable from the container. Use `host.docker.internal` when PostgreSQL runs on the deployment host.
- [ ] `pg_trgm` extension available in the target database.
- [ ] Free host port for the instance. The default is `8024`; the application listens on `8000` inside the container. Two environments on one host need distinct ports and separate deployment accounts.
- [ ] TLS terminated at NGINX or another reverse proxy. The service itself serves plain HTTP.

---

## 3. Bundle setup (first deployment or bundle change)

From the developer checkout, if the deployment account can read it:

```bash
deployment/scripts/sync-to-deploy authority-service.sead.se
```

The helper writes `~/container`, removes obsolete bundle files, and preserves `.env`, `config/`, and `logs/`. It installs the systemd user unit but does not enable, restart, or pull anything.

- [ ] Preview an existing deployment first: add `--dry-run`.
- [ ] Review the config comparison in the dry run. Existing mounted config is preserved unless `--sync-config` is supplied.
- [ ] When replacing config, use a checkout at the source revision associated with the image tag; preview with `--dry-run --sync-config` first.
- [ ] Isolated instance: add `--remote-dir container-dev` and pass `DEPLOY_DIR=~/container-dev` to later Makefile commands.

---

## 4. Deployment environment

Edit `~/container/.env` and keep mode `0600`.

- [ ] `SEAD_AUTHORITY_ENVIRONMENT` set to `dev`, `staging`, or `production`.
- [ ] `SEAD_AUTHORITY_IMAGE_TAG` set to the tag being deployed.
- [ ] `SEAD_AUTHORITY_CONTAINER_UID` and `SEAD_AUTHORITY_CONTAINER_GID` set to `id -u` and `id -g` of the deployment account.
- [ ] `SEAD_AUTHORITY_OPTIONS_DATABASE_*` set for the target database.
- [ ] `LLM_PROVIDER` and that provider's settings set when LLM-backed strategies are enabled.
- [ ] `GEONAMES_USERNAME` set when GeoNames lookups are used.
- [ ] No credentials committed to the repository.

---

## 5. Mounted configuration

`~/container/config/` is mounted read-only at `/app/config/`. Verify it before pulling the new image.

- [ ] `config.yml`, `entities.yml`, and `prompts.yml` are present.
- [ ] `identity_policy.yml` is present. `GET /identity/capabilities` and `POST /identity/resolve` fail with `FileNotFoundError` when it is missing.
- [ ] The mounted `entities.yml` sets `reconciliation: simple` for every classifier registered by the image tag being deployed. The current inventory is 45 entries.
- [ ] `options:reconciliation:label_threshold` and `options:reconciliation:description_threshold` in `config.yml` are numbers greater than 0 and at most 1.
- [ ] Only `rdb_code` sets `description_match_weight` above 0.
- [ ] Compare the mounted files with the checkout's single tracked source:

```bash
for f in config.yml entities.yml prompts.yml identity_policy.yml; do
  cmp -s "config/$f" "$HOME/container/config/$f" || echo "differs or missing: $f"
done
```

Any output is either an intentional environment override or drift. Preserve it
by default. Use `sync-to-deploy --sync-config` only when replacing all four
mounted files with the checkout versions. Record intentional overrides in
`~/container/config/OVERRIDES.md`, including the file or key, reason, image tag,
and source commit.

---

## 6. Database schema

Generate and deploy from a checkout:

```bash
schema/create_schema.sh --deploy --schema both --database <db> --host <host> --user <user>
```

- [ ] `create_schema.sh` reports a successful deploy.
- [ ] Match functions exist for the enabled types:

```sql
select to_regprocedure('authority.fuzzy_site(text,integer)');
```

- [ ] The service role can use the schema: `select has_schema_privilege(current_user, 'authority', 'usage');`

---

## 7. Start or update the service

```bash
cd ~/container
make pull
make config      # review locally; the output can contain credentials
```

First deployment:

```bash
make service-install
make service-enable
```

Update of a running deployment:

```bash
make restart
```

---

## 8. Post-deployment verification

- [ ] `make healthcheck` returns `{"status":"alive"}`.
- [ ] `curl -fsS http://localhost:8024/reconcile/readiness?type=site` reports `ready: true`.
- [ ] `GET /reconcile` returns the manifest without an error.
- [ ] `GET /identity/capabilities` returns the configured entity list rather than HTTP 500.
- [ ] `make status` shows the container running.
- [ ] `make logs` and `~/container/logs/` show no startup error.
- [ ] `systemctl --user status sead-authority-service` is active when the unit is installed.

A failing classifier configuration error names the first unconfigured key. Fix the mounted `entities.yml` or the image version; do not work around it by disabling the check.

---

## 9. Rollback

- [ ] Set `SEAD_AUTHORITY_IMAGE_TAG` in `~/container/.env` to the previous tag.
- [ ] Run `make pull`, then `make restart`, then `make healthcheck`.
- [ ] Confirm `GET /reconcile` and `GET /identity/capabilities` respond as before the deployment.

Schema changes are not rolled back by an image rollback. Restore the database schema through the approved database process when a release changed it.

---

## Notes

- Reconciliation results do not depend on any `pg_trgm.*` database setting. Thresholds come from `options:reconciliation` in `config.yml`.
- The image build always uses the selected GitHub ref, never uncommitted local source.
- The image workflow publishes images only. It does not deploy the service.
