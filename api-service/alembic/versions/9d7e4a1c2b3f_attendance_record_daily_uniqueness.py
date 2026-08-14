"""enforce one attendance record per employee and work date

Revision ID: 9d7e4a1c2b3f
Revises: 4b5c6d7e8f90
Create Date: 2026-07-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d7e4a1c2b3f"
down_revision: Union[str, Sequence[str], None] = "4b5c6d7e8f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DUPLICATE_DETECTION_SQL = """
SELECT employee_id, work_date::date AS work_date, COUNT(*) AS record_count
FROM attendance_records
GROUP BY employee_id, work_date::date
HAVING COUNT(*) > 1
ORDER BY record_count DESC, employee_id, work_date::date
"""


def upgrade() -> None:
    # Do not guess which official attendance record should survive. Operators must
    # review and reconcile duplicates before this migration can proceed.
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                duplicate_group_count bigint;
            BEGIN
                SELECT COUNT(*)
                INTO duplicate_group_count
                FROM (
                    SELECT employee_id, work_date::date
                    FROM attendance_records
                    GROUP BY employee_id, work_date::date
                    HAVING COUNT(*) > 1
                ) AS duplicates;

                IF duplicate_group_count > 0 THEN
                    RAISE EXCEPTION USING
                        MESSAGE = format(
                            'attendance_records contains %s duplicate employee/day group(s)',
                            duplicate_group_count
                        ),
                        HINT = 'Run the duplicate detection query in revision 9d7e4a1c2b3f, reconcile records explicitly, then rerun the migration.';
                END IF;
            END
            $$;
            """
        )
    )

    op.alter_column(
        "attendance_records",
        "work_date",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="work_date::date",
    )
    op.create_unique_constraint(
        "uq_attendance_records_employee_work_date",
        "attendance_records",
        ["employee_id", "work_date"],
    )
    op.create_index(
        "ix_attendance_records_work_date_status",
        "attendance_records",
        ["work_date", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_records_work_date_status",
        table_name="attendance_records",
    )
    op.drop_constraint(
        "uq_attendance_records_employee_work_date",
        "attendance_records",
        type_="unique",
    )
    op.alter_column(
        "attendance_records",
        "work_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="work_date::timestamp without time zone",
    )
