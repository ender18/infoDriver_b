"""create banks table

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BANKS = [
    ("40133", "ACTINVER"), ("40062", "AFIRME"), ("90721", "ALBO"),
    ("90706", "ARCUS FI"), ("90659", "ASP INTEGRA OPC"), ("40127", "AZTECA"),
    ("37166", "BaBien"), ("40030", "BAJIO"), ("40002", "BANAMEX"),
    ("40154", "BANCO COVALTO"), ("37006", "BANCOMEXT"), ("40137", "BANCOPPEL"),
    ("40160", "BANCO S3"), ("40152", "BANCREA"), ("37019", "BANJERCITO"),
    ("40147", "BANKAOOL"), ("40106", "BANK OF AMERICA"), ("40159", "BANK OF CHINA"),
    ("37009", "BANOBRAS"), ("40072", "BANORTE"), ("40058", "BANREGIO"),
    ("40060", "BANSI"), ("2001", "BANXICO"), ("40129", "BARCLAYS"),
    ("40145", "BBASE"), ("40012", "BBVA MEXICO"), ("40112", "BMONEX"),
    ("90677", "CAJA POP MEXICA"), ("90683", "CAJA TELEFONIST"), ("90715", "CASHI CUENTA"),
    ("90630", "CB INTERCAM"), ("90631", "CI BOLSA"), ("40124", "CITI MEXICO"),
    ("90901", "CLS"), ("90903", "CoDi Valida"), ("40130", "COMPARTAMOS"),
    ("40140", "CONSUBANCO"), ("90725", "COOPDESARROLLO"), ("90652", "CREDICAPITAL"),
    ("90688", "CREDICLUB"), ("90680", "CRISTOBAL COLON"), ("90723", "Cuenca"),
    ("90729", "Dep y Pag Dig"), ("40151", "DONDE"), ("90616", "FINAMEX"),
    ("90634", "FINCOMUN"), ("90734", "FINCO PAY"), ("90738", "FINTOC"),
    ("90699", "FONDEADORA"), ("90685", "FONDO (FIRA)"), ("90601", "GBM"),
    ("40167", "HEY BANCO"), ("37168", "HIPOTECARIA FED"), ("40021", "HSBC"),
    ("40155", "ICBC"), ("40036", "INBURSA"), ("90902", "INDEVAL"),
    ("40150", "INMOBILIARIO"), ("40136", "INTERCAM BANCO"), ("40059", "INVEX"),
    ("40110", "JP MORGAN"), ("40128", "KAPITAL"), ("90661", "KLAR"),
    ("90653", "KUSPIT"), ("90670", "LIBERTAD"), ("90602", "MASARI"),
    ("90722", "Mercado Pago W"), ("90720", "MexPago"), ("40042", "MIFEL"),
    ("40158", "MIZUHO BANK"), ("90600", "MONEXCB"), ("40108", "MUFG"),
    ("40132", "MULTIVA BANCO"), ("37135", "NAFIN"), ("90638", "NU MEXICO"),
    ("90710", "NVIO"), ("40148", "PAGATODO"), ("90732", "Peibo"),
    ("90620", "PROFUTURO"), ("40156", "SABADELL"), ("40014", "SANTANDER"),
    ("40044", "SCOTIABANK"), ("40157", "SHINHAN"), ("90728", "SPIN BY OXXO"),
    ("90646", "STP"), ("90730", "Swap"), ("90703", "TESORED"),
    ("90684", "TRANSFER"), ("90727", "TRANSFER DIRECT"), ("40138", "UALA"),
    ("90656", "UNAGRA"), ("90617", "VALMEX"), ("90605", "VALUE"),
    ("40113", "VE POR MAS"), ("40141", "VOLKSWAGEN"),
]


def upgrade() -> None:
    op.create_table(
        'banks',
        sa.Column('code', sa.String(10),  nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('code'),
    )
    op.bulk_insert(
        sa.table('banks',
                 sa.column('code', sa.String),
                 sa.column('name', sa.String)),
        [{"code": code, "name": name} for code, name in BANKS]
    )


def downgrade() -> None:
    op.drop_table('banks')
