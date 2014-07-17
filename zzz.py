'''
zzz
'''
import os

import mako.lookup

import tornado.options
import tornado.httpserver
import tornado.web
import tornado.template

from tornado.options import define, options

CURRENT_PATH = os.path.dirname(__file__)

define('port', default=8080, help="run on the given port", type=int)
define('debug', default=False, help="run on debug mode", type=bool)

from utils import route, route_add

import config
import handlers
import admins

def main():
    '''main'''
    tornado.options.parse_command_line()
    routes = route.get_routes()
    template_path=os.path.join(CURRENT_PATH, 'templates'), 
    settings = dict(
        template_path=template_path,
        static_path=os.path.join(CURRENT_PATH, 'static'), 
        xsrf_cookies=True,
        cookie_secret=config.cookie_secret,
        debug=options.debug,
        )
    app = tornado.web.Application(
        routes,
        **settings
        )

    #templdate
    app.lookup = mako.lookup.TemplateLookup(
        directories = template_path,
        input_encoding = 'utf-8',
        output_encoding = 'utf-8'
        )
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
