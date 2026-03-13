# План: Система управления профилями в Telegram MiniApp

## Текущее состояние

### Backend (уже реализовано)
- [`config_routes.py`](src/telegram_panel/backend/routes/config_routes.py):
  - `GET /api/config/profiles` — список профилей
  - `GET /api/config/profiles/{name}` — получить профиль
  - `PUT /api/config/profiles/{name}` — создать/обновить профиль
  - `DELETE /api/config/profiles/{name}` — удалить профиль
  - `GET /api/config/symbol-profiles` — получить маппинг символ→профиль
  - `PUT /api/config/symbol-profiles/{symbol}` — назначить профиль символу

### Frontend (уже реализовано)
- [`Settings.tsx`](src/telegram_panel/frontend/src/pages/Settings.tsx):
  - Вкладка "Profiles" — просмотр профилей
  - Вкладка "Symbols" — назначение профилей символам
- [`client.ts`](src/telegram_panel/frontend/src/api/client.ts):
  - API функции: `getProfiles()`, `updateProfile()`, `deleteProfile()`, `setSymbolProfile()`

---

## Требования пользователя

1. **Нельзя изменять базовые настройки стратегии напрямую** — только через профили
2. **Авто-создание профиля**: При изменении настроек стратегии в MiniApp:
   - Автоматически создаётся новый профиль
   - Профиль подключается ко всем символам, которые сейчас используют `default`
   - Последующие изменения применяются к созданному профилю
3. **Отдельное создание профилей**: Пользователь может создавать профили отдельно
4. **Удобный UI/UX**

---

## Предлагаемая архитектура

### 1. Типы данных

```typescript
// src/telegram_panel/frontend/src/api/types.ts

interface Profile {
  name: string;
  _description?: string;
  _version?: string;
  _inherits: string | null;
  _strategy: string | null;  // SCALP, MACDX, HYBRID, etc.
  preset?: Record<string, unknown>;
  position?: Record<string, unknown>;
  signal_rules?: Record<string, unknown>;
  // ... другие секции
}

interface ProfileMetadata {
  name: string;
  isAutoCreated: boolean;  // true если создан автоматически
  createdAt?: string;
  sourceStrategy?: string;
}
```

### 2. API эндпоинты (новые)

```python
# src/telegram_panel/backend/routes/config_routes.py

@router.post("/profiles/{name}/clone")
async def clone_profile(name: str, request: Request, _user: dict = Depends(get_current_user)) -> dict:
    """Клонировать профиль с новым именем."""

@router.post("/profiles/auto-create")
async def auto_create_profile_from_strategy(
    strategy_settings: dict,
    _user: dict = Depends(get_current_user)
) -> dict:
    """
    Авто-создание профиля при изменении настроек стратегии.
    Возвращает имя созданного профиля и список символов, которые были переключены.
    """

@router.get("/profiles/{name}/usage")
async def get_profile_usage(name: str, _user: dict = Depends(get_current_user)) -> dict:
    """Получить список символов, использующих профиль."""
```

### 3. Frontend — Структура страниц

```
Settings Page
├── Strategy Tab (только чтение базовых настроек)
│   └── Кнопка "Create Profile from Current Settings"
├── Profiles Tab (УПРАВЛЕНИЕ ПРОФИЛЯМИ)
│   ├── Список профилей с карточками
│   │   ├── default (заблокирован, только просмотр)
│   │   ├── custom-1 (редактируемый)
│   │   └── auto-created-xxx (авто-созданный)
│   ├── Создание профиля
│   │   ├── "Новый пустой профиль"
│   │   ├── "Клонировать существующий"
│   │   └── "Создать из настроек стратегии" (авто)
│   └── Редактирование профиля (модальное окно)
│       ├── Preset (leverage, atr_sl_mult, etc.)
│       ├── Position (size_percent, etc.)
│       └── Signal Rules (strategy-specific)
└── Symbols Tab
    └── Назначение профилей символам
```

### 4. Логика авто-создания профиля

```mermaid
flowchart TD
    A[Пользователь меняет настройки в Strategy Tab] --> B{Есть ли профиль для редактирования?}
    B -->|Да| C[Применить изменения к текущему профилю]
    B -->|Нет| D[Создать новый профиль]
    D --> E[Имя: auto-{strategy}-{timestamp}]
    E --> F[Найти все символы с профилем 'default']
    F --> G[Переключить их на новый профиль]
    G --> H[Сохранить в active.json]
    C --> I[Показать уведомление]
    H --> I
```

### 5. UI/UX компоненты

#### 5.1 ProfileCard компонент
```tsx
// src/telegram_panel/frontend/src/components/ProfileCard.tsx
interface ProfileCardProps {
  profile: Profile;
  onEdit: () => void;
  onDelete: () => void;
  onClone: () => void;
  isAutoCreated?: boolean;
}
```

#### 5.2 ProfileEditor модальное окно
- Секции: Preset, Position, Signal Rules
- Preview изменений
- Валидация (проверка совместимости со стратегией)

#### 5.3 Auto-create flow
- Modal: "Вы собираетесь изменить базовые настройки"
- Опции:
  - "Создать новый профиль" (ввести имя)
  - "Использовать существующий" (выбрать из списка)
- Preview: какие символы будут переключены

---

## План реализации

### Фаза 1: Бэкенд расширение
- [ ] Добавить эндпоинт `POST /profiles/{name}/clone`
- [ ] Добавить эндпоинт `POST /profiles/auto-create`
- [ ] Добавить эндпоинт `GET /profiles/{name}/usage`
- [ ] Обновить `validate_profile_strategy_match` для проверки при создании

### Фаза 2: Frontend — API клиент
- [ ] Добавить функции: `cloneProfile()`, `autoCreateProfile()`, `getProfileUsage()`
- [ ] Обновить типы в `types.ts`

### Фаза 3: Frontend — UI компоненты
- [ ] Создать `ProfileCard.tsx`
- [ ] Создать `ProfileEditor.tsx` (модальное окно)
- [ ] Обновить `ProfilesTab`:
  - Добавить кнопки создания/клонирования
  - Добавить бейджи для авто-созданных профилей

### Фаза 4: Frontend — Интеграция Strategy Tab
- [ ] Добавить кнопку "Изменить через профиль" в Strategy Tab
- [ ] Реализовать flow авто-создания
- [ ] Показывать уведомление о переключённых символах

### Фаза 5: Тестирование и Polishing
- [ ] Валидация: профиль должен соответствовать стратегии
- [ ] Защита от удаления профиля, используемого символами
- [ ] History/логирование создания профилей

---

## Примеры API

### Авто-создание профиля
```bash
POST /api/config/profiles/auto-create
Body: {
  "name": "my-custom-profile",  # опционально
  "settings": {
    "preset": { "leverage": 10 },
    "position": { "size_percent": 15 }
  },
  "strategy": "SCALP"
}
Response: {
  "profile": "my-custom-profile",
  "switchedSymbols": ["BTCUSDT", "ETHUSDT"],
  "previouslyUsingDefault": true
}
```

### Получить использование профиля
```bash
GET /api/config/profiles/my-profile/usage
Response: {
  "profile": "my-custom-profile",
  "symbols": ["BTCUSDT", "SOLUSDT"],
  "isUsed": true
}
```

---

## Граничные случаи

1. **Профиль уже используется другими символами** — показать предупреждение
2. **Профиль несовместим со стратегией** — валидация с понятной ошибкой
3. **Удаление профиля** — сначала переключить символы на default
4. **Переименование профиля** — обновить все ссылки в active.json
5. **Стратегия меняется в active.json** — профили становятся несовместимы, показать warning

---

## Файлы для изменения

### Backend
- `src/telegram_panel/backend/routes/config_routes.py` — новые эндпоинты

### Frontend
- `src/telegram_panel/frontend/src/api/types.ts` — типы
- `src/telegram_panel/frontend/src/api/client.ts` — API функции
- `src/telegram_panel/frontend/src/components/ProfileCard.tsx` — новый компонент
- `src/telegram_panel/frontend/src/components/ProfileEditor.tsx` — новый компонент
- `src/telegram_panel/frontend/src/pages/Settings.tsx` — обновление UI
