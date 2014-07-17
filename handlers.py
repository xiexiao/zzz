# -*- coding:utf-8 -*-
'''
handler
'''
import datetime
import tornado
import domains
import utils

from sqlalchemy import func
from domains import Post, Option, Tag, Comment, post_tag
from domains import load_info
from utils import dbhook, route 

class BaseHandler(tornado.web.RequestHandler):
    '''BaseHandler'''
    def initialize(self):
        self.lookup = self.application.lookup
        self.db = None
        self.admin_page = False

    def render_html(self, filename, **kwargs):
        '''
            Override render_html to use mako template.
            Like tornado render_string method, this method
            also pass request handler environment to template engin.
        '''
        theme_name = 'default'
        if self.admin_page:
            theme_name = '_admin'
        filename = theme_name + '/' + filename
        template = self.lookup.get_template(filename)
        db_query_times = None
        if self and hasattr(self, 'db') and self.db:
            conn = self.db.connection()
            if hasattr(conn, 'db_query_times'):
                db_query_times = conn.db_query_times
        env_kwargs = {
            'handler' : self,
            'request' : self.request,
            'current_user' : self.current_user,
            'locale' : self.locale,
            '_' : self.locale.translate,
            'static_url' : self.static_url,
            'xsrf_form_html' : self.xsrf_form_html,
            'reverse_url' : self.application.reverse_url,

            'db_query_times': db_query_times,
            'theme_name': theme_name,

            'debug': self.application.settings.get('debug', False)
        }
        env_kwargs.update(kwargs)
        return template.render(**env_kwargs)

    def render(self, filename, **kwargs):
        self.finish(self.render_html(filename, **kwargs))

    def write_error(self, status_code, **kwargs):
        is_debug = self.application.settings.get('debug', False)
        if is_debug: 
            import traceback
            if self.settings.get("debug") and "exc_info" in kwargs:
                exc_info = kwargs["exc_info"]
                trace_info = ''.join(["%s<br/>" % line for line in traceback.format_exception(*exc_info)])
                request_info = ''.join(["<strong>%s</strong>: %s<br/>" % (k, self.request.__dict__[k] ) for k in self.request.__dict__.keys()])
                error = exc_info[1]
            
                self.set_header('Content-Type', 'text/html')
                self.finish("""<html>
                             <title>%s</title>
                             <body>
                                <h2>Error</h2>
                                <p>%s</p>
                                <h2>Traceback</h2>
                                <p>%s</p>
                                <h2>Request Info</h2>
                                <p>%s</p>
                             </body>
                           </html>""" % (error, error, 
                                        trace_info, request_info)
                )
        else:
            if status_code in [403, 404, 500, 503]:
                self.write('Error %s' % status_code)
            else:
                self.write('BOOM! %s' % status_code)
            self.finish()

    @classmethod 
    def notfound(cls):
        '''not found'''
        raise tornado.web.HTTPError(404)

@route(r'/', name='z.Index')
@route(r'/page([0-9]{1,6})', name='z.IndexPage')
class IndexHandler(BaseHandler):
    '''首页'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self, page_current=1):
        db = self.db
        d = load_info(db).copy()
        page_size = utils.get_int(d.get('posts_pagesize', ''), 10)
        page_current = utils.get_int(page_current, 1)
        start_index = page_size * (page_current-1)
        posts_count = d['posts_available']
        page_count = utils.get_pagecount(posts_count, page_size)
        if posts_count < 1:
            self.finish("<p>No any posts</p>")
            return
        elif page_current > page_count or page_current < 1:
            pass
        else:
            if posts_count > 0:
                post_ids = db.query(Post.id).\
                    filter(Post.ispass == True).\
                    order_by( 
                        Post.pubdate.desc()
                    )[start_index:start_index+page_size]
                ids = (x[0] for x in post_ids)
                d['posts'] = db.query(Post).\
                    filter(Post.id.in_(ids)).\
                    order_by(Post.pubdate.desc()).\
                    all()
            d['page_count'] = page_count
            d['page_current'] = page_current
            return self.render('index.html', **d)
        self.notfound()

@route(r'/archives', name='z.Archives')
class Archives(BaseHandler):
    '''Archives'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self):
        db = self.db
        d = load_info(db).copy()
        return self.render('archives.html', **d)

@route(r'/archives/([0-9]{4})-([0-9]{1,2})', name='z.ArchivesList')
@route(r'/archives/([0-9]{4})-([0-9]{1,2})/page([0-9]{1,6})',
        name='z.ArchivesListPage')
class ArchivesList(BaseHandler):
    '''ArchivesList'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self, year, month, page_current=1):
        db = self.db
        d = load_info(db).copy()
        year = utils.get_int(year)
        month = utils.get_int(month)
        first_day = None
        if 13 > month > 0:
            first_day = datetime.datetime(year, month, 1)
        if first_day in d['archives_count']:
            archive_posts_count = d['archives_count'][first_day]
            if archive_posts_count is None: 
                archive_posts_count = 0
            archive_page_size = utils.get_int(d.get('posts_pagesize', ''), 10)
            page_current = utils.get_int(page_current, 1)
            start_index = archive_page_size * (page_current-1)
            archive_page_count = utils.get_pagecount(archive_posts_count,
                archive_page_size)
            if page_current > archive_page_count or page_current < 1:
                pass
            elif archive_posts_count > 0:
                post_ids = db.query(Post.id).\
                    filter(Post.ispass==True).\
                    filter(Post.pubyear==year).\
                    filter(Post.pubmonth==month).\
                    order_by( 
                        Post.id.desc()
                    )[start_index:start_index+archive_page_size]
                ids = (x[0] for x in post_ids)
                d['post_list'] = db.query(Post).\
                    filter(Post.id.in_(ids)).\
                    all()
                d['post_page_count'] = archive_page_count
                d['post_page_current'] = page_current
                d['mode_type'] = 'archive' 
                d['first_day'] = first_day 
                return self.render('list.html', **d)
        self.notfound()

@route(r'/tags', name='z.Tags')
@route(r'/tags/page([0-9]{1,6})', name='z.TagsPage')
class Tags(BaseHandler):
    '''Tags'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self, page_current=1):
        db = self.db
        d = load_info(db).copy()
        tag_page_size = 100
        tag_page_current = utils.get_int(page_current, 1)
        start_index = tag_page_size * (tag_page_current-1)
        tag_count = db.query(func.count(Tag.id)).\
            filter(Tag.nums>0).\
            scalar()
        tag_page_count = utils.get_pagecount(tag_count, tag_page_size)
        tag_max_nums = 1
        tag_maxs = db.query(Tag).\
            order_by(Tag.nums.desc())[:1]
        if tag_maxs and len(tag_maxs) == 1:
            tag_max_nums = tag_maxs[0].nums
        tags = db.query(Tag).\
            filter(Tag.nums>0).\
            order_by(Tag.id.desc())[start_index:start_index+tag_page_size]
        d['tag_max_nums'] = tag_max_nums
        d['tag_count'] = tag_count
        d['tag_page_count'] = tag_page_count
        d['tag_page_current'] = tag_page_current 
        d['tags'] = tags
        return self.render('tags.html', **d)

@route(r'/tags/([^.///?]+)', name='z.TagsList')
@route(r'/tags/([^.///?]+)/page([0-9]{1,6})', name='z.TagsListPage')
class TagsList(BaseHandler):
    '''TagsList'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self, tag_name, page_current=1):
        db = self.db
        d = load_info(db).copy()
        tag = db.query(Tag).\
            filter(Tag.tag==tag_name).\
            scalar()
        if not tag:
            self.notfound()
        d['tag_item'] = tag
        tag_posts_count = tag.nums 
        if tag_posts_count is None: 
            tag_posts_count = 0
        tag_page_size = utils.get_int(d.get('posts_pagesize', ''), 10)
        tag_page_current = utils.get_int(page_current, 1)
        start_index = tag_page_size * (tag_page_current-1)
        tag_page_count = utils.get_pagecount(tag_posts_count, tag_page_size)
        if tag_page_current > tag_page_count or tag_page_current < 1:
            pass
        else:
            if tag_posts_count > 0:
                post_ids = db.query(post_tag.c.post_id).\
                    filter(post_tag.c.tag_id==tag.id).\
                    filter(Post.ispass==True).\
                    filter(Post.id==post_tag.c.post_id).\
                    order_by( 
                        Post.pubdate.desc()
                    )[start_index:start_index+tag_page_size]
                ids = [x[0] for x in post_ids]
                d['post_list'] = db.query(Post).\
                    filter(Post.id.in_(ids)).\
                    order_by(Post.pubdate.desc()).\
                    all()
            d['post_page_count'] = tag_page_count
            d['post_page_current'] = tag_page_current
            d['mode_type'] = 'tag' 
            return self.render('list.html', **d)
        self.notfound()

@route(r'/rss', name='z.Rss')
class Rss(BaseHandler):
    '''Rss'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self):
        self.set_header('Content-Type','text/xml')
        db = self.db
        d = load_info(db).copy()
        site_url = d['site_url']
        rss_size = utils.get_int(d.get('rss_size', ''), 10)
        items = []
        last_update = None
        if rss_size > 0:
            postIds = db.query(Post.id).\
                filter(Post.ispass == True).\
                order_by( 
                    Post.id.desc()
                )[0:rss_size]
            postIds = (x[0] for x in postIds)
            posts = db.query(Post).\
                filter(Post.id.in_(postIds)).\
                all()
            for post in posts:
                items.append({
                    'title':post.title,
                    'link': utils.urlwrite(site_url, post.url),
                    'pubDate': post.\
                        pubdate.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'dc:creator': post.user.nickname,
                    'guid':{
                        '_text': utils.urlwrite(site_url, post.url),
                        '__isPermaLink': 'true'
                    },
                    'content:encoded': post.content 
                })
            if posts and len(posts) > 0:
                last_update = posts[0].\
                    pubdate.strftime('%a, %d %b %Y %H:%M:%S GMT')
        xmldict = {'rss': {
            '__version':'2.0',
            '__xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
            '__xmlns:wfw': 'http://wellformedweb.org/CommentAPI/',
            '__xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'channel': {
                'title': d['site_name'],
                'link': d['site_url'],
                'description': d['site_description'],
                'pubDate': last_update,
                'language': 'zh-CN',
                'item': items# end item
            }# end channel 
        }}
        return self.finish(utils.dict_to_xml(xmldict))

@route(r'/([^.///?]+)', name='z.Details', rank=-1)
@route(r'/([^.///?]+)/comment-page([0-9]{1,6})', 
        name='z.DetailsComment', rank=-2)
class Details(BaseHandler):
    '''Details'''
    @tornado.web.asynchronous
    @dbhook(read_only=True)
    def get(self, url, page_current=1):
        db = self.db
        d = load_info(db).copy()
        post = db.query(Post).\
            filter(Post.url== url).\
            filter(Post.ispass == True).\
            first()
        return self.do(db, d, post, page_current)

    def do(self, db, d, post, page_current=1):
        '''do'''
        if post:
            d['post'] = post
            comment_pagesize = utils.get_int(
                d.get('comments_pagesize', ''), 10)
            page_current = utils.get_int(page_current, 1)
            start_index = comment_pagesize * (page_current-1)

            commentpass = post.commentpass
            comments = None
            if commentpass > 0:
                comments = db.query(Comment).\
                    filter(Comment.post_id == post.id).\
                    filter(Comment.ispass==True).\
                    order_by( 
                        Comment.id.desc()
                    )[start_index:start_index + comment_pagesize]
            if comments:
                page_count = utils.get_pagecount(commentpass, 
                    comment_pagesize)
                d['post_comments'] = comments
                d['page_current'] = page_current 
                d['page_count'] = page_count
                d['page_comment_count'] = commentpass 
            return self.render('details.html', **d)
        self.notfound()

    @tornado.web.asynchronous
    @dbhook(read_only=False)
    def post(self, url, page_current=1):
        '''post'''
        db = self.db

        post_id = self.get_argument('id', 0)
        username = self.get_argument('name', None)
        email = self.get_argument('email', None)
        comment = self.get_argument('comment', None)

        url = self.get_argument('site', None)
        if post_id == 0:
            self.finish("<li>id error</li>")
        msg = ''
        if not username:
            msg = msg + "<li>name must input</li>"
        if not email:
            msg = msg + "<li>email must input</li>"
        if not comment:
            msg = msg + "<li>comment must input</li>"
        if msg:
            self.finish(msg)
        
        d = load_info(db).copy()
        post = db.query(Post).\
            filter(Post.id == post_id).\
            filter(Post.ispass == True).\
            first()
        if not post:
            self.finish("<li>id error</li>")
        #save comment
        utcnow = datetime.datetime.utcnow()
        item = Comment(post, None, username,
            email, url, comment,
            False, utcnow 
            )

        #item.ispass = True 
        item.ip = self.request.remote_ip
        db.add(item)
        domains.update_post_count(db, post_id)
        d['msg'] = u'保存成功，需要审核通过才能才网站上显示。'

        return self.do(db, d, post, page_current)
