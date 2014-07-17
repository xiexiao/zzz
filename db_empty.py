# -*- coding:utf-8 -*-
'''
zzz db tool
'''
import sys

from sqlalchemy import func
from domains import Post, Option, Tag, Comment, post_tag

import os
import random
import datetime
import domains
from sqlalchemy import create_engine
from domains import User
def get_session(echo=False, create_db=False):
    '''get session'''
    dbfile = 'empty.db'
    if create_db:
        if os.path.isfile(dbfile):os.unlink(dbfile)
    engine = create_engine('sqlite:///' + dbfile,
      convert_unicode=True,
      encoding='utf-8',
      echo=echo,
      )

    if create_db:
        from domains import metadata
        metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def create_emptydb():
    '''创建空的数据库'''
    db = get_session(create_db=True)
    initdb(db)
    db.commit()
    db.close()

def initdb(db):
    u = User(u'admin', u'admin123', u'admin@123.com')
    db.add(u)

    op1 = Option(u'site_name', u'My test site')
    db.add(Option(u'site_url', u'http://localhost:8080/'))
    op2 = Option(u'site_description', u'This is a test site.')
    op3 = Option(u'site_keywords',
            u'test, site, python')
    db.add(op1)
    db.add(op2)
    db.add(op3)

    db.add(Option(u'posts_pagesize', u'5'))
    db.add(Option(u'rss_size', u'10'))
    db.add(Option(u'comments_pagesize', u'10'))

    pubdate = datetime.datetime.now()
    post = Post(u'test1', u'test post', u'test post content', True,
            pubdate, u)
    db.add(post)

    domains.update_all_count(db) 
    domains.update_post_count(db, post.id) 
    domains.update_db_month(db)
    return u

if __name__ == '__main__':
    print '=== create emptydb start ==='
    create_emptydb()
    print '=== create emptydb end ==='

