# Private Knowledge Library Backup and Recovery

This runbook covers the local SQLite authoring library only. It is not a hosted-service
backup plan, and a successful helper call is not proof of disaster-recovery readiness.

## Security and scope

- The default database is `.local/knowledge.sqlite3`; substitute the actual configured path.
- Backups contain the same private source bodies, notes, and review metadata as the database.
  Treat each backup as a sensitive full copy, including copies made before source-text purging.
- The helpers use SQLite's online backup API and run `PRAGMA integrity_check` on both
  the backup and restored database. The restore source is opened read-only.
- New backup/restore files are created exclusively and use best-effort 0600 file and
  0700 newly-created directory permissions on supported filesystems. Existing directory
  permissions are not changed.
- **Backups are not encrypted.** Store them only on encrypted storage with access controls.
  Do not commit them, attach them to tickets, or place them in shared/synchronized folders
  unless that storage is explicitly approved for the data.
- This procedure does not provide scheduling, off-site replication, retention management,
  ransomware protection, key management, or an RPO/RTO guarantee.

## Create a backup

Use a dedicated private destination directory outside the repository:

```bash
python - <<'PY'
from open_ielts_strategy.knowledge_backup import backup_database

result = backup_database(
    ".local/knowledge.sqlite3",
    "/secure/private-backups/knowledge-2026-11-25.sqlite3",
)
print(result)
PY
```

The helper refuses to overwrite an existing destination. Choose a new filename for each
backup. Keep the output's `integrity: ok` and `encrypted: false` meaning explicit; do not
interpret integrity as encryption or recoverability proof.

## Restore to a new location

Never restore over the active database. Restore into a new private path first:

```bash
python - <<'PY'
from open_ielts_strategy.knowledge_backup import restore_database

result = restore_database(
    "/secure/private-backups/knowledge-2026-11-25.sqlite3",
    "/secure/private-restore-check/knowledge.sqlite3",
)
print(result)
PY
```

Then open the restored database using the application's normal read-only or inspection
commands and verify expected source/card counts and representative records. Keep the
original database untouched until the owner has reviewed the restored copy. Switching an
application to a restored database is a separate, explicit operator action.

## Recovery drill checklist

- [ ] Record the source database path, backup timestamp, and intended recovery point.
- [ ] Confirm the backup is stored on encrypted, access-controlled storage.
- [ ] Restore to a new, empty destination (never overwrite).
- [ ] Confirm both helper results report `integrity: ok`.
- [ ] Open the restored library and inspect expected record counts and selected records.
- [ ] Record elapsed backup/restore/verification time and any data loss relative to the
      chosen recovery point.
- [ ] Obtain owner approval before changing the active database path.
- [ ] Retain or dispose of the old database and backup copies under the applicable policy.

A drill is complete only when the restored data is application-readable and the owner
has confirmed the recovery point. Unit tests and SQLite integrity checks alone do not
establish a measured RPO/RTO or production backup service.
