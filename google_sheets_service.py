"""
Полный сервис для работы с Google Sheets API
Подробные комментарии для понимания каждой строки кода
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Класс для управления всеми операциями с Google Sheets.
    
    Основные возможности:
    1. Авторизация через сервисный аккаунт
    2. Добавление новых записей
    3. Чтение данных
    4. Получение статистики
    5. Очистка старых записей
    """
    
    def __init__(self, credentials_file: str = "credentials.json", 
                 spreadsheet_id: str = None):
        """
        Инициализация сервиса.
        
        Args:
            credentials_file: Путь к файлу с ключами сервисного аккаунта
            spreadsheet_id: ID Google таблицы
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self.sheet = None
        
        # Кэширование для уменьшения запросов к API
        self._stats_cache = None
        self._cache_time = None
        self.CACHE_TIMEOUT = 60  # секунд
        
    def _get_scopes(self) -> List[str]:
        """
        Определяем необходимые разрешения (scopes).
        
        Важно: чем меньше scope, тем безопаснее.
        Для нашего бота достаточно только sheets.
        """
        return [
            "https://www.googleapis.com/auth/spreadsheets",
            # "https://www.googleapis.com/auth/drive"  # Нужен только если создаем таблицы
        ]
    
    def _create_credentials(self):
        """
        Создание объекта Credentials из файла сервисного аккаунта.
        
        Важно: файл credentials.json должен быть в той же папке
        или указан полный путь.
        """
        try:
            # Читаем файл с учетными данными
            with open(self.credentials_file, 'r') as f:
                creds_data = json.load(f)
                logger.info(f"✅ Учетные данные загружены. Email: {creds_data.get('client_email')}")
            
            # Создаем объект Credentials
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self._get_scopes()
            )
            return creds
            
        except FileNotFoundError:
            logger.error(f"❌ Файл {self.credentials_file} не найден!")
            logger.info("💡 Создайте файл credentials.json по инструкции в README")
            raise
        except json.JSONDecodeError:
            logger.error(f"❌ Ошибка чтения JSON из {self.credentials_file}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка создания учетных данных: {e}")
            raise
    
    def connect(self) -> bool:
        """
        Подключение к Google Sheets API.
        
        Returns:
            bool: Успешно ли подключение
        """
        try:
            logger.info("🔄 Подключаемся к Google Sheets API...")
            
            # Получаем учетные данные
            creds = self._create_credentials()
            
            # Авторизуем клиент gspread
            self.client = gspread.authorize(creds)
            
            # Открываем таблицу по ID
            if self.spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                self.sheet = self.spreadsheet.sheet1  # Первый лист
                
                # Проверяем доступ
                title = self.spreadsheet.title
                logger.info(f"✅ Подключено успешно! Таблица: '{title}'")
                
                # Инициализируем заголовки, если таблица пустая
                self._initialize_headers()
                
                return True
            else:
                logger.warning("⚠️ Не указан spreadsheet_id")
                return False
                
        except gspread.exceptions.APIError as e:
            logger.error(f"❌ Ошибка API Google Sheets: {e}")
            logger.info("💡 Проверьте:")
            logger.info("1. Включен ли Google Sheets API в консоли")
            logger.info("2. Правильный ли spreadsheet_id")
            logger.info("3. Есть ли доступ у сервисного аккаунта к таблице")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            return False
    
    def _initialize_headers(self):
        """
        Инициализация заголовков таблицы, если она пустая.
        Создает структуру для хранения отзывов.
        """
        try:
            # Получаем все значения из первого ряда
            first_row = self.sheet.row_values(1)
            
            # Если первая строка пустая, создаем заголовки
            if not first_row:
                headers = [
                    "Timestamp",          # Дата и время
                    "User ID",           # ID пользователя Telegram
                    "Username",          # @username
                    "First Name",        # Имя
                    "Last Name",         # Фамилия
                    "Rating",            # Оценка 1-5
                    "Type",              # Тип фидбека
                    "Comment",           # Комментарий
                    "Status",            # Статус (новый/обработан)
                    "Language Code",     # Язык пользователя
                    "Chat ID",           # ID чата
                    "Platform",          # Платформа (Telegram)
                    "Bot Version",       # Версия бота
                    "Session ID",        # ID сессии
                ]
                
                self.sheet.insert_row(headers, 1)
                logger.info("✅ Созданы заголовки таблицы")
                
                # Форматируем заголовки (жирный шрифт)
                self.sheet.format('A1:N1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 1.0}
                })
                
                # Настраиваем ширину колонок
                self._adjust_column_widths()
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации заголовков: {e}")
    
    def _adjust_column_widths(self):
        """
        Автоматическая настройка ширины колонок для лучшего отображения.
        """
        try:
            # Задаем оптимальную ширину для каждой колонки
            column_widths = {
                'A': 150,  # Timestamp
                'B': 100,  # User ID
                'C': 120,  # Username
                'D': 100,  # First Name
                'E': 100,  # Last Name
                'F': 80,   # Rating
                'G': 100,  # Type
                'H': 300,  # Comment
                'I': 100,  # Status
                'J': 100,  # Language Code
                'K': 100,  # Chat ID
                'L': 100,  # Platform
                'M': 100,  # Bot Version
                'N': 120,  # Session ID
            }
            
            # Применяем ширину (через gspread нет прямой поддержки,
            # но можно через batch_update)
            requests = []
            for col, width in column_widths.items():
                requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": self.sheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": ord(col) - ord('A'),
                            "endIndex": ord(col) - ord('A') + 1
                        },
                        "properties": {
                            "pixelSize": width
                        },
                        "fields": "pixelSize"
                    }
                })
            
            if requests:
                self.spreadsheet.batch_update({"requests": requests})
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось настроить ширину колонок: {e}")
    
    def save_feedback(self, user_data: Dict[str, Any], 
                     feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сохранение отзыва в таблицу.
        
        Args:
            user_data: Данные пользователя Telegram
            feedback_data: Данные отзыва
            
        Returns:
            Dict: Результат операции с деталями
        """
        result = {
            "success": False,
            "row_number": None,
            "error": None,
            "timestamp": None
        }
        
        try:
            # Проверяем подключение
            if not self.client or not self.sheet:
                if not self.connect():
                    result["error"] = "Не удалось подключиться к Google Sheets"
                    return result
            
            # Готовим данные для сохранения
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["timestamp"] = timestamp
            
            row_data = [
                timestamp,                                 # A: Дата и время
                str(user_data.get("id", "")),             # B: User ID
                user_data.get("username", ""),            # C: Username
                user_data.get("first_name", ""),          # D: Имя
                user_data.get("last_name", ""),           # E: Фамилия
                str(feedback_data.get("rating", "")),     # F: Оценка
                feedback_data.get("type", ""),            # G: Тип фидбека
                feedback_data.get("comment", ""),         # H: Комментарий
                "🆕 Новый",                               # I: Статус
                user_data.get("language_code", "ru"),     # J: Язык
                str(user_data.get("chat_id", "")),        # K: Chat ID
                "Telegram",                               # L: Платформа
                "1.0",                                    # M: Версия бота
                feedback_data.get("session_id", ""),      # N: ID сессии
            ]
            
            # Добавляем строку в таблицу
            self.sheet.append_row(row_data)
            
            # Получаем номер добавленной строки
            all_values = self.sheet.get_all_values()
            row_number = len(all_values)
            
            # Форматируем новую строку
            self._format_new_row(row_number)
            
            # Сбрасываем кэш статистики
            self._stats_cache = None
            
            result.update({
                "success": True,
                "row_number": row_number,
                "message": f"Отзыв сохранен в строке {row_number}"
            })
            
            logger.info(f"✅ Отзыв #{row_number} сохранен для пользователя {user_data.get('id')}")
            
            # Отправляем вебхук-уведомление (опционально)
            self._send_webhook_notification(row_number, user_data, feedback_data)
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка сохранения: {str(e)}"
            logger.error(f"❌ {error_msg}")
            result["error"] = error_msg
            return result
    
    def _format_new_row(self, row_number: int):
        """
        Форматирование новой строки для лучшей читаемости.
        
        Args:
            row_number: Номер строки для форматирования
        """
        try:
            # Форматируем оценку (цвет в зависимости от значения)
            rating_cell = f"F{row_number}"
            rating_value = self.sheet.acell(rating_cell).value
            
            if rating_value:
                rating = int(rating_value)
                # Цвета от красного (1) до зеленого (5)
                colors = {
                    1: {"red": 1.0, "green": 0.8, "blue": 0.8},
                    2: {"red": 1.0, "green": 0.9, "blue": 0.7},
                    3: {"red": 1.0, "green": 1.0, "blue": 0.7},
                    4: {"red": 0.8, "green": 1.0, "blue": 0.8},
                    5: {"red": 0.7, "green": 1.0, "blue": 0.7},
                }
                
                if rating in colors:
                    self.sheet.format(rating_cell, {
                        "backgroundColor": colors[rating],
                        "horizontalAlignment": "CENTER",
                        "textFormat": {"bold": True, "fontSize": 11}
                    })
            
            # Форматируем ячейку статуса
            status_cell = f"I{row_number}"
            self.sheet.format(status_cell, {
                "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 1.0},
                "horizontalAlignment": "CENTER",
                "textFormat": {"bold": True}
            })
            
            # Форматируем ячейку типа фидбека
            type_cell = f"G{row_number}"
            type_value = self.sheet.acell(type_cell).value
            type_colors = {
                "Предложение": {"red": 0.9, "green": 1.0, "blue": 0.9},
                "Ошибка": {"red": 1.0, "green": 0.9, "blue": 0.9},
                "Идея": {"red": 0.9, "green": 0.9, "blue": 1.0},
                "Благодарность": {"red": 1.0, "green": 1.0, "blue": 0.9},
            }
            
            if type_value in type_colors:
                self.sheet.format(type_cell, {
                    "backgroundColor": type_colors[type_value],
                    "horizontalAlignment": "CENTER"
                })
            
            # Автоподбор ширины для комментария
            comment_cell = f"H{row_number}"
            self.sheet.format(comment_cell, {
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"
            })
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отформатировать строку {row_number}: {e}")
    
    def _send_webhook_notification(self, row_number: int, 
                                  user_data: Dict, feedback_data: Dict):
        """
        Отправка уведомления через вебхук (опционально).
        Можно подключить к Slack, Discord, Telegram и т.д.
        """
        # Это опциональная функция - можно реализовать позже
        pass
    
    def get_all_feedbacks(self, limit: int = 100) -> List[Dict]:
        """
        Получение всех отзывов из таблицы.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            List[Dict]: Список отзывов
        """
        try:
            if not self.sheet:
                self.connect()
            
            # Получаем все значения (кроме заголовка)
            all_values = self.sheet.get_all_values()
            
            if len(all_values) <= 1:
                return []
            
            # Преобразуем в список словарей
            headers = all_values[0]
            data = all_values[1:limit+1]
            
            feedbacks = []
            for i, row in enumerate(data, start=2):  # start=2 потому что заголовок в строке 1
                if len(row) >= len(headers):
                    feedback = {}
                    for j, header in enumerate(headers):
                        feedback[header] = row[j] if j < len(row) else ""
                    feedback["_row"] = i  # Добавляем номер строки
                    feedbacks.append(feedback)
            
            return feedbacks
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения отзывов: {e}")
            return []
    
    def get_statistics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Получение статистики по отзывам с кэшированием.
        
        Args:
            force_refresh: Игнорировать кэш и обновить данные
            
        Returns:
            Dict: Статистика
        """
        # Проверяем кэш
        if (not force_refresh and self._stats_cache and 
            self._cache_time and 
            (datetime.now() - self._cache_time).seconds < self.CACHE_TIMEOUT):
            return self._stats_cache
        
        try:
            feedbacks = self.get_all_feedbacks()
            
            if not feedbacks:
                stats = {
                    "total": 0,
                    "average_rating": 0,
                    "rating_distribution": {},
                    "type_distribution": {},
                    "last_week": 0,
                    "today": 0,
                    "with_comments": 0,
                    "status_distribution": {},
                    "last_update": "Нет данных"
                }
            else:
                # Считаем статистику
                ratings = []
                type_counts = {}
                status_counts = {}
                today_count = 0
                week_count = 0
                with_comments = 0
                
                today = datetime.now().date()
                
                for fb in feedbacks:
                    # Рейтинги
                    if fb.get("Rating") and fb["Rating"].isdigit():
                        rating = int(fb["Rating"])
                        ratings.append(rating)
                    
                    # Распределение по типам
                    fb_type = fb.get("Type", "Не указан")
                    type_counts[fb_type] = type_counts.get(fb_type, 0) + 1
                    
                    # Распределение по статусам
                    status = fb.get("Status", "Не указан")
                    status_counts[status] = status_counts.get(status, 0) + 1
                    
                    # Комментарии
                    if fb.get("Comment", "").strip():
                        with_comments += 1
                    
                    # Дата для подсчета за сегодня/неделю
                    try:
                        fb_date = datetime.strptime(fb.get("Timestamp", ""), 
                                                   "%Y-%m-%d %H:%M:%S").date()
                        if fb_date == today:
                            today_count += 1
                        
                        # За последние 7 дней
                        days_diff = (today - fb_date).days
                        if days_diff <= 7:
                            week_count += 1
                    except:
                        pass
                
                # Распределение оценок
                rating_dist = {str(i): 0 for i in range(1, 6)}
                for r in ratings:
                    rating_dist[str(r)] = rating_dist.get(str(r), 0) + 1
                
                # Средний рейтинг
                avg_rating = sum(ratings) / len(ratings) if ratings else 0
                
                # Форматируем процент комментариев
                comment_percentage = (with_comments / len(feedbacks)) * 100 if feedbacks else 0
                
                stats = {
                    "total": len(feedbacks),
                    "average_rating": round(avg_rating, 2),
                    "rating_distribution": rating_dist,
                    "type_distribution": type_counts,
                    "status_distribution": status_counts,
                    "last_week": week_count,
                    "today": today_count,
                    "with_comments": with_comments,
                    "comment_percentage": round(comment_percentage, 1),
                    "last_update": feedbacks[0].get("Timestamp", "") if feedbacks else "Нет данных",
                    "success_rate": round((avg_rating / 5) * 100, 1) if avg_rating > 0 else 0
                }
            
            # Сохраняем в кэш
            self._stats_cache = stats
            self._cache_time = datetime.now()
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета статистики: {e}")
            return {
                "total": 0,
                "average_rating": 0,
                "error": str(e)
            }
    
    def create_dashboard_sheet(self):
        """
        Создание отдельного листа с дашбордом и графиками.
        Показывает аналитику в удобном виде.
        """
        try:
            # Создаем новый лист
            dashboard_title = "📊 Дашборд"
            
            # Проверяем, существует ли уже дашборд
            try:
                dashboard = self.spreadsheet.worksheet(dashboard_title)
                logger.info("✅ Дашборд уже существует")
                return dashboard
            except gspread.exceptions.WorksheetNotFound:
                pass
            
            # Создаем новый лист
            dashboard = self.spreadsheet.add_worksheet(
                title=dashboard_title,
                rows=50,
                cols=20
            )
            
            # Заполняем дашборд
            dashboard.update('A1', [['📊 ДАШБОРД ОБРАТНОЙ СВЯЗИ']])
            dashboard.format('A1', {
                'textFormat': {'bold': True, 'fontSize': 16},
                'horizontalAlignment': 'CENTER'
            })
            
            # Объединяем ячейки для заголовка
            dashboard.merge_cells('A1:E1')
            
            # Добавляем статистику
            stats = self.get_statistics(force_refresh=True)
            
            dashboard_data = [
                ['', ''],
                ['📈 ОБЩАЯ СТАТИСТИКА', ''],
                ['Всего отзывов:', stats['total']],
                ['Средняя оценка:', stats['average_rating']],
                ['Отзывов сегодня:', stats['today']],
                ['Отзывов за неделю:', stats['last_week']],
                ['С комментариями:', f"{stats['with_comments']} ({stats['comment_percentage']}%)"],
                ['Удовлетворенность:', f"{stats['success_rate']}%"],
                ['', ''],
                ['⭐ РАСПРЕДЕЛЕНИЕ ОЦЕНОК', ''],
            ]
            
            # Добавляем распределение оценок
            for rating, count in stats['rating_distribution'].items():
                percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
                stars = '⭐' * int(rating)
                dashboard_data.append([f'{stars} {rating}/5', f'{count} ({round(percentage, 1)}%)'])
            
            dashboard_data.extend([
                ['', ''],
                ['📂 РАСПРЕДЕЛЕНИЕ ПО ТИПАМ', ''],
            ])
            
            # Добавляем распределение по типам
            for fb_type, count in stats['type_distribution'].items():
                percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
                dashboard_data.append([fb_type, f'{count} ({round(percentage, 1)}%)'])
            
            # Обновляем данные
            dashboard.update('A3', dashboard_data)
            
            # Форматируем
            dashboard.format('A3:A10', {'textFormat': {'bold': True}})
            dashboard.format('A12', {'textFormat': {'bold': True, 'fontSize': 14}})
            dashboard.format('A22', {'textFormat': {'bold': True, 'fontSize': 14}})
            
            # Настраиваем ширину колонок
            dashboard.resize(rows=len(dashboard_data) + 10, cols=3)
            
            logger.info("✅ Дашборд создан успешно")
            return dashboard
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания дашборда: {e}")
            return None
    
    def export_to_csv(self, filename: str = "feedback_export.csv"):
        """
        Экспорт данных в CSV файл.
        
        Args:
            filename: Имя файла для экспорта
        """
        try:
            feedbacks = self.get_all_feedbacks()
            
            if not feedbacks:
                logger.warning("⚠️ Нет данных для экспорта")
                return False
            
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Получаем заголовки из первого отзыва
                if feedbacks:
                    fieldnames = list(feedbacks[0].keys())
                    # Убираем служебное поле
                    if '_row' in fieldnames:
                        fieldnames.remove('_row')
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for fb in feedbacks:
                        # Копируем без служебных полей
                        row = {k: v for k, v in fb.items() if k != '_row'}
                        writer.writerow(row)
            
            logger.info(f"✅ Данные экспортированы в {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Тестирование подключения и прав доступа.
        
        Returns:
            Dict: Результаты теста
        """
        test_results = {
            "connected": False,
            "has_access": False,
            "sheet_exists": False,
            "can_write": False,
            "can_read": False,
            "details": {},
            "errors": []
        }
        
        try:
            # Тест 1: Подключение
            if self.connect():
                test_results["connected"] = True
                test_results["details"]["spreadsheet_title"] = self.spreadsheet.title
                test_results["details"]["sheet_title"] = self.sheet.title
            else:
                test_results["errors"].append("Не удалось подключиться")
                return test_results
            
            # Тест 2: Чтение
            try:
                cell_value = self.sheet.acell('A1').value
                test_results["can_read"] = True
                test_results["details"]["first_cell"] = cell_value
            except Exception as e:
                test_results["errors"].append(f"Ошибка чтения: {e}")
            
            # Тест 3: Запись
            try:
                test_cell = 'Z100'  # Далекая ячейка, чтобы не мешать данным
                original_value = self.sheet.acell(test_cell).value
                
                # Пытаемся записать и прочитать обратно
                test_value = f"TEST_{datetime.now().timestamp()}"
                self.sheet.update(test_cell, test_value)
                
                # Проверяем запись
                written_value = self.sheet.acell(test_cell).value
                if written_value == test_value:
                    test_results["can_write"] = True
                
                # Восстанавливаем оригинальное значение
                if original_value is None:
                    self.sheet.update(test_cell, '')
                else:
                    self.sheet.update(test_cell, original_value)
                    
            except Exception as e:
                test_results["errors"].append(f"Ошибка записи: {e}")
            
            # Тест 4: Общие проверки
            test_results["sheet_exists"] = True
            test_results["has_access"] = test_results["can_read"] and test_results["can_write"]
            
            return test_results
            
        except Exception as e:
            test_results["errors"].append(f"Общая ошибка теста: {e}")
            return test_results


# ==================== ИСПОЛЬЗОВАНИЕ ====================

# Пример использования в основном боте:
def setup_google_sheets():
    """
    Инициализация Google Sheets для бота.
    """
    from config import Config
    
    # Создаем экземпляр сервиса
    sheets_service = GoogleSheetsService(
        credentials_file="credentials.json",
        spreadsheet_id=Config.SPREADSHEET_ID
    )
    
    # Тестируем подключение
    print("🧪 Тестируем подключение к Google Sheets...")
    test_results = sheets_service.test_connection()
    
    if test_results["connected"] and test_results["has_access"]:
        print("✅ Подключение успешно!")
        print(f"   Таблица: {test_results['details'].get('spreadsheet_title')}")
        
        # Создаем дашборд (если нужно)
        sheets_service.create_dashboard_sheet()
        
        # Получаем текущую статистику
        stats = sheets_service.get_statistics()
        print(f"   Всего отзывов: {stats['total']}")
        print(f"   Средняя оценка: {stats['average_rating']}/5")
        
        return sheets_service
    else:
        print("❌ Ошибка подключения!")
        for error in test_results.get("errors", []):
            print(f"   • {error}")
        
        print("\n🔧 Проверьте:")
        print("1. Файл credentials.json в папке проекта")
        print("2. ID таблицы в .env файле")
        print("3. Доступ сервисного аккаунта к таблице")
        print("4. Интернет-подключение")
        
        return None


if __name__ == "__main__":
    # Запуск теста
    service = setup_google_sheets()
    
    if service:
        print("\n📊 Демонстрация работы:")
        
        # Пример сохранения тестового отзыва
        test_user = {
            "id": 123456789,
            "username": "test_user",
            "first_name": "Иван",
            "last_name": "Тестовый",
            "language_code": "ru",
            "chat_id": 123456789
        }
        
        test_feedback = {
            "rating": 5,
            "type": "Благодарность",
            "comment": "Тестовый отзыв для демонстрации работы бота",
            "session_id": "test_session_001"
        }
        
        result = service.save_feedback(test_user, test_feedback)
        print(f"✅ Тестовый отзыв: {result.get('message', 'Отправлен')}")
        
        # Экспорт данных
        service.export_to_csv("demo_export.csv")
        print("✅ Данные экспортированы в demo_export.csv")