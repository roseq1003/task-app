import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

class TaskDatabase:
    def __init__(self,path): self.path=Path(path); self._init()
    @contextmanager
    def con(self):
        c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try: yield c;c.commit()
        finally:c.close()
    def now(self):return datetime.now().isoformat(timespec='seconds')
    def _init(self):
        with self.con() as c:c.executescript('''CREATE TABLE IF NOT EXISTS main_tasks(id TEXT PRIMARY KEY,name TEXT,category TEXT,priority TEXT,due_date TEXT,completed INTEGER DEFAULT 0,completed_at TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE IF NOT EXISTS sub_tasks(id TEXT PRIMARY KEY,main_id TEXT,name TEXT,priority TEXT,due_date TEXT,note TEXT,completed INTEGER DEFAULT 0,completed_at TEXT,created_at TEXT,updated_at TEXT,FOREIGN KEY(main_id) REFERENCES main_tasks(id) ON DELETE CASCADE);''')
    def all(self):
        with self.con() as c:ms=[dict(x) for x in c.execute('SELECT * FROM main_tasks ORDER BY completed,due_date')];ss=[dict(x) for x in c.execute('SELECT * FROM sub_tasks ORDER BY completed,due_date')]
        g={}
        for s in ss:g.setdefault(s['main_id'],[]).append(s)
        for m in ms:m['subs']=g.get(m['id'],[])
        return ms
    def add_main(self,n,c,p,d):
        t=self.now()
        with self.con() as x:x.execute('INSERT INTO main_tasks VALUES(?,?,?,?,?,0,NULL,?,?)',(uuid4().hex,n,c,p,d,t,t))
    def edit_main(self,i,n,c,p,d):
        with self.con() as x:x.execute('UPDATE main_tasks SET name=?,category=?,priority=?,due_date=?,updated_at=? WHERE id=?',(n,c,p,d,self.now(),i))
    def add_sub(self,m,n,p,d,note):
        t=self.now()
        with self.con() as x:x.execute('INSERT INTO sub_tasks VALUES(?,?,?,?,?,?,0,NULL,?,?)',(uuid4().hex,m,n,p,d,note,t,t))
    def edit_sub(self,i,n,p,d,note):
        with self.con() as x:x.execute('UPDATE sub_tasks SET name=?,priority=?,due_date=?,note=?,updated_at=? WHERE id=?',(n,p,d,note,self.now(),i))
    def sub_state(self,i,v):
        t=self.now()
        with self.con() as x:x.execute('UPDATE sub_tasks SET completed=?,completed_at=?,updated_at=? WHERE id=?',(v,t if v else None,t,i))
    def restore_sub(self,m,i):
        self.sub_state(i,0)
        with self.con() as x:x.execute('UPDATE main_tasks SET completed=0,completed_at=NULL,updated_at=? WHERE id=?',(self.now(),m))
    def main_done(self,i,subs):
        t=self.now()
        with self.con() as x:
            if subs:x.execute('UPDATE sub_tasks SET completed=1,completed_at=?,updated_at=? WHERE main_id=?',(t,t,i))
            x.execute('UPDATE main_tasks SET completed=1,completed_at=?,updated_at=? WHERE id=?',(t,t,i))
    def restore_main(self,i):
        with self.con() as x:x.execute('UPDATE main_tasks SET completed=0,completed_at=NULL,updated_at=? WHERE id=?',(self.now(),i))
