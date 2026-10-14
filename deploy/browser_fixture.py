"""Temporary browser QA user. Never imports credentials or contacts Amazon."""
import sys
from sqlalchemy import select, delete, func
from cli_anything.amazon_ads_ops_workbench.control_plane.settings import Settings
from cli_anything.amazon_ads_ops_workbench.control_plane.database import Database
from cli_anything.amazon_ads_ops_workbench.control_plane.models import User, Account, Task, Token, Session, Audit, ReportRow
from cli_anything.amazon_ads_ops_workbench.control_plane.security import password_hash

db=Database(Settings.load())
username='qa-local-20261014'
with db.sessions.begin() as s:
    user=s.scalar(select(User).where(User.username==username))
    if sys.argv[1]=='seed':
        if user or s.scalar(select(func.count()).select_from(Account)):
            raise RuntimeError('Refuse to create QA fixture on an initialized account workspace')
        s.add(User(username=username,password_hash=password_hash('AdsLocal-QA-20261014!')))
        print('Created temporary isolated browser QA user; no Amazon account configured')
    elif sys.argv[1]=='cleanup':
        if user:
            ids=s.scalars(select(Task.id).where(Task.owner_id==user.id)).all()
            s.execute(delete(ReportRow).where(ReportRow.task_id.in_(ids)))
            for model in (Audit,Task,Token,Account):s.execute(delete(model).where(model.owner_id==user.id))
            s.execute(delete(Session).where(Session.user_id==user.id))
            s.delete(user)
        print('Removed only temporary browser QA user and its owned fixtures')
    else: raise ValueError('seed or cleanup required')
