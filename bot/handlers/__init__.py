from aiogram import Router

# ================================================
# Импорт всех роутеров модулей
# ================================================
from .commands import router as commands_router
from .agents import router as agents_router  
from .messages import router as messages_router

# ================================================
# Главный роутер, объединяющий все модули
# ================================================
def get_main_router() -> Router:
    """Создает и возвращает главный роутер со всеми обработчиками"""
    main_router = Router()
    
    # Порядок важен - более специфичные обработчики должны быть первыми
    main_router.include_router(commands_router)
    main_router.include_router(agents_router)
    main_router.include_router(messages_router)  # Общий обработчик сообщений должен быть последним
    
    return main_router

# ================================================
# Для обратной совместимости экспортируем router
# ================================================
router = get_main_router()
