"""Add refunds support

Revision ID: 427d55a6fd22
Revises: 5e08deebdb74
Create Date: 2023-02-05 14:16:00.051868

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "427d55a6fd22"
down_revision: str | None = "5e08deebdb74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "refunds",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=36, scale=18), nullable=False),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("wallet_id", sa.Text(), nullable=True),
        sa.Column("invoice_id", sa.Text(), nullable=True),
        sa.Column("payout_id", sa.Text(), nullable=True),
        sa.Column("destination", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name=op.f("refunds_invoice_id_invoices_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["payout_id"], ["payouts.id"], name=op.f("refunds_payout_id_payouts_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("refunds_user_id_users_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
            name=op.f("refunds_wallet_id_wallets_fkey"),
            ondelete="SET NULL",
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("refunds_pkey")),
    )
    op.create_index(op.f("refunds_id_idx"), "refunds", ["id"], unique=False)
    op.create_index(op.f("refunds_invoice_id_idx"), "refunds", ["invoice_id"], unique=False)
    op.create_index(op.f("refunds_payout_id_idx"), "refunds", ["payout_id"], unique=False)
    op.create_index(op.f("refunds_wallet_id_idx"), "refunds", ["wallet_id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("refunds_wallet_id_idx"), table_name="refunds")
    op.drop_index(op.f("refunds_payout_id_idx"), table_name="refunds")
    op.drop_index(op.f("refunds_invoice_id_idx"), table_name="refunds")
    op.drop_index(op.f("refunds_id_idx"), table_name="refunds")
    op.drop_table("refunds")
    # ### end Alembic commands ###
