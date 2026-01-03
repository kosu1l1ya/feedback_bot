import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import Config


class GoogleSheetsManager:
    """Управление Google Sheets."""
    
    def __init__(self):
        self.config = Config
        self.client = None
        
    def connect(self):
        """Подключение к Google Sheets."""
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(
                "credentials.json",
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            print("✅ Подключено к Google Sheets")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            self.client = None
    
    def save_feedback(self, user_data: dict, feedback_data: dict):
        """Сохранение отзыва в таблицу."""
        if not self.client:
            self.connect()
            if not self.client:
                return False
        
        try:
            spreadsheet = self.client.open_by_key(self.config.SPREADSHEET_ID)
            sheet = spreadsheet.worksheet(self.config.SHEET_NAME)
            
            # Формируем строку для добавления
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(user_data.get("id", "")),
                user_data.get("username", ""),
                user_data.get("first_name", ""),
                user_data.get("last_name", ""),
                str(feedback_data.get("rating", "")),
                feedback_data.get("type", ""),
                feedback_data.get("comment", ""),
                "новый"
            ]
            
            sheet.append_row(row)
            print(f"✅ Отзыв сохранен для пользователя {user_data.get('id')}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False
    
    def get_stats(self):
        """Получение статистики."""
        if not self.client:
            self.connect()
            if not self.client:
                return {"total": 0, "average": 0}
        
        try:
            spreadsheet = self.client.open_by_key(self.config.SPREADSHEET_ID)
            sheet = spreadsheet.worksheet(self.config.SHEET_NAME)
            
            data = sheet.get_all_values()
            if len(data) <= 1:
                return {"total": 0, "average": 0}
            
            # Пропускаем заголовок
            rows = data[1:]
            ratings = []
            
            for row in rows:
                if len(row) > 5 and row[5].isdigit():
                    ratings.append(int(row[5]))
            
            total = len(rows)
            average = sum(ratings) / len(ratings) if ratings else 0
            
            return {
                "total": total,
                "average": round(average, 2),
                "last_feedback": rows[-1][0] if rows else "Нет данных"
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {"total": 0, "average": 0}


# Глобальный экземпляр
sheets_manager = GoogleSheetsManager()