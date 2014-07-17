# -*- coding:utf-8 -*-
'''
handler
'''
import tornado
import hashlib

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import contains_eager

from domains import Post, Option, Tag, Comment, post_tag, User
from domains import load_info
from utils import dbhook, route, cached
from handlers import BaseHandler

import utils
import domains

class AdminHandler(BaseHandler):
    def initialize(self):
        super(AdminHandler, self).initialize()
        self.admin_page = True

    def get_current_user(self):
        user = self.get_secure_cookie('user')
        if not user:
            return None
        return tornado.escape.json_decode(user)

    def get_login_url(self):
        return u"/admin/login"

    def get_flash(self):
        flash = self.get_secure_cookie('flash')
        self.clear_cookie('flash')
        if not flash:
            return None
        return tornado.escape.json_decode(flash)

    def set_flash(self, msg):
        self.set_secure_cookie('flash', tornado.escape.json_encode(msg))

@route(r'/admin/login', name='za.login')
class Login(AdminHandler):
    def get(self):
        d = {}
        d['flash'] = self.get_flash()
        self.render('login.html', **d)

    @dbhook(read_only=True)
    def post(self):
        name = self.get_argument("user", "")
        pwd = self.get_argument("pass", "")
        remember = self.get_argument("remember", "")
    
        db = self.db 
        user = db.query(User).\
            filter(User.username==name).\
            first()
        m = hashlib.md5()
        m.update(pwd)

        md5_pwd = unicode(m.hexdigest(), 'utf-8')
        if user and user.pwd and md5_pwd == user.pwd:
            expires_days = None
            if remember:
                expires_days = 30
            self.set_current_user(name, expires_days)
            self.redirect("/admin/")
        else:
            self.set_flash({'error': True, 'msg': u"登录失败"})
            self.redirect(u"/admin/login")
    def set_current_user(self, user, expires_days = None):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user),
                    expires_days)
        else:
            self.clear_cookie("user")

@route(r'/admin/logout', name='za.logout')
class Logout(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(u"/admin/login")

@route(r'/admin', name='za.index')
class AdminIndex(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self):
        is_update = self.get_argument("update_count", None)
        db = self.db 
        if is_update != None:
            import domains
            domains.update_all_count(db)
            db.commit()
            self.set_flash({'error': False, 'msg': u"更新统计成功"})
            self.redirect(u"/admin")
        d = load_info(db)
        d['user_name'] = self.get_current_user()
        d['flash'] = self.get_flash()
        self.render('index.html', **d)

@route(r'/admin/settings', name='za.settings')
class AdminSettings(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self):
        db = self.db 
        d = load_info(db)
        d['user_name'] = self.get_current_user()
        d['flash'] = self.get_flash()
        self.render('settings.html', **d)

    @tornado.web.authenticated
    @dbhook(read_only=False)
    @cached(cache_key='site_info', remove=True)
    def post(self):
        db = self.db 
        site_name = self.get_argument("site_name", "")
        site_url = self.get_argument("site_url", "")
        site_keywords = self.get_argument("site_keywords", "")
        site_description = self.get_argument("site_description", "")

        posts_pagesize = utils.get_int(
                self.get_argument("posts_pagesize", ""), 10)
        comments_pagesize = utils.get_int(
                self.get_argument("comments_pagesize", ""), 10)
        rss_size = utils.get_int(self.get_argument("rss_size", ""), 10)

        domains.update_option(db, "site_name", site_name)
        domains.update_option(db, "site_url", site_url)
        domains.update_option(db, "site_keywords", site_keywords)
        domains.update_option(db, "site_description", site_description)

        domains.update_option(db, "posts_pagesize", posts_pagesize)
        domains.update_option(db, "comments_pagesize", comments_pagesize)
        domains.update_option(db, "rss_size", rss_size)
        db.commit()
        self.set_flash({'error': False, 'msg': u"更新成功"})
        self.redirect(u"/admin/settings")

@route(r'/admin/profile', name='za.profile')
class AdminProfile(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self):
        db = self.db 
        name = self.get_current_user()
        user = db.query(User).\
            filter(User.username==name).\
            first()
        d = {}
        d['user_name'] = name
        d['user_nickname'] = user.nickname 
        d['user_mail'] = user.mail
        f = self.get_flash()
        d['flash'] = f
        self.render('profile.html', **d)

    @tornado.web.authenticated
    @dbhook(read_only=False)
    def post(self):
        db = self.db 
        name = self.get_current_user()
        
        nickname = self.get_argument("user_nickname", "")
        pwd = self.get_argument("pass", "")
        new_pwd = self.get_argument("new_pass", "")
        mail = self.get_argument("user_mail", "")
        if not mail:
            self.set_flash({'error': True, 'msg': u"邮件地址不能为空"})
            self.redirect(u"/admin/profile")
            return
        if not nickname:
            self.set_flash({'error': True, 'msg': u"RSS显示名不能为空"})
            self.redirect(u"/admin/profile")
            return

        user = db.query(User).\
            filter(User.username==name).\
            first()

        if new_pwd and not pwd:
            self.set_flash({'error': True, 'msg': u"请输入原密码"})
            self.redirect(u"/admin/profile")
            return
        elif new_pwd and pwd:
            #修改密码
            m = hashlib.md5()
            m.update(pwd)
            md5_pwd = unicode(m.hexdigest(), 'utf-8')

            if user.pwd != md5_pwd:
                self.set_flash({'error': True, 'msg': u"原密码错误"})
                self.redirect(u"/admin/profile")
                return
            m1 = hashlib.md5()
            m1.update(new_pwd)
            user.pwd = unicode(m1.hexdigest(), 'utf-8')
        user.nickname = nickname
        user.mail = mail
        db.add(user)
        db.commit()
        self.set_flash({'error': False, 'msg': u"更新成功"})
        self.redirect(u"/admin/profile")

@route(r'/admin/posts', name='za.posts')
@route(r'/admin/posts/page([0-9]{1,6})', name='za.posts_page')
class AdminPosts(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self, page_current=1):
        db = self.db 
        d = {}
        d['user_name'] = self.get_current_user()
        d['flash'] = self.get_flash()
        page_size = 10
        page_current = utils.get_int(page_current, 1)
        start_index = page_size * (page_current-1)
        total_count = db.query(func.count(Post.id)).\
            scalar()
        page_count = utils.get_pagecount(total_count, page_size)
        items = db.query(Post).\
            order_by(Post.id.desc())[start_index:start_index+page_size]
        start_last = start_index + len(items)
        d['start_index'] = start_index
        d['start_last'] = start_last
        d['total_count'] = total_count
        d['page_count'] = page_count
        d['page_current'] = page_current 
        d['posts'] = items
        self.render('posts.html', **d)


@route(r'/admin/posts_new', name='za.posts_new')
@route(r'/admin/posts_edit,([0-9]{1,6})', name='za.posts_edit')
class AdminPostsEdit(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self, pid=0):
        db = self.db 
        d = {}
        user_name= self.get_current_user()
        if pid >0:
            post =  db.query(Post).\
                filter(Post.id == int(pid)).\
                first()
            if post:
                d['post'] = post
            else:
                self.set_flash({'error': True, 'msg': u"没有该文章"})
                self.redirect(u"/admin/posts")
                return
        else:
            #新的文章
            pubdate = datetime.now()
            post = Post(u'', u'', u'', True, pubdate, None)
            post.taglist = ''
            d['post'] = post
        d['user_name'] = user_name 
        d['pid'] = pid
        d['flash'] = self.get_flash()
        self.render('posts_edit.html', **d)       
        
    @tornado.web.authenticated
    @dbhook(read_only=False, auto_commit=False)
    @cached(cache_key='site_info', remove=True)
    def post(self, pid=0):
        db = self.db 
        msg = u"添加成功"
        user_name= self.get_current_user()

        title = self.get_argument("title", "")
        if not title or len(title.strip())==0:
            self.finish({'error': True, 'msg': u"请输入标题"})
            return
        url = self.get_argument("url", "")
        if not url or len(url.strip())==0:
            self.finish({'error': True, 'msg': u"请输入地址"})
            return

        if pid >0:
            msg = u'修改成功'
            post =  db.query(Post).\
                filter(Post.id == int(pid)).\
                first()
            if not post:
                self.finish({'error': True, 'msg': u"没有该文章"})
                return
            #地址是否已经存在
            item = db.query(Post).\
                filter(Post.id != int(pid)).\
                filter(Post.url == url).\
                first()
            if item:
                self.finish({'error': True, 'msg': u"地址已经存在"})
                return
        else:
            pubdate = datetime.now()
            user = db.query(User).\
                filter(User.username==user_name).\
                first()
            post = Post(u'', u'', u'', True, pubdate, user)
            #地址是否已经存在
            item = db.query(Post).\
                filter(Post.url == url).\
                first()
            if item:
                self.finish({'error': True, 'msg': u"地址已经存在"})
                return
        taglist = self.get_argument("taglist", "")
        content = self.get_argument("content", "")
        if not content or len(content.strip())==0:
            self.finish({'error': True, 'msg': u"请输入内容"})
            return
        ispass = self.get_argument("ispass", None) 
        post.ispass = False
        if ispass and ispass.lower()=='true':
            post.ispass = True
        post.title = title
        post.url = url
        post.content = content
        tags = []
        oldtags = []
        if taglist:
            tags = [Tag(unicode(str(x), 'utf8')) for x in taglist.split('|') if len(x.strip())>0]
            tags = domains.get_post_tags(db, tags)
        if post.tags:
            oldtags = post.tags
        post.taglist = ""
        if tags:
            post.taglist = '|'.join([t.tag for t in tags])

        inputdate = self.get_argument("pubdate", "")
        try:
            pubdate = datetime.strptime(inputdate, '%Y-%m-%d %H:%M')
        except:
            pass
        post.pubdate = pubdate
        post.tags = tags
        db.add(post)
        domains.update_all_count(db) #更新统计信息
        alltags = domains.update_post_tags(db, post.id, tags, oldtags) #更新tag相关, 新旧tag都要
        domains.update_db_month(db)#更新日期统计
        domains.update_post_count(db, post.id)
        db.commit()
        for t in alltags:
            domains.update_tag_post(db, t.id)
        db.commit()
        if pid > 0:
            self.finish({'error': False, 'msg': u"修改成功"})
            return
        else:
            new_url = u"/admin/posts_edit,%d" % (post.id, )
            self.set_flash({'error': False, 'msg': u"添加成功"})
            self.finish({'error': False, 'url':True, 'msg': new_url})

@route(r'/admin/comments', name='za.comments')
@route(r'/admin/comments/page([0-9]{1,6})', name='za.comments_page')
class AdminComments(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self, page_current=1):
        db = self.db 
        d = {}
        d['user_name'] = self.get_current_user()
        d['flash'] = self.get_flash()
        page_size = 10
        page_current = utils.get_int(page_current, 1)
        start_index = page_size * (page_current-1)
        total_count = db.query(func.count(Comment.id)).\
            scalar()
        page_count = utils.get_pagecount(total_count, page_size)
        items = db.query(Comment).\
            join(Comment.post).\
            options(contains_eager(Comment.post)).\
            order_by(Comment.id.desc())[start_index:start_index+page_size]
        start_last = start_index + len(items)
        d['start_index'] = start_index
        d['start_last'] = start_last
        d['total_count'] = total_count
        d['page_count'] = page_count
        d['page_current'] = page_current 
        d['comments'] = items
        self.render('comments.html', **d)

@route(r'/admin/comments_dopass,([0-9]{1,6})', name='za.comments_dopass')
class AdminCommentsDopass(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=False)
    @cached(cache_key='site_info', remove=True)
    def get(self, cid=0):
        db = self.db 
        comment =  db.query(Comment).\
            filter(Comment.id == int(cid)).\
            first()
        if comment:
            comment.ispass = not comment.ispass
            db.add(comment)
            domains.update_all_count(db)
            db.commit()
            self.set_flash({'error': False, 'msg': u"修改成功"})
            self.redirect(u"/admin/comments")
        else:
            self.set_flash({'error': True, 'msg': u"找不到该评论"})
            self.redirect(u"/admin/comments")

@route(r'/admin/comments_delete,([0-9]{1,6})', name='za.comments_delete')
class AdminCommentsDelete(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=False)
    @cached(cache_key='site_info', remove=True)
    def get(self, cid=0):
        db = self.db 
        comment = db.query(Comment).\
            filter(Comment.id == int(cid)).\
            first()
        if comment:
            db.delete(comment)
            domains.update_all_count(db)
            db.commit()
            self.set_flash({'error': False, 'msg': u"删除成功"})
            self.redirect(u"/admin/comments")
        else:
            self.set_flash({'error': True, 'msg': u"找不到该评论"})
            self.redirect(u"/admin/comments")

@route(r'/admin/tags', name='za.tags')
@route(r'/admin/tags/page([0-9]{1,6})', name='za.tags_page')
class AdminTags(AdminHandler):
    @tornado.web.authenticated
    @dbhook(read_only=True)
    def get(self, page_current=1):
        db = self.db 
        d = {}
        d['user_name'] = self.get_current_user()
        d['flash'] = self.get_flash()
        tag_page_size = 10
        tag_page_current = utils.get_int(page_current, 1)
        start_index = tag_page_size * (tag_page_current-1)
        tag_count = db.query(func.count(Tag.id)).\
            scalar()
        tag_page_count = utils.get_pagecount(tag_count, tag_page_size)
        tags = db.query(Tag).\
            order_by(Tag.id.desc())[start_index:start_index+tag_page_size]
        start_last = start_index + len(tags)
        d['start_index'] = start_index
        d['start_last'] = start_last
        d['total_count'] = tag_count
        d['page_count'] = tag_page_count
        d['page_current'] = tag_page_current 
        d['tags'] = tags

        self.render('tags.html', **d)
