import os
import sys
from flask import *

base_dir = os.path.abspath(sys.argv[1])
if not os.path.isdir(base_dir):
    raise RuntimeError("Not a directory: %r" % base_dir)

app = Flask(__name__)


@app.route("/")
def list():
    return jsonify(os.listdir(base_dir))


@app.route("/<path:path>")
def get(path):
    return send_from_directory(base_dir, path)


if __name__ == "__main__":
    app.run(port=5101)
