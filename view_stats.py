#!/usr/bin/env python3
"""Скрипт для просмотра статистики использования агента."""

from core.logger import logger

def main():
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ИСПОЛЬЗОВАНИЯ АГЕНТА")
    print("="*60 + "\n")
    
    stats = logger.get_stats()
    
    if stats[0] == 0:
        print("Пока нет данных. Отправьте несколько запросов боту.")
        return
    
    total_requests, avg_iterations, avg_duration, total_cost = stats
    
    print(f"📈 Общая статистика:")
    print(f"   • Всего запросов: {total_requests}")
    print(f"   • Среднее количество итераций: {avg_iterations:.2f}")
    print(f"   • Среднее время выполнения: {avg_duration:.2f} сек")
    print(f"   • Общая стоимость: {total_cost:.4f} руб")
    print(f"   • Средняя стоимость запроса: {total_cost/total_requests:.4f} руб")
    
    print("\n" + "="*60)
    print("📝 ПОСЛЕДНИЕ 5 ЗАПРОСОВ")
    print("="*60 + "\n")
    
    cursor = logger.conn.cursor()
    cursor.execute("""
        SELECT timestamp, user_input, route, iterations, duration_seconds, cost_rub
        FROM requests
        ORDER BY id DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        timestamp, user_input, route, iterations, duration, cost = row
        print(f"🕐 {timestamp[:19]}")
        print(f"   Запрос: {user_input[:50]}...")
        print(f"   Маршрут: {route}")
        print(f"   Итераций: {iterations}, Время: {duration:.2f}с, Стоимость: {cost:.4f} руб")
        print()

if __name__ == "__main__":
    main()
