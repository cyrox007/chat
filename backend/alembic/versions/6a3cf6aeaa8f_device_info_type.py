"""device info type

Revision ID: 6a3cf6aeaa8f
Revises: 314c52922982
Create Date: 2025-04-23 21:41:44.198298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6a3cf6aeaa8f'
down_revision: Union[str, None] = '314c52922982'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Добавляем временный столбец
    op.add_column('user_devices',
                 sa.Column('device_info_temp', postgresql.JSONB(astext_type=sa.Text()),
                 nullable=True))
    
    # 2. Преобразуем данные с обработкой простых строк
    op.execute('''
        UPDATE user_devices 
        SET device_info_temp = 
            CASE 
                WHEN device_info IS NULL THEN NULL
                WHEN device_info = '' THEN NULL
                WHEN device_info ~ '^\{.*\}$' THEN device_info::jsonb  
                ELSE jsonb_build_object('value', device_info)  
            END
    ''')
    
    # 3. Удаляем старый столбец
    op.drop_column('user_devices', 'device_info')
    
    # 4. Переименовываем временный столбец
    op.alter_column('user_devices', 'device_info_temp', 
                    new_column_name='device_info')

def downgrade() -> None:
    # 1. Добавляем временный столбец VARCHAR
    op.add_column('user_devices',
                 sa.Column('device_info_temp', sa.VARCHAR()),
                 nullable=True)
    
    # 2. Преобразуем данные обратно
    op.execute('''
        UPDATE user_devices 
        SET device_info_temp = 
            CASE 
                WHEN device_info IS NULL THEN NULL
                WHEN jsonb_typeof(device_info) = 'object' AND device_info::text != '{}' THEN device_info::text
                ELSE NULL  # Или можно извлечь значение из {"value": "строка"}
            END
    ''')
    
    # 3. Удаляем JSONB столбец
    op.drop_column('user_devices', 'device_info')
    
    # 4. Переименовываем временный столбец
    op.alter_column('user_devices', 'device_info_temp', 
                    new_column_name='device_info')