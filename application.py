import os

from flask import Flask, session, redirect, g
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from flask import jsonify, render_template, request, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
	if 'username' in session:
		return redirect(url_for('userpage', user = session['username']))
	return render_template("home.html")

@app.route("/register", methods = ["GET", "POST"])
def register():
	if request.method == "POST":
		username = request.form.get('username')
		password = generate_password_hash(request.form.get('password'))		
		try:
			db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
				{"username": username, "password": password})
			db.commit()
		except IntegrityError as e:
			flash('User already exists. Please Login instead.')
			return redirect(url_for('login'))
		return render_template("success.html", message = "Successfully Registered. Please Login.")
	return render_template("register.html")
	
@app.route("/login", methods = ["GET", "POST"])
def login():
	if request.method == "POST":
		username = request.form.get('username')
		password = request.form.get('password')
		pws = db.execute("SELECT password FROM users WHERE username = :username", {"username": username}).fetchone()
		db.commit()
		if pws is None:
			return render_template("login.html", error = "The credentials do not exist!")
		if check_password_hash(pws[0], password):
			session['username'] = username
			return redirect(url_for('userpage', user = session['username']))
		else:
			return render_template("login.html", error = "The credentials do not match!")
	return render_template("login.html")

def check_login():
	if 'username' not in session:
		flash('Please Login to continue your operation.')
		return redirect(url_for('login'))

@app.route("/userpage/<user>", methods = ["GET", "POST"])
def userpage(user):
	check_login()
	query = request.form.get('search_text')
	if query:
		return redirect(url_for('results', search = query))
	return render_template("search.html", username = user)
	
@app.route("/logout")
def logout():
	session.pop('username', None)
	return redirect(url_for('index'))
	
@app.route("/results/<search>", methods = ["GET"])
def results(search):
	check_login()
	dbresult = db.execute("SELECT * FROM books WHERE (isbn LIKE :dbq) OR (UPPER(title) LIKE UPPER(:dbq)) OR (UPPER(author) LIKE UPPER(:dbq)) LIMIT 30", {"dbq": '%' + search + '%'}).fetchall()
	db.commit()
	return render_template("results.html", dbresult = dbresult, search = search)

@app.route("/book/<book_isbn>", methods = ["GET", "POST"])
def book(book_isbn):
	check_login()
	db_details = db.execute("SELECT * FROM books WHERE (isbn = :book_isbn)", {"book_isbn": book_isbn}).fetchone()
	db.commit()
	if db_details is None:
		return jsonify({"error": "No book with such ISBN is found on our server."}), 404
	book_details = db_details.items()
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "uTHQ4F9cSJapF2QQcz4mw", "isbns": book_isbn})
	data = res.json()
	wc = data['books'][0]['work_ratings_count']
	ar = data['books'][0]['average_rating']
	book_details.append(('work_ratings_count', wc))
	book_details.append(('average_rating', ar))
	already_reviewed = False
	if request.method == "POST":
		star = request.form.get("star")
		review = request.form.get("review")
		username = session['username']
		isbn = book_isbn
		db.execute("INSERT INTO reviews (username, isbn, review, star) VALUES (:username, :isbn, :review, :star)",
				{"username": username, "isbn": isbn, "review": review, "star": star})
		db.commit()
	dbreview = db.execute("SELECT * FROM reviews WHERE (isbn = :isbn)", {"isbn": book_isbn}).fetchall()
	db.commit()
	for dbre in dbreview:
		if session['username'] == dbre.username:
			already_reviewed = True
	return render_template("book.html", book_details = book_details, dbreview = dbreview, already_reviewed = already_reviewed)

@app.route("/api/<isbn>", methods = ["GET"])
def api(isbn):
	db_details = db.execute("SELECT * FROM books WHERE (isbn = :isbn)", {"isbn": isbn}).fetchone()
	db.commit()
	if db_details is None:
		return jsonify({"error": "No book with such ISBN is found on our server."}), 404
	book_details = db_details.items()
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "uTHQ4F9cSJapF2QQcz4mw", "isbns": isbn})
	data = res.json()
	wc = data['books'][0]['work_ratings_count']
	ar = data['books'][0]['average_rating']
	book_details.append(('work_ratings_count', wc))
	book_details.append(('average_rating', ar))
	return jsonify({
			"title": book_details[1][1],
			"author": book_details[2][1],
			"year": book_details[3][1],
			"isbn": book_details[0][1],
			"review_count": book_details[4][1],
			"average_score": book_details[5][1]
		})

	
