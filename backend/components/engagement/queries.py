from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from components.engagement.model import PersonaAppearance
from components.engagement.service import _persona_appearance_projection
from components.identity.model import Persona
from components.space.service import _get_account


async def get_my_persona_appearance(db: AsyncSession, viewer_uid):
    account = await _get_account(db, viewer_uid)
    result = await db.execute(
        select(Persona).where(Persona.account_uid == account.uid, Persona.is_primary.is_(True)).limit(1)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        return None
    item = await db.get(PersonaAppearance, persona.uid)
    return _persona_appearance_projection(item, persona.uid)
