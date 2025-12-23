# Асинхронный сервис анализа произведений искусства

Это второй сервис на Python (FastAPI), который выполняет отложенный анализ произведений искусства с задержкой 5-10 секунд.

## Описание

Сервис реализует межсервисное взаимодействие с основным Go бэкендом:

1. **Основной Go сервис** вызывает `POST /api/analyze` этого сервиса
2. **Async сервис** выполняет анализ с задержкой 5-10 секунд  
3. **После завершения** результат отправляется обратно в основной сервис через `POST /api/internal/analysis-result`

## Установка и запуск

### Локально (для разработки)

```bash
cd /home/denis/rip/backend/AsyncService

# Создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем сервис
python main.py
```

Сервис будет доступен на `http://localhost:8090`

### Через Docker Compose

```bash
cd /home/denis/rip/backend/ArtAnalysis
docker-compose up -d async-service
```

## API Эндпоинты

### `GET /` - Информация о сервисе
```json
{
  "service": "Art Analysis Async Service",
  "version": "1.0.0",
  "status": "running"
}
```

### `GET /health` - Проверка работоспособности
```json
{"status": "healthy"}
```

### `POST /api/analyze` - Запуск асинхронного анализа

**Запрос:**
```json
{
  "request_id": 1,
  "factor_x": 0.5,
  "factor_y": 0.48,
  "description": "Анализ картины"
}
```

**Ответ (сразу):**
```json
{
  "status": "accepted",
  "request_id": 1,
  "message": "Анализ запущен. Результат будет отправлен в основной сервис через 5-10 секунд."
}
```

### `POST /api/analyze/sync` - Синхронный анализ (для тестирования)

Выполняет тот же анализ, но ждёт результат и возвращает его напрямую.

**Ответ:**
```json
{
  "request_id": 1,
  "success": true,
  "analysis_result": "Отлично сбалансированная композиция",
  "confidence_score": 0.8543,
  "processing_time": 7.23,
  "message": "Анализ успешно завершён"
}
```

## Тестирование через Insomnia/Postman

### 1. Запуск асинхронного анализа (напрямую к async сервису)

```
POST http://localhost:8090/api/analyze
Content-Type: application/json

{
  "request_id": 1,
  "factor_x": 0.5,
  "factor_y": 0.48
}
```

### 2. Синхронный анализ (для отладки)

```
POST http://localhost:8090/api/analyze/sync
Content-Type: application/json

{
  "request_id": 1,
  "factor_x": 0.5,
  "factor_y": 0.48
}
```

### 3. Запуск анализа через основной Go сервис

```
POST http://localhost:8080/api/center_request/1/analyze
Authorization: Bearer <JWT_TOKEN>
```

### 4. Ручное обновление результата с ключом

```
PUT http://localhost:8080/api/internal/analysis-result/1
Content-Type: application/json

{
  "service_key": "a1b2c3d4e5f67890",
  "analysis_result": "Новый результат анализа",
  "confidence_score": 0.95,
  "success": true
}
```

## Псевдо-авторизация

Межсервисное взаимодействие защищено секретным ключом:

- **Ключ:** `a1b2c3d4e5f67890` (8 байт = 16 hex символов)
- Передаётся в поле `service_key` при отправке результата

## Алгоритм анализа

1. Случайная задержка 5-10 секунд (симуляция тяжёлых вычислений)
2. Успех/неуспех определяется случайно (80% успех, 20% неуспех)
3. При успехе вычисляется `confidence_score` на основе:
   - Расстояния от центра (0.5, 0.5)
   - Случайного шума ±15%
4. Текстовый результат зависит от `confidence_score`:
   - `> 0.7` - "Отлично сбалансированная композиция"
   - `> 0.5` - "Хорошая композиция с небольшими отклонениями"
   - `> 0.3` - "Композиция требует корректировки"
   - иначе - "Нестандартная композиция, требуется экспертная оценка"

## Миграция БД

Перед использованием выполните SQL миграцию:

```bash
psql -h localhost -p 5433 -U root -d art_analysis -f build/migrate_async_analysis.sql
```

Или через Adminer: http://localhost:8081

## Файловая структура

```
AsyncService/
├── main.py           # Основной код сервиса
├── requirements.txt  # Python зависимости
├── Dockerfile        # Для сборки Docker образа
└── README.md         # Эта документация
```
