""" Besturing van appartuur thuis """
import waitress
from flask import Flask, render_template

app = Flask(__name__)


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ toon de hoofdpagina """
  return render_template('hoofdpagina.html')


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8088)
