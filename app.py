from flask import Flask
import json
import mysql.connector
from config import DB_CONFIG
from flask import request, jsonify, render_template
import re

app = Flask(__name__)

# Connect to MySQL database
def connect_db():
    return mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )

# Create the recipe_details table
def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_details (
            cuisine VARCHAR(100),
            title VARCHAR(255),
            url VARCHAR(255),
            rating FLOAT,
            total_time INT,
            prep_time INT,
            cook_time INT,
            description TEXT,
            ingredients JSON,
            instructions JSON,
            nutrients JSON,
            serves VARCHAR(50)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Insert the data
def insert_recipe(recipe):
    conn = connect_db()
    cursor = conn.cursor()

    ingredients = json.dumps(recipe.get('ingredients', []))
    instructions = json.dumps(recipe.get('instructions', []))
    nutrients = json.dumps(recipe.get('nutrients', {}))

    cursor.execute("""
        INSERT INTO recipe_details (
            cuisine,
            title,
            url,
            rating,
            total_time,
            prep_time,
            cook_time,
            description,
            ingredients,
            instructions,
            nutrients,
            serves
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        recipe.get('cuisine', ''),
        recipe.get('title', ''),
        recipe.get('URL', ''),
        recipe.get('rating', 0.0),
        recipe.get('total_time', 0),
        recipe.get('prep_time', 0),
        recipe.get('cook_time', 0),
        recipe.get('description', ''),
        ingredients,
        instructions,
        nutrients,
        recipe.get('serves', '')
    ))

    conn.commit()
    cursor.close()
    conn.close()

# API route to import recipes from a JSON file
@app.route('/import-recipes')
def import_recipes():
    try:
        with open('recipes.json', 'r') as f:
            data = json.load(f)
            for recipe in data.values():
                insert_recipe(recipe)
        return "Recipes added successfully!"

    except Exception as e:
        return f"Error: {e}"

@app.route('/')
def home():
    return " "

# API 1
@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit

        conn = connect_db()
        cursor = conn.cursor(dictionary=True)

        # Get recipes sorted by rating
        cursor.execute("SELECT * FROM recipe_details ORDER BY rating DESC LIMIT %s OFFSET %s", (limit, offset))
        recipes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(recipes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API 2
@app.route('/api/recipes/search', methods=['GET'])
def search_recipes():
    try:
        query = "SELECT * FROM recipe_details"
        params = []

        # Utility to parse operators
        def parse_filter_param(param_value):
            match = re.match(r'(<=|>=|=|<|>)(\d+(\.\d+)?)', param_value)
            if match:
                operator, value = match.group(1), match.group(2)
                return operator, float(value) if '.' in value else int(value)
            return None, None

        title = request.args.get('title')
        if title:
            query += " AND title LIKE %s"
            params.append(f"%{title}%")

        cuisine = request.args.get('cuisine')
        if cuisine:
            query += " AND cuisine = %s"
            params.append(cuisine)

        total_time = request.args.get('total_time')
        if total_time:
            op, val = parse_filter_param(total_time)
            if op and val is not None:
                query += f" AND total_time {op} %s"
                params.append(val)

        rating = request.args.get('rating')
        if rating:
            op, val = parse_filter_param(rating)
            if op and val is not None:
                query += f" AND rating {op} %s"
                params.append(val)

        calories = request.args.get('calories')
        if calories:
            op, val = parse_filter_param(calories)
            if op and val is not None:
                query += f" AND CAST(JSON_UNQUOTE(JSON_EXTRACT(nutrients, '$.calories')) AS UNSIGNED) {op} %s"
                params.append(val)

        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    create_table()
    app.run(debug=True)
