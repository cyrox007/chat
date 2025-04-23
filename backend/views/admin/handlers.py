import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from components.device.model import UserDevice
from utils.file_handler import save_file
from components.room.model import Room
from utils.logger import setup_logger
from components.user.model import Penalty, User
from components.message.model import Message
from components.decorators.db import get_session

from datetime import datetime
from uuid import UUID

from sqlalchemy import String, func, select, and_, extract
from datetime import datetime, timedelta

from socket_manager import private_manager, room_manager

logger = setup_logger(__name__)



async def get_dashboard_stats(db_session):
    """Сбор статистики из БД и веб-сокетов"""
    
    # 1. Основные счетчики (асинхронные запросы)
    total_users = await db_session.scalar(
        select(func.count(User.id)).where(User.deleted_at == None)
    )
    
    today = datetime.utcnow().date()
    new_today = await db_session.scalar(
        select(func.count(User.id)).where(
            and_(
                User.created_at >= today,
                User.deleted_at == None
            )
        )
    )
    
    total_rooms = await db_session.scalar(
        select(func.count(Room.id)).where(Room.is_active == True)
    )
    
    # 2. Статистика по полу (из профилей)
    gender_stats = await db_session.execute(
        select(
            User.gender,
            func.count(User.id)
        )
        .where(User.gender != None)
        .group_by(User.gender)
    )
    gender_data = [{"gender": g, "count": c} for g, c in gender_stats]
    
    # 3. География (города/страны)
    geo_stats = await db_session.execute(
        select(
            User.country,
            User.city,
            func.count(User.id)
        )
        .where(and_(
            User.country != None,
            User.deleted_at == None
        ))
        .group_by(User.country, User.city)
        .order_by(func.count(User.id).desc())
        .limit(20)
    )
    geo_data = [{
        "country": country, 
        "city": city, 
        "count": count
    } for country, city, count in geo_stats]
    
    # 4. Устройства (из UserDevice)
    device_stats = await db_session.execute(
        select(
            func.coalesce(
                # Просто используем device_info как строку, если он не JSON
                func.cast(UserDevice.device_info, String),
                func.substring(UserDevice.user_agent, 1, 50)
            ).label('device_name'),
            func.count(UserDevice.id)
        )
        .where(UserDevice.is_active == True)
        .group_by('device_name')
        .order_by(func.count(UserDevice.id).desc())
        .limit(20)
    )
    devices_data = [{
        "device": device_name if device_name else "Unknown",
        "count": count
    } for device_name, count in device_stats]

    # 4.1. Распределение по типам устройств
    # Поскольку у нас в данных только "Other", упрощаем запрос
    device_type_stats = await db_session.execute(
        select(
            func.coalesce(
                func.cast("other", String),  # Используем строковый литерал
                func.cast("unknown", String)
            ).label('device_type'),
            func.count(UserDevice.id)
        )
        .where(UserDevice.is_active == True)
        .group_by('device_type')
    )
    device_types_data = [{
        "type": "Other",  # Приводим к читаемому виду
        "count": count
    } for device_type, count in device_type_stats]
    
    # 4.2. Активные устройства (по последним подключениям)
    active_devices_last_hour = await db_session.scalar(
        select(func.count(UserDevice.id))
        .where(and_(
            UserDevice.is_active == True,
            UserDevice.expires_at >= datetime.utcnow()
        ))
    )
    
    # 5. Активность по часам (последние 24 часа)
    hours_ago = datetime.utcnow() - timedelta(hours=24)
    activity_by_hour = await db_session.execute(
        select(
            extract('hour', User.last_online),
            func.count(User.id)
        )
        .where(User.last_online >= hours_ago)
        .group_by(extract('hour', User.last_online))
    )
    activity_data = [{
        "hour": int(hour), 
        "count": count
    } for hour, count in activity_by_hour]

    # 6. Популярные комнаты (комбинированный рейтинг)
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Получаем базовую статистику по комнатам из БД
    room_stats = await db_session.execute(
        select(
            Room.id,
            Room.name,
            func.count(Message.uid).label('messages_count'),
            func.max(Message.created_at).label('last_message_time')
        )
        .join(Message, Message.room_uid == Room.uid)
        .where(Message.created_at >= week_ago)
        .group_by(Room.id)
    )
    
    # Преобразуем в словарь для удобства
    room_stats_dict = {
        room_id: {
            "name": name,
            "messages_count": messages_count,
            "last_message_time": last_message_time
        }
        for room_id, name, messages_count, last_message_time in room_stats
    }
    
    # Получаем текущие подключения из менеджера WebSocket
    active_rooms = {}
    for room_uid, connections in room_manager.room_connections.items():
        active_users = len({user_id for _, user_id in connections})
        if room_uid in room_stats_dict:
            active_rooms[room_uid] = {
                **room_stats_dict[room_uid],
                "active_users": active_users
            }
    
    # Вычисляем рейтинг популярности для каждой комнаты
    popular_rooms = []
    for room_uid, stats in active_rooms.items():
        # Коэффициент активности (сообщения за неделю)
        activity_score = min(stats["messages_count"] / 10, 10)  # Нормализуем
        
        # Коэффициент "свежести" (0-1, где 1 = сообщение было только что)
        freshness_score = 0
        if stats["last_message_time"]:
            hours_since_last = (datetime.utcnow() - stats["last_message_time"]).total_seconds() / 3600
            freshness_score = 1 / (1 + hours_since_last / 24)  # Полураспад за 24 часа
        
        # Коэффициент онлайн-участников
        online_score = min(stats["active_users"] / 5, 5)  # Нормализуем
        
        # Общий рейтинг (можно регулировать веса)
        popularity_score = 0.5 * activity_score + 0.3 * online_score + 0.2 * freshness_score
        
        popular_rooms.append({
            "id": room_uid,
            "name": stats["name"],
            "popularity_score": round(popularity_score, 2),
            "active_users": stats["active_users"],
            "messages_last_week": stats["messages_count"],
            "last_activity": stats["last_message_time"].isoformat() if stats["last_message_time"] else None
        })
    
    # Сортируем по рейтингу
    popular_rooms_sorted = sorted(popular_rooms, key=lambda x: x["popularity_score"], reverse=True)[:5]
    
    # 7. Последние зарегистрированные
    recent_users = await db_session.execute(
        select(User)
        .where(User.deleted_at == None)
        .order_by(User.created_at.desc())
        .limit(5)
    )
    recent_users_data = [{
        "id": u.id,
        "username": u.username,
        "created_at": u.created_at.isoformat()
    } for u in recent_users.scalars()]
    
    # 8. Онлайн пользователи (из веб-сокетов)
    online_users = private_manager.online_users_count
    
    return {
        "total_users": total_users,
        "online_users": online_users,
        "active_rooms": total_rooms,
        "new_today": new_today,
        "gender_stats": gender_data,
        "geo_stats": geo_data,
        "devices_stats": {
            "by_model": devices_data,
            "by_type": device_types_data,
            "active_now": active_devices_last_hour
        },
        "activity_stats": activity_data,
        "popular_rooms": popular_rooms_sorted,
        "recent_users": recent_users_data
    }

@get_session
async def dashboard_stats(db_session = None):
    """
    Получение статистики для админ-панели
    """
    stats = await get_dashboard_stats(db_session)
    return {
        'status': 'ok',
        'stats': {
            "total_users": stats.get("total_users", 0),
            "online_users": stats.get("online_users", 0),
            "active_rooms": stats.get("active_rooms", 0),
            "new_today": stats.get("new_today", 0),
            "gender_data": stats.get("gender_stats", []),
            "geo_data": stats.get("geo_stats", []),
            "devices_data": stats.get("devices_stats", {}),
            "activity_data": stats.get("activity_stats", []),
            "popular_rooms": stats.get("popular_rooms", []),
            "recent_users": stats.get("recent_users", [])
        }
    }

@get_session
async def assign_penalty(request: Request, response: Response, db_session=None):
    """
    Назначение наказания пользователю.
    """
    try:
        # Извлекаем данные из запроса
        try:
            data: dict = await request.json()
            user_uid = data.get("user_uid")
            penalty_type = data.get("penalty_type")
            expires_at = data.get("expires_at")
            reason = data.get("reason")
        except json.JSONDecodeError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Invalid JSON data"
            }

        # Проверяем, что все необходимые поля присутствуют
        if not all([user_uid, penalty_type, expires_at]):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Недостаточно данных для назначения наказания",
                'details': {
                    'required_fields': ['user_uid', 'penalty_type', 'expires_at']
                }
            }

        # Проверяем, существует ли пользователь
        try:
            user = await User.get_user_by_uid(db_session, user_uid)
            if not user:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    'status': 'error',
                    'message': "Пользователь не найден"
                }
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Некорректный формат user_uid"
            }

        # Преобразуем expires_at в datetime
        try:
            expires_at_datetime = datetime.fromisoformat(expires_at)

            # Проверяем, что временная зона указана как UTC (+00:00 или Z)
            if expires_at_datetime.tzinfo is None:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Требуется указать временную зону UTC",
                    'details': {
                        'expected_format': "YYYY-MM-DDTHH:MM:SS+00:00 или YYYY-MM-DDTHH:MM:SSZ"
                    }
                }

            # Приводим к UTC явно (на случай если указана другая зона)
            expires_at_utc = expires_at_datetime.astimezone(timezone.utc)
            
            # Проверяем что время действительно в UTC
            if expires_at_utc.tzinfo != timezone.utc:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Время должно быть в формате UTC",
                    'details': {
                        'received_timezone': str(expires_at_datetime.tzinfo)
                    }
                }

            # Сравниваем с текущим UTC временем
            now_utc = datetime.now(timezone.utc)

            if expires_at_utc <= now_utc:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Дата окончания должна быть в будущем",
                    'details': {
                        'current_time_utc': now_utc.isoformat(),
                        'provided_expires_at': expires_at_utc.isoformat()
                    }
                }
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Некорректный формат даты",
                'details': {
                    'expected_format': "YYYY-MM-DDTHH:MM:SS"
                }
            }
        
        # Создаем запись о наказании
        penalty = await Penalty.create_penalty(
            db_session=db_session,
            user_uid=user.uid,
            penalty_type=penalty_type,
            expires_at=expires_at_datetime,
            issuer_uid=request.state.user['user_uid'],
            reason=reason,
        )

        return {
            "status": "ok",
            "message": "Наказание успешно назначено",
            "data": {
                "penalty_id": penalty.id,
                "user_uid": str(penalty.user_uid),
                "penalty_type": penalty.penalty_type.value,
                "issued_at": penalty.issued_at.isoformat(),
                "expires_at": penalty.expires_at.isoformat(),
                "issuer_uid": str(penalty.issuer_uid),
                "reason": penalty.reason,
            }
        }

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(f"Неожиданная ошибка при назначении наказания: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': "Internal server error"
        }

@get_session
async def delete_penalty(penalty_id: int, response: Response, db_session = None):
    try:
        response_data = await Penalty.delete_penalty(db_session, penalty_id)
        return response_data
    except HTTPException:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': 'error', 'message': 'Неожиданная ошибка'}

@get_session
async def get_users(
    response: Response, 
    db_session = None,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    role_filter: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None
):
    """ Получение списка пользователей с пагинацией, фильтрацией и сортировкой """
    try:
        users_data = await User.get_users(
            db_session=db_session,
            page=page,
            per_page=per_page,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            role_filter=role_filter,
            is_active=is_active,
            is_verified=is_verified
        )

        return {
            "status": "ok",
            "users": users_data['data'],
            "meta": {
                "total": users_data['meta']['total'],
                "page": page,
                "per_page": per_page,
                "total_pages": (users_data['meta']['total'] + per_page - 1) // per_page,
                "sort_by": sort_by,
                "sort_dir": sort_dir
            }
        }
    except Exception as e:
        logger.error(f"Error in get_users: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": "error",
            "message": "Произошла ошибка при получении списка пользователей",
            "details": str(e)
        }
    #response.status_code = status.HTTP_200_OK #иной статус код в случае ошибок {'status': 'error', 'message': 'Произошла какая-то ошибка'}
    return {'status': 'ok', 'users': []}

@get_session
async def get_user_rooms(target_uid: UUID, db_session = None):
    rooms = await Room.get_rooms_by_owner(
        db=db_session,
        owner_uid=target_uid
    )

    return {'status': 'ok', "rooms": rooms}

@get_session
async def get_user_penalties(target_uid: UUID, db_session = None):
    penalties = await Penalty.get_user_penalties(
        db_session=db_session,
        user_uid=target_uid
    )

    return {'status': 'ok', "penalties": penalties}

@get_session
async def update_user(target_uid: UUID, request: Request, response: Response, db_session=None):
    try:
        try:
            data = await request.json()
            user_data = data.get('data', {})
            if not user_data:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': 'Отсутствуют данные для обновления'
                }
        except json.JSONDecodeError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status':'error',
                'message': "Invalid JSON data",
            }

        # Проверка существования пользователя
        user = await User.get_user_by_uid(db_session, target_uid)
        if not user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {
                'status': 'error', 
                'message': "Пользователь не найден",
            }
        
        # Обработка аватара, если он передан
        if 'avatar' in user_data and user_data['avatar']:
            try:
                # Сохраняем файл через утилиту save_file
                avatar_url = save_file(user_data['avatar'])
                user_data['avatar'] = avatar_url  # Заменяем Base64 на URL аватара
            except HTTPException as e:
                response.status_code = e.status_code
                return {
                    'status': 'error',
                    'message': e.detail,
                }

        # Обновление профиля
        updated_user = await User.update_profile(
            db_session=db_session,
            user_uid=target_uid,
            new_data=user_data
        )

        return {
            'status': 'ok',
            "user_uid": str(target_uid),
            "user": updated_user
        }

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(
            f"Ошибка при обновлении пользователя: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': "Ошибка при обновлении данных пользователя",   
        }