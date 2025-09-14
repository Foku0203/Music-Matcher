# matcher/management/commands/import_users_csv.py
import csv, uuid
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.db import transaction
from matcher.models import AppUser

def parse_created_at(val):
    if not val:
        return timezone.now()
    dt = parse_datetime(val)
    if dt:
        return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
    d = parse_date(val)
    if d:
        return timezone.make_aware(timezone.datetime(d.year, d.month, d.day))
    return timezone.now()

def norm_status(s):
    s = (s or "").strip().lower()
    return s if s in {"active", "suspended"} else "active"

class Command(BaseCommand):
    help = "Import users from CSV (columns: user_id,email,username,password_hash,status,created_at)"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to CSV file (UTF-8)")
        parser.add_argument("--delimiter", default=",")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        csv_path = opts["csv_path"]; delim = opts["delimiter"]; dry = opts["dry_run"]
        seen = created = updated = 0

        try:
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f, delimiter=delim)
                req = {"email","username","password_hash","status","created_at"}
                if not reader.fieldnames:
                    raise CommandError("CSV ไม่มีหัวคอลัมน์")
                missing = req - set(h.strip() for h in reader.fieldnames)
                if missing:
                    raise CommandError(f"ขาดคอลัมน์: {', '.join(sorted(missing))}")

                for i, row in enumerate(reader, start=2):
                    seen += 1
                    uid_raw = (row.get("user_id") or "").strip()
                    email   = (row.get("email") or "").strip()
                    username= (row.get("username") or "").strip()
                    pwd     = (row.get("password_hash") or "").strip()
                    status  = norm_status(row.get("status"))
                    created_at = parse_created_at(row.get("created_at"))
                    if not email or not username:
                        raise CommandError(f"แถว {i}: ต้องมี email และ username")

                    if uid_raw:
                        try: uid = uuid.UUID(uid_raw)
                        except Exception: raise CommandError(f"แถว {i}: user_id ไม่ใช่ UUID: {uid_raw}")
                        obj, is_created = AppUser.objects.update_or_create(
                            user_id=uid,
                            defaults={"email":email,"username":username,"password_hash":pwd,
                                      "status":status,"created_at":created_at}
                        )
                    else:
                        obj, is_created = AppUser.objects.update_or_create(
                            email=email,
                            defaults={"username":username,"password_hash":pwd,
                                      "status":status,"created_at":created_at}
                        )
                    created += 1 if is_created else 0
                    updated += 0 if is_created else 1

            summary = f"Rows: {seen}\nCreated: {created}\nUpdated: {updated}\n"
            if dry:
                self.stdout.write(self.style.WARNING("[DRY-RUN] ไม่ได้เขียน DB")); self.stdout.write(summary)
                raise transaction.TransactionManagementError("dry-run: rollback")
            else:
                self.stdout.write(self.style.SUCCESS(summary))
        except FileNotFoundError:
            raise CommandError(f"ไม่พบไฟล์: {csv_path}")
