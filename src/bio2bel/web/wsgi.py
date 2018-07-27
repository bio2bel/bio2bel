# -*- coding: utf-8 -*-

"""Run Bio2BEL with WSGI."""

from bio2bel.web.application import create_application

if __name__ == '__main__':
    app = create_application()
    app.run(host='0.0.0.0', port=5000, debug=True)
