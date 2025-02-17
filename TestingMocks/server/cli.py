import questionary
import requests
import os

SERVER_URL = "http://127.0.0.1:8000"

class CLI:
    def register_user():
        username = questionary.text("Введите имя пользователя:").ask()
        password = questionary.password("Введите пароль:").ask()
        
        response = requests.post(f"{SERVER_URL}/register/", json={"username": username, "password": password})
        print(response.json()["message"] if response.status_code == 200 else response.json()["detail"])

    def upload_file():
        username = questionary.text("Введите имя пользователя:").ask()
        file_path = questionary.path("Введите путь к CSV файлу:").ask()
        
        if not os.path.exists(file_path):
            print("Ошибка: Файл не найден!")
            return
        
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/csv")}
            response = requests.post(f"{SERVER_URL}/upload/{username}", files=files)
        
        print(response.json()["message"] if response.status_code == 200 else response.json()["detail"])

    def list_users():
        response = requests.get(f"{SERVER_URL}/users/")
        if response.status_code == 200:
            print("Зарегистрированные пользователи:")
            for user in response.json()["users"]:
                print(f"- {user}")
        else:
            print("Ошибка при получении списка пользователей.")

    def get_user_data():
        username = questionary.text("Введите имя пользователя:").ask()
        response = requests.get(f"{SERVER_URL}/user/{username}")
        print(response)
        
        if response.status_code == 200:
            print(f"Данные пользователя {username}:")
            for item in response.json()["data"]:
                print(item)
        else:
            print(response.json()["detail"])

    def main():
        while True:
            choice = questionary.select(
                "Выберите действие:",
                choices=[
                    "1. Зарегистрировать пользователя",
                    "2. Загрузить CSV-файл",
                    "3. Посмотреть список пользователей",
                    "4. Посмотреть данные пользователя",
                    "5. Выйти"
                ],
            ).ask()

            if choice.startswith("1"):
                register_user()
            elif choice.startswith("2"):
                upload_file()
            elif choice.startswith("3"):
                list_users()
            elif choice.startswith("4"):
                get_user_data()
            elif choice.startswith("5"):
                break

    if __name__ == "__main__":
        main()
