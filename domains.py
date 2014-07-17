# -*- coding:utf-8 -*-
'''
zzz domains
'''
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from sqlalchemy import Table, Column, ForeignKey, MetaData
from sqlalchemy import Integer, Boolean
from sqlalchemy import Unicode, UnicodeText, DateTime
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

metadata = MetaData()
Base = declarative_base()
Base.metadata = metadata

class Option(Base):
    '''配置表'''
    __tablename__ = 'option'
    name = Column('option_name', Unicode(200), 
        primary_key=True, nullable=False, unique=True,
        index=True)
    value = Column('option_value', UnicodeText, nullable=False)
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return "<Option('%s')" % self.name

#关联表
post_tag = Table('post_tag', Base.metadata,
    Column('post_id', Integer, ForeignKey('post.id'), index=True),
    Column('tag_id', Integer, ForeignKey('tag.id'), index=True)
)

class Post(Base):
    '''正文表'''
    __tablename__ = 'post'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    url = Column(Unicode(200), nullable=False, unique=True, index=True)
    title = Column(Unicode(200), nullable=False)
    content = Column(UnicodeText, nullable=False)
    ispass = Column(Boolean, nullable=False, index=True)
    pubdate = Column(DateTime, index=True)
    pubyear = Column(Integer, index=True)
    pubmonth = Column(Integer, index=True)
    commentnum = Column(Integer)
    commentpass = Column(Integer)
    taglist = Column(Unicode(500))

    def __init__(self, url, title, content, ispass, pubdate, user):
        self.url = url
        self.title = title
        self.content = content 
        self.ispass = ispass
        self.pubdate = pubdate
        self.pubyear = pubdate.year
        self.pubmonth = pubdate.month
        self.user = user

    tags = relationship("Tag",
                    secondary=post_tag,
                    backref="posts")
    comments = relationship("Comment", 
            backref="post")

import hashlib
class User(Base):
    '''用户表'''
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True, index=True)
    username = Column(Unicode(200), unique=True, nullable=False, index=True)
    pwd = Column(Unicode(200), nullable=False)
    nickname = Column(Unicode(200), unique=True, nullable=False, index=True)
    mail = Column(Unicode(200), nullable=False)
    posts = relationship("Post", 
            backref="user")

    commnets = relationship("Comment", 
            backref="user")
    def __init__(self, username, pwd, mail):
        self.username = username
        self.nickname = username
        m = hashlib.md5()
        m.update(pwd)
        self.pwd = unicode(m.hexdigest(), 'utf-8')
        self.mail = mail

class Comment(Base):
    '''评论表'''
    __tablename__ = 'comment'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True, index=True)
    username = Column(Unicode(200), nullable=False)
    mail = Column(Unicode(200), nullable=False)
    site = Column(Unicode(200))
    comment = Column(Unicode(1000), nullable=False)
    ispass = Column(Boolean, nullable=False, index=True)
    isshowsite = Column(Boolean, nullable=False)
    ip = Column(Unicode(200), nullable=True)
    adddate = Column(DateTime, nullable=False, index=True)
    ##notify = Column(Boolean, nullable=True)

    def __init__(self, post, user, username, mail, site, 
            comment, ispass, adddate):
        self.post = post
        self.user = user
        self.username = username
        self.mail = mail
        self.site = site
        self.comment = comment
        self.ispass = ispass
        self.isshowsite = False 
        self.adddate = adddate

class Tag(Base):
    '''标签表'''
    __tablename__ = 'tag'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True, index=True)
    tag = Column(Unicode(200), nullable=False, unique=True, index=True)
    nums = Column(Integer, nullable=False, index=True)
    def __init__(self, tag, nums=0):
        self.tag = tag
        self.nums = nums

def update_all_count(db):
    '''更新统计量'''
    count = db.query(func.count(Post.id)).\
        filter(Post.ispass == True).scalar()
    update_option(db, u'posts_available', count)

    count = db.query(func.count(Post.id)).\
        scalar()
    update_option(db, u'posts_total', count)

    count = db.query(func.count(Comment.id)).\
        filter(Comment.ispass == True).scalar()
    update_option(db, u'comments_available', count)

    count = db.query(func.count(Comment.id)).\
        scalar()
    update_option(db, u'comments_total', count)

    count = db.query(func.count(Tag.id)).\
        scalar()
    update_option(db, u'tags_total', count)

def get_post_tags(db, tags):
    results = []
    for t in tags:
        tag = db.query(Tag).\
            filter(Tag.tag==t.tag).\
            first()
        if not tag:
            db.add(t)
            results.append(t)
        else:
            results.append(tag)
    return results

def update_post_tags(db, post_id, tags, oldtags):
    #删除的
    names = [x.tag for x in tags]
    deletes = [o for o in oldtags if o.tag not in names]
    for o in deletes:
        ptag = db.query(post_tag).\
            filter(post_tag.c.tag_id==o.id).\
            first()
        if ptag:
            print '===================='
            print ptag
            db.delete(ptag)
    #更新统计
    alls = tags + [o for o in oldtags if o.tag not in names]
    return alls
    #for x in alls:
    #    update_tag_post(db, x.id)

def update_post_count(db, post_id):
    '''更新文章的统计量'''
    comment_count = db.query(func.count(Comment.id)).\
        filter(Comment.post_id==post_id).\
        scalar()
    comment_pass= db.query(func.count(Comment.id)).\
        filter(Comment.post_id==post_id).\
        filter(Comment.ispass==True).\
        scalar()
    db.query(Post).\
        filter(Post.id==post_id).\
        update({
            Post.commentnum:comment_count,
            Post.commentpass:comment_pass
            })
    return comment_count

def update_option(db, name, value):
    count = db.query(Option).\
        filter(Option.name == name).first()
    if not count:
        count = Option(name, None)
    count.value = unicode(str(value), 'utf8')
    db.add(count)

def update_post_commentnum(db):
    '''更新所有文章的评论数量'''
    post_ids = db.query(Comment.post_id).\
        distinct().all()
    if post_ids:
        post_ids = [x[0] for x in post_ids]
    for post_id in post_ids:
        comment_count = update_post_count(db, post_id)
        print '\r updating: \t post_id:%d comments: %d' \
            % (post_id, comment_count),
    db.commit()
    print '\r\n',
    print ' total : %s' % len(post_ids)
    print '\r\n',

def update_tag_post(db, tag_id):
    '''更新Tag的文章数量'''
    count = db.query(func.count(post_tag.c.post_id)).\
            filter(post_tag.c.tag_id==tag_id).\
            filter(Post.ispass==True).\
            filter(Post.id==post_tag.c.post_id).\
            scalar()
    db.query(Tag).\
            filter(Tag.id==tag_id).\
            update({Tag.nums:count})
    return count

#更新月份记录文章记录
import datetime
import cPickle
def update_db_month(db):
    '''update_db_month'''
    pubdate_max = db.query(Post.pubdate).\
            filter(Post.ispass==True).\
            order_by(Post.pubdate.desc()).first()
    pubdate_min = db.query(Post.pubdate).\
            filter(Post.ispass==True).\
            order_by(Post.pubdate).first()
    if pubdate_max:
        pubdate_max = pubdate_max[0]
    if pubdate_min:
        pubdate_min = pubdate_min[0]
    update_archives_count(db, pubdate_min, pubdate_max)

def min_max_months(min_date, max_date):
    '''get all month time ranges'''
    year_months = []
    if min_date > max_date:
        return year_months
    for year in range(min_date.year, max_date.year+1):
        for month in range(1, 13):
            if year == min_date.year and month < min_date.month:
                pass
            elif year == max_date.year and month > max_date.month:
                pass
            else:
                month_range = get_month_range(year, month)
                year_months.append(month_range)
    return year_months

def get_month_range(year, month):
    '''get_month_range'''
    month_first = datetime.datetime(year, month, 1, 0, 0, 0)
    time_delta = datetime.timedelta(microseconds=1)
    if month == 12:
        month_last = datetime.datetime(year + 1, 1, 1) - time_delta
    else:
        month_last = datetime.datetime(year, month + 1, 1) - time_delta
    return month_first, month_last

def update_archives_count(db, min_date, max_date):
    '''更新小月到大月之间的文章数'''
    #get months
    year_months = min_max_months(min_date, max_date)
    #print year_months
    month_counts = {}
    #print 'year_months:', year_months
    for x in year_months:
        #print 'year_months -- x:', x 
        #filter(Post.pubdate.between(x[0], x[1])).\
        #print '\r update month: \t %d-%d' % (x[0].year, x[0].month),
        post_count = db.query(func.count(Post.id)).\
            filter(Post.ispass==True).\
            filter(Post.pubyear==x[0].year).\
            filter(Post.pubmonth==x[0].month).\
            scalar()
        if post_count:
            month_counts[x[0]] = post_count
    #print '\r\n',
    if month_counts:
        option_name = u'site_archives_count'
        count1 = db.query(Option).\
            filter(Option.name == option_name).first()
        db_vals = {}
        if not count1:
            count1 = Option(option_name, None)
        else:
            try:
                db_vals = cPickle.loads(str(count1.value))
            except cPickle.UnpicklingError :
                pass
        db_vals.update(month_counts)
        option_value = cPickle.dumps(db_vals)
        count1.value = unicode(option_value, 'utf8')
        db.add(count1)

def get_archives_count(db):
    '''get archives count'''
    name1 = u'site_archives_count'
    counts = db.query(Option).\
        filter(Option.name == name1).first()
    db_vals = {}
    if counts and counts.value:
        try:
            db_vals = cPickle.loads(str(counts.value))
        except cPickle.UnpicklingError :
            pass
    return db_vals

from utils import cached, get_int

@cached(cache_key='site_info')
def load_info(db):
    d = {}
    #配置表
    options = db.query(Option).all()
    for x in options:
        d[x.name] = x.value
    posts_available = get_int(d.get('posts_available',''), -1)
    posts_total = get_int(d.get('posts_total',''), -1)
    if posts_available == -1: 
        posts_available = db.query(func.count(Post.id)).\
            filter(Post.ispass == True).\
            scalar()

    if posts_total== -1: 
        posts_total= db.query(func.count(Post.id)).\
            scalar()

    d['posts_available'] = posts_available
    d['posts_total'] = posts_total

    # archive
    archives_count = get_archives_count(db)
    d['archives_count'] = archives_count
    return d
