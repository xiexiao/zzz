# -*- coding:utf-8 -*-
'''
utils
'''
import sys
import math
import tornado.web
from tornado.options import options

startdir = sys.path[0]

class route(object):
    """
    decorates RequestHandlers and builds up a list of routables handlers
 
    Tech Notes (or "What the *@# is really happening here?")
    --------------------------------------------------------
 
    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.
 
    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.
 
    Example
    -------
 
    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        def get(self):
            goto = self.reverse_url('other')
            self.redirect(goto)
 
    # so you can do myapp.reverse_url('other')
    @route('/some/other/path', name='other')
    class SomeOtherRequestHandler(RequestHandler):
        def get(self):
            goto = self.reverse_url('SomeRequestHandler')
            self.redirect(goto)
 
    my_routes = route.get_routes()
    """
    _routes = []
 
    def __init__(self, uri, name=None, rank=1):
        self._uri = uri
        self.name = name
        self.rank = rank 
 
    def __call__(self, _handler):
        """gets called when we class decorate"""
        name = self.name and self.name or _handler.__name__
        url = tornado.web.url(self._uri, _handler, name=name)
        url.rank = self.rank
        self._routes.append(url)
        return _handler
 
    @classmethod
    def get_routes(cls):
        '''get routes'''
        import operator
        routes = sorted(cls._routes, 
            key=operator.attrgetter('rank'), reverse=True)
        return routes

    @classmethod
    def add_route(cls, url, rank=1):
        '''add route'''
        url.rank = rank
        cls._routes.append(url)
 
# Use it as follows to redirect other paths into your decorated handler.
#
#   from routes import route, route_redirect
#   route_redirect('/smartphone$', '/smartphone/')
#   route_redirect('/iphone/$', '/smartphone/iphone/', name='iphone_shortcut')
#   @route('/smartphone/$')
#   class SmartphoneHandler(RequestHandler):
#        def get(self):
#            ...
def route_redirect(from_, to, name=None):
    '''route_redirect'''
    route.add_route(tornado.web.url(from_, tornado.web.RedirectHandler,
        dict(url=to), name=name))

def route_add(from_, _handler, name=None):
    '''
    route_add(r'/(.*)/', RedirectHandler)
    '''
    route.add_route(tornado.web.url(from_, _handler, name))

@route(r'/(.*)/')
class RedirectHandler(tornado.web.RequestHandler):
    '''RedirectHandler'''
    def initialize(self, permanent=True):
        self._permanent = permanent
    def get(self, url):
        self.write(url)
        if url and not url.startswith('/'):
            url = '/' + url
        self.redirect(url, permanent=self._permanent)

#连接数据库
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
#计算数据库查询的时间
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, 
        parameters, context, executemany):
    '''before_cursor_execute'''
    conn.db_query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, 
        parameters, context, executemany):
    '''after_cursor_execute'''
    total = time.time() - conn.db_query_start_time
    if not hasattr(conn, 'db_query_times'):
        conn.db_query_times = []
    conn.db_query_times.append(total)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tornado.options import options
import config
class Backend(object):
    '''Backend'''
    def __init__(self):
        db_url = 'sqlite:///%s/%s' % (startdir, config.database_name) 
        engine = create_engine(
            db_url,
            convert_unicode=True,
            encoding='utf-8',
            echo=options.debug,
        )
        self._session = sessionmaker(bind=engine)
  
    @classmethod
    def instance(cls):
        """Singleton like accessor to instantiate backend object"""
        if not hasattr(cls,"_instance"):
            cls._instance = cls()
        return cls._instance
  
    def get_session(self):
        '''get session'''
        return self._session()

def dbhook(read_only=False, auto_commit=True):
    '''数据库的hook'''
    def _(func):
        '''_'''
        def wrapper(*a, **kw):
            '''wrapper'''
            _handler = a[0]
            _handler.db = Backend.instance().get_session()
            try:
                result = func(*a, **kw)
            finally:
                if read_only:
                    _handler.db.rollback()
                else:
                    if auto_commit:
                        _handler.db.commit()
                _handler.db.close()
            return result
        return wrapper 
    return _

def get_int(val, value=0):
    '''try get int, if except return value'''
    try:
        return int(val)
    except ValueError:
        return value

def get_pagecount(record_count, page_size):
    '''计算页面的总数'''
    if record_count == 0:
        page_count = 0
    else:
        page_count = int(math.ceil(record_count / float(page_size)))
        if page_count == 0 and record_count > 0:
            page_count = 1
    return page_count

def urlwrite(site_url, url=''):
    '''url write'''
    if site_url.endswith('/'):
        s_url = site_url.rstrip('/')
    else:
        s_url = site_url
    if url and not url.startswith('/'):
        url = '/' + url
    url = s_url + url
    return url

import xml.etree.cElementTree as ET

def _dict_to_xml_recurse(parent, dictitem):
    '''dict to xml recurse'''
    assert type(dictitem) is not type([])

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if str(tag).startswith('__'):
                parent.set(str(tag).lstrip('__'), str(child))
            elif str(tag) == '_text':
                parent.text = str(child)
            elif type(child) is type([]):
                # iterate through the array and convert
                for listchild in child:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    _dict_to_xml_recurse(elem, listchild)
            else:                
                elem = ET.Element(tag)
                parent.append(elem)
                _dict_to_xml_recurse(elem, child)
    else:
        parent.text = str(dictitem)
    
def dict_to_et(xmldict):
    """
    Converts a dictionary to an XML ElementTree Element 
    """
    roottag = xmldict.keys()[0]
    root = ET.Element(roottag)
    _dict_to_xml_recurse(root, xmldict[roottag])
    return root

from xml.dom import minidom
def dict_to_xml(xmldict):
    '''dict to xml'''
    rough_string = ET.tostring(dict_to_et(xmldict), 'utf-8')
    reparsed = minidom.parseString(rough_string) 
    return reparsed.toprettyxml(indent="    ")

class Cache(object):
    data = {}

    @classmethod
    def get(cls, key):
        if key in cls.data:
            return cls.data.get(key)
        return None

    @classmethod
    def set(cls, key, value, timeout = 0):
        if value is not None:
            cls.data[key] = value
            return value
    @classmethod
    def delete(cls, key):
        if key in cls.data:
            cls.data.pop(key)

    @classmethod
    def clear(self):
        self.data.clear()

import datetime
def cached(cache_key=None, timeout_seconds=3000, remove=False):
    '''timeout = 60*60*24*100 s= 100 days
    '''
    def _(cls=None):
        '''_'''
        if not cache_key: 
            #key = (cls, tuple(a), tuple(sorted(kw.items())))
            assert cls != None
            key = (cls)
        else:
            key = cache_key
        key_addtime = (key, '_addtime')
        def do_cached(*a, **kw):
            '''do cached'''
            cached_obj = Cache.get(key)
            if not cached_obj:
                cached_obj = cls(*a, **kw)
                Cache.set(key, cached_obj, timeout_seconds)
            return cached_obj
        def remove_cached(*a, **kw):
            '''remove cached'''
            Cache.delete(cache_key)
            if cls:
                return cls(*a, **kw)
        if remove:
            return remove_cached
        else: 
            return do_cached 
    return _

