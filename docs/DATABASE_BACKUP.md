# Database Backup and Recovery Procedure

This application uses SQLite with WAL/standard mode. Because the application runs on a local workstation and collects personal identification information (NIC, Passport, Mobile numbers), backups must be performed regularly, securely, and without causing write contention.

---

## 1. Automated Online Backup (Recommended)

The backend provides a dedicated online backup utility in [`backend/app/core/backup.py`](file:///d:/UniKey/registration-card-scanner/backend/app/core/backup.py) that leverages SQLite's official online backup API (`sqlite3.Connection.backup`).

### Why use online backup?
- **Zero Lock Contention**: Backs up active databases cleanly even while card registration records or imports are being processed.
- **Atomic & Consistent**: Produces an exact point-in-time snapshot.
- **Safe from File Corruption**: Never copies a partial or torn database page.

### Command to Create a Backup

Run from the `backend/` directory:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.core.backup --action backup
```

Snapshots are timestamped and saved into `backend/data/backups/`:
`backend/data/backups/app_backup_YYYYMMDD_HHMMSS.db`

You can also specify a custom output directory:

```powershell
python -m app.core.backup --action backup --file "D:\Backups\Events"
```

---

## 2. Restore Procedure

To restore from a backup snapshot:

1. **Stop the backend server** (or stop any running uvicorn instance):
   ```powershell
   # Ctrl+C in terminal
   ```
2. **Execute restore command**:
   ```powershell
   cd backend
   .venv\Scripts\Activate.ps1
   python -m app.core.backup --action restore --file "data/backups/app_backup_YYYYMMDD_HHMMSS.db"
   ```
3. **Restart the server**:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## 3. Scheduled Automated Backups (Windows Task Scheduler)

For production/office event use, schedule automated daily backups using Windows Task Scheduler:

1. Open PowerShell as Administrator.
2. Register a daily task at 18:00 (end of day):
   ```powershell
   $Action = New-ScheduledTaskAction -Execute "D:\UniKey\registration-card-scanner\backend\.venv\Scripts\python.exe" -Argument "-m app.core.backup --action backup" -WorkingDirectory "D:\UniKey\registration-card-scanner\backend"
   $Trigger = New-ScheduledTaskTrigger -Daily -At 6pm
   Register-ScheduledTask -TaskName "CardScanner_DailyDbBackup" -Action $Action -Trigger $Trigger -Description "Daily snapshot of Registration Card Scanner SQLite DB"
   ```

---

## 4. Manual Fallback Copy

If Python is inaccessible, ensure uvicorn is stopped, then copy `backend/data/db/app.db` (and any `app.db-wal` / `app.db-shm` files if present) directly to your secure storage drive.
