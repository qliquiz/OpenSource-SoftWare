from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
import csv

app = FastAPI()

class User(BaseModel):
    username: str
    password: str

users_db = {}
user_files = {}

def parse_csv(csv_string: str) -> List[Dict[str, str]]:
    data = []
    lines = csv_string.strip().split("\n")
    if not lines:
        return data

    reader = csv.reader(lines)
    header = next(reader)

    for row in reader:
        row_dict = {}
        for col_name, value in zip(header, row):
            row_dict[col_name] = value.strip()
        data.append(row_dict)

    return data

@app.post("/register/")
def register_user(user: User):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    users_db[user.username] = user.password
    user_files[user.username] = []
    return {"message": "User registered successfully"}

@app.post("/upload/{username}")
async def upload_file(username: str, file: UploadFile = File(...)):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    contents = await file.read()
    csv_string = contents.decode("utf-8")
    parsed_data = parse_csv(csv_string)
    user_files[username].extend(parsed_data)
    return {"message": "File uploaded successfully"}

@app.get("/users/")
def get_users():
    return {"users": list(users_db.keys())}

@app.get("/user/{username}")
def get_user_data(username: str):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return {"data": user_files.get(username, [])}

@app.get("/data/{username}")
def get_user_data_json(username: str):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return user_files.get(username, [])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
