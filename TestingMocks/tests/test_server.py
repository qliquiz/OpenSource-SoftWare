from fastapi.testclient import TestClient
from server.server import app
 

client = TestClient(app)

def test_register_user():
    # Тест успешной регистрации
    response = client.post(
        "/register/",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully"}

    # Тест регистрации существующего пользователя
    response = client.post(
        "/register/",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "User already exists"}

def test_get_users():
    # Регистрация тестового пользователя
    client.post(
        "/register/",
        json={"username": "testuser2", "password": "testpass"}
    )
    
    response = client.get("/users/")
    assert response.status_code == 200
    assert "testuser2" in response.json()["users"]

def test_upload_file():
    # Регистрация пользователя
    client.post(
        "/register/",
        json={"username": "fileuser", "password": "testpass"}
    )

    # Создание тестового CSV файла
    csv_content = "name,age\nJohn,30\nJane,25"
    files = {
        "file": ("test.csv", csv_content, "text/csv")
    }

    response = client.post(
        "/upload/fileuser",
        files=files
    )
    assert response.status_code == 200
    assert response.json() == {"message": "File uploaded successfully"}

    # Тест загрузки файла для несуществующего пользователя
    response = client.post(
        "/upload/nonexistent",
        files=files
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_get_user_data():
    # Регистрация пользователя
    client.post(
        "/register/",
        json={"username": "datauser", "password": "testpass"}
    )

    # Загрузка тестовых данных
    csv_content = "name,age\nJohn,30\nJane,25"
    files = {
        "file": ("test.csv", csv_content, "text/csv")
    }
    client.post("/upload/datauser", files=files)

    # Получение данных пользователя
    response = client.get("/user/datauser")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["name"] == "John"
    assert data[0]["age"] == "30"

    # Тест получения данных несуществующего пользователя
    response = client.get("/user/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

def test_get_user_data_json():
    # Регистрация пользователя
    client.post(
        "/register/",
        json={"username": "jsonuser", "password": "testpass"}
    )

    # Загрузка тестовых данных
    csv_content = "name,age\nJohn,30\nJane,25"
    files = {
        "file": ("test.csv", csv_content, "text/csv")
    }
    client.post("/upload/jsonuser", files=files)

    # Получение JSON данных пользователя
    response = client.get("/data/jsonuser")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "John"
    assert data[0]["age"] == "30"

    # Тест получения JSON данных несуществующего пользователя
    response = client.get("/data/nonexistent")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

 