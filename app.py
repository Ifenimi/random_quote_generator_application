from random import choice

from flask import Flask, make_response, render_template

app = Flask(__name__)

QUOTES = [
    {
        "text": "Programs must be written for people to read, and only incidentally for machines to execute.",
        "author": "Harold Abelson",
    },
    {
        "text": "First, solve the problem. Then, write the code.",
        "author": "John Johnson",
    },
    {
        "text": "Simplicity is the ultimate sophistication.",
        "author": "Leonardo da Vinci",
    },
    {
        "text": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.",
        "author": "Martin Fowler",
    },
    {
        "text": "The most important property of a program is whether it accomplishes the intention of its user.",
        "author": "C.A.R. Hoare",
    },
    {
        "text": "Make it work, make it right, make it fast.",
        "author": "Kent Beck",
    },
    {
        "text": "It's not a bug; it's an undocumented feature.",
        "author": "Anonymous",
    },
]


@app.get("/")
def home():
    response = make_response(render_template("index.html", quote=choice(QUOTES)))
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(debug=True)