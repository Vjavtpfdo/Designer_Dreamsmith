from flask import Flask, render_template, request, redirect, url_for, session
from database import init_db, add_user
import requests
import os
import sqlite3
import bcrypt  # For password hashing
import certifi
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
init_db()

# Ensure API Key is set
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Get API key from environment variable
if not GEMINI_API_KEY:
    GEMINI_API_KEY = "your_actual_api_key"  # Hardcode for testing (not recommended)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')  # Convert to bytes
        
        user = check_user(username)
        if user and bcrypt.checkpw(password, user[1]):  # Compare hashed password
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid credentials, please try again."
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        add_user(username, hashed_password)
        return redirect(url_for('user_login'))
    return render_template('register.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    color = request.form['color']
    gender = request.form['gender']
    top_bottom = request.form['top_bottom']
    occasion = request.form['occasion']
    style = request.form['style']
    age = request.form['age']

    # Get dress description from Gemini API
    description = get_dress_description(f"{color} {top_bottom} for {occasion}")

    # Get image through web scraping
    image_url = scrape_dress_image(f"{color} {top_bottom}")

    # Keep generating images until user is satisfied
    while not user_satisfied():
        image_url = scrape_dress_image(f"{color} {top_bottom}")
    
    # Recommend accessories
    accessories = recommend_accessories(top_bottom)

    return render_template('recommendation.html', description=description, image_url=image_url, accessories=accessories)

def check_user(username):
    """Retrieve user by username"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT username, password FROM users WHERE username=?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def get_dress_description(dress_type):
    """Fetch dress description using Gemini API"""
    if not GEMINI_API_KEY:
        return "API Key is missing."

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateText?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "prompt": {"text": f"Describe a stylish {dress_type}."},
        "temperature": 0.7
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("text", "No description available.")
    return "Failed to fetch description."

def scrape_dress_image(dress_type):
    """Scrape images from a fashion website"""
    search_url = f"https://www.fashionwebsite.com/search?q={dress_type}"  # Replace with real website
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(search_url, headers=headers, verify=certifi.where())
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return "https://via.placeholder.com/150"  # Fallback placeholder image

    soup = BeautifulSoup(response.text, 'html.parser')
    image_tag = soup.find('img')  # Adjust this for the actual structure
    
    if image_tag and 'src' in image_tag.attrs:
        return image_tag['src']
    
    return "https://via.placeholder.com/150"  # Placeholder image if scraping fails

def recommend_accessories(dress_type):
    """Recommend accessories dynamically"""
    accessories_mapping = {
        "dress": ["Necklace", "Bracelet", "Earrings"],
        "jeans": ["Leather Belt", "Sneakers", "Backpack"],
        "shirt": ["Watch", "Tie", "Cufflinks"]
    }
    return accessories_mapping.get(dress_type.lower(), ["Sunglasses", "Handbag", "Hat"])

def user_satisfied():
    """Poll user if they are satisfied with the generated image"""
    response = input("Are you satisfied with the generated outfit? (yes/no): ").strip().lower()
    return response == "yes"

if __name__ == '__main__':
    app.run(debug=True)
