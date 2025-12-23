"""
Асинхронный сервис для выполнения отложенного вычисления анализа произведения искусства.
Сервис вызывается из основного Go бэкенда и выполняет расчёт с задержкой 5-10 секунд.
Результат (успех/неуспех + вычисленное значение) отправляется обратно в основной сервис.
"""

import asyncio
import random
import time
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Art Analysis Async Service",
    description="Асинхронный сервис для вычисления анализа произведения искусства",
    version="1.0.0"
)

# Секретный ключ для псевдо-авторизации (8 байт = 16 hex символов)
SERVICE_SECRET_KEY = "a1b2c3d4e5f67890"

# URL основного Go-сервиса (для отправки результатов)
MAIN_SERVICE_URL = "http://localhost:8080"


class AnalysisRequest(BaseModel):
    """Запрос на выполнение асинхронного анализа"""
    request_id: int
    factor_x: Optional[float] = None
    factor_y: Optional[float] = None
    description: Optional[str] = None


class AnalysisResult(BaseModel):
    """Результат асинхронного анализа"""
    request_id: int
    success: bool
    analysis_result: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time: float
    message: str


async def perform_analysis(request: AnalysisRequest) -> AnalysisResult:
    """
    Выполняет асинхронный анализ произведения искусства.
    Симулирует задержку 5-10 секунд и возвращает случайный результат.
    """
    start_time = time.time()
    
    # Случайная задержка от 5 до 10 секунд
    delay = random.uniform(5.0, 10.0)
    await asyncio.sleep(delay)
    
    # Случайный результат: успех (80%) или неуспех (20%)
    success = random.random() < 0.8
    
    if success:
        # Вычисляем "анализ" на основе входных данных
        base_score = 0.5
        
        if request.factor_x is not None and request.factor_y is not None:
            # Вычисляем расстояние от центра (0.5, 0.5)
            dx = request.factor_x - 0.5
            dy = request.factor_y - 0.5
            distance = (dx**2 + dy**2) ** 0.5
            
            # Чем ближе к центру, тем выше оценка
            base_score = max(0.1, 1.0 - distance)
        
        # Добавляем случайный шум
        confidence = min(1.0, max(0.0, base_score + random.uniform(-0.15, 0.15)))
        
        # Определяем результат анализа
        if confidence > 0.7:
            result_text = "Отлично сбалансированная композиция"
        elif confidence > 0.5:
            result_text = "Хорошая композиция с небольшими отклонениями"
        elif confidence > 0.3:
            result_text = "Композиция требует корректировки"
        else:
            result_text = "Нестандартная композиция, требуется экспертная оценка"
        
        return AnalysisResult(
            request_id=request.request_id,
            success=True,
            analysis_result=result_text,
            confidence_score=round(confidence, 4),
            processing_time=round(time.time() - start_time, 2),
            message="Анализ успешно завершён"
        )
    else:
        return AnalysisResult(
            request_id=request.request_id,
            success=False,
            analysis_result=None,
            confidence_score=None,
            processing_time=round(time.time() - start_time, 2),
            message="Не удалось провести анализ: недостаточно данных или ошибка вычислений"
        )


async def send_result_to_main_service(result: AnalysisResult):
    """
    Отправляет результат анализа в основной Go-сервис.
    Использует псевдо-авторизацию с секретным ключом.
    """
    url = f"{MAIN_SERVICE_URL}/api/internal/analysis-result"
    
    payload = {
        "request_id": result.request_id,
        "success": result.success,
        "analysis_result": result.analysis_result,
        "confidence_score": result.confidence_score,
        "processing_time": result.processing_time,
        "message": result.message,
        "service_key": SERVICE_SECRET_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print(f"[OK] Результат для заявки {result.request_id} успешно отправлен в основной сервис")
            else:
                print(f"[ERROR] Ошибка отправки результата: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Не удалось отправить результат в основной сервис: {e}")


async def process_analysis_task(request: AnalysisRequest):
    """
    Фоновая задача: выполняет анализ и отправляет результат.
    """
    print(f"[START] Начинаем анализ для заявки {request.request_id}")
    
    result = await perform_analysis(request)
    
    print(f"[DONE] Анализ для заявки {request.request_id} завершён: success={result.success}")
    
    # Отправляем результат в основной сервис
    await send_result_to_main_service(result)
    
    return result


@app.get("/")
async def root():
    """Корневой эндпоинт - информация о сервисе"""
    return {
        "service": "Art Analysis Async Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Проверка работоспособности сервиса"""
    return {"status": "healthy"}


@app.post("/api/analyze", response_model=dict)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Запускает асинхронный анализ произведения искусства.
    
    Анализ выполняется в фоновом режиме с задержкой 5-10 секунд.
    Результат будет отправлен в основной сервис после завершения.
    
    - **request_id**: ID заявки в основной системе
    - **factor_x**: Координата X композиционного центра
    - **factor_y**: Координата Y композиционного центра
    - **description**: Описание заявки
    """
    if request.request_id <= 0:
        raise HTTPException(status_code=400, detail="Некорректный ID заявки")
    
    # Добавляем задачу в фоновую очередь
    background_tasks.add_task(process_analysis_task, request)
    
    return {
        "status": "accepted",
        "request_id": request.request_id,
        "message": "Анализ запущен. Результат будет отправлен в основной сервис через 5-10 секунд."
    }


@app.post("/api/analyze/sync", response_model=AnalysisResult)
async def analyze_sync(request: AnalysisRequest):
    """
    Синхронный анализ (для тестирования).
    Выполняет анализ и возвращает результат напрямую, без отправки в основной сервис.
    """
    if request.request_id <= 0:
        raise HTTPException(status_code=400, detail="Некорректный ID заявки")
    
    result = await perform_analysis(request)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
