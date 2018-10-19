import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE books (isbn CHAR(10) PRIMARY KEY,title VARCHAR(255) NOT NULL,author VARCHAR(255) NOT NULL,year INTEGER NOT NULL);")
    db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY,username VARCHAR NOT NULL,password VARCHAR NOT NULL);")
    db.execute("CREATE TABLE reviews (id SERIAL PRIMARY KEY,isbn CHAR(10) NOT NULL,star INTEGER NOT NULL,review VARCHAR NOT NULL);")
    b = open("books.csv")
    reader = csv.reader(b)
    for isbn, title, author, year in reader:
    	i = 0;
    	db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
    		{"isbn": isbn, "title": title,"author": author, "year": year})
    	i += 1
    	print("Book " + str(i) + " added successfully!")
    db.commit()
    
if __name__ == "__main__":
    main()
