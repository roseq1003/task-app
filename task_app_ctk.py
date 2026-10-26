import sys
import json
from datetime import date,timedelta
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from tkcalendar import Calendar
from task_database import TaskDatabase

CAT=['メイン業務','改善','事務処理','他'];PRI=['高','中','低']
C={'bg':('#f4f6f8','#10151d'),'card':('#fff','#19212e'),'line':('#dfe5ed','#303b4c'),'text':('#182033','#f1f5f9'),'muted':('#707b8e','#9aa8bb'),'blue':'#438cff','red':'#ff565f','yellow':'#e1a900','green':'#2bc47d','done':('#e8eaed','#252b35')}
def base():return Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
SETTINGS_DEFAULT={'scroll_speed':5,'zoom':100,'density':'標準','add_default':'既存メインへサブ追加','default_due':'1週間後','default_priority':'中','hide_completed':True,'confirm_delete':True}
def settings_path():return base()/'settings.json'
def load_settings():
 try:
  data=json.loads(settings_path().read_text(encoding='utf-8'))
  return {**SETTINGS_DEFAULT,**data}
 except Exception:return SETTINGS_DEFAULT.copy()
def save_settings(data):settings_path().write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def default_due_value(value):
 days={'今日':0,'3日後':3,'1週間後':7,'2週間後':14}.get(value)
 return '' if days is None else (date.today()+timedelta(days=days)).isoformat()
def D(s):return date.fromisoformat(s) if s else None
def pcol(v):return {'高':C['red'],'中':C['yellow'],'低':C['green']}[v]
def due(v):
 if not v:return '期限なし',C['muted']
 d=D(v);t=date.today();we=t+timedelta(days=6-t.weekday())
 if d<t:return f'{(t-d).days}日超過',C['red']
 if d<=we:return d.strftime('%m/%d'),C['green']
 return d.strftime('%Y/%m/%d'),C['muted']

class FastScroll(ctk.CTkScrollableFrame):
 def __init__(self,*a,app=None,**k):self.app=app;super().__init__(*a,**k);self._parent_canvas.bind_all('<MouseWheel>',self.wheel,add='+')
 def wheel(self,e):
  if not self.winfo_exists():return
  x,y=self.winfo_pointerx(),self.winfo_pointery();rx,ry=self.winfo_rootx(),self.winfo_rooty()
  if rx<=x<=rx+self.winfo_width() and ry<=y<=ry+self.winfo_height():self._parent_canvas.yview_scroll((-1 if e.delta>0 else 1)*max(2,int(self.app.settings['scroll_speed'])*3),'units');return 'break'

class Cal(ctk.CTkToplevel):
 def __init__(self,m,v,cb):
  super().__init__(m);self.cb=cb;self.title('日付選択');self.geometry('360x390');self.transient(m);self.grab_set();d=D(v);self.c=Calendar(self,selectmode='day',date_pattern='yyyy-mm-dd',year=d.year,month=d.month,day=d.day,firstweekday='monday',showweeknumbers=False);self.c.pack(fill='both',expand=True,padx=16,pady=16);ctk.CTkButton(self,text='この日を選択',command=self.ok).pack(fill='x',padx=16,pady=(0,16))
 def ok(self):self.cb(self.c.get_date());self.destroy()

class Editor(ctk.CTkToplevel):
 def __init__(self,app,kind='sub',main=None,sub=None,allow_switch=True):
  super().__init__(app);self.app=app;self.kind=kind;self.main=main;self.sub=sub;self.edit=bool(sub or (main and kind=='main'));self.allow_switch=allow_switch;self.title('タスク編集' if self.edit else 'タスク追加');self.geometry('500x580');self.transient(app);self.grab_set();self.grid_columnconfigure(0,weight=1);self.draw()
 def draw(self):
  for w in self.winfo_children():w.destroy()
  b=ctk.CTkFrame(self,fg_color='transparent');b.grid(row=0,column=0,sticky='nsew',padx=24,pady=20);b.grid_columnconfigure(0,weight=1);r=0;ctk.CTkLabel(b,text=self.title(),font=ctk.CTkFont(size=20,weight='bold')).grid(row=r,column=0,sticky='w',pady=(0,10));r+=1
  if not self.edit and self.allow_switch:
   seg=ctk.CTkSegmentedButton(b,values=['既存メインへサブ追加','新規メインタスク'],command=self.switch);seg.set('既存メインへサブ追加' if self.kind=='sub' else '新規メインタスク');seg.grid(row=r,column=0,sticky='ew');r+=1
  if self.kind=='sub':
   self.parents={m['name']:m['id'] for m in self.app.tasks if not m['completed']};self.parent=ctk.CTkOptionMenu(b,values=list(self.parents) or ['追加先なし']);self.parent.grid(row=r,column=0,sticky='ew',pady=8);r+=1
   if self.main:self.parent.set(self.main['name'])
  else:
   q=ctk.CTkFrame(b,fg_color='transparent');q.grid(row=r,column=0,sticky='ew',pady=8);q.grid_columnconfigure((0,1),weight=1);self.cat=ctk.CTkOptionMenu(q,values=CAT);self.cat.grid(row=0,column=0,sticky='ew',padx=(0,4));self.pri=ctk.CTkOptionMenu(q,values=PRI);self.pri.grid(row=0,column=1,sticky='ew',padx=(4,0));self.cat.set(self.main['category'] if self.main else CAT[0]);self.pri.set(self.main['priority'] if self.main else self.app.settings['default_priority']);r+=1
  self.name=ctk.CTkEntry(b,placeholder_text='タスク名',height=38);self.name.grid(row=r,column=0,sticky='ew',pady=8);r+=1
  n=self.sub['name'] if self.sub else (self.main['name'] if self.edit else '')
  if n:self.name.insert(0,n)
  if self.kind=='sub':self.pri=ctk.CTkOptionMenu(b,values=PRI);self.pri.grid(row=r,column=0,sticky='ew',pady=8);self.pri.set(self.sub['priority'] if self.sub else self.app.settings['default_priority']);r+=1
  dv=self.sub['due_date'] if self.sub else (self.main['due_date'] if self.edit else default_due_value(self.app.settings['default_due']));self.dvar=ctk.StringVar(value=dv);q=ctk.CTkFrame(b,fg_color='transparent');q.grid(row=r,column=0,sticky='ew',pady=8);q.grid_columnconfigure(0,weight=1);ctk.CTkEntry(q,textvariable=self.dvar,state='readonly',height=38).grid(row=0,column=0,sticky='ew',padx=(0,6));ctk.CTkButton(q,text='カレンダー',width=100,height=38,command=self.open_calendar).grid(row=0,column=1);r+=1
  if self.kind=='sub':self.note=ctk.CTkTextbox(b,height=120);self.note.grid(row=r,column=0,sticky='ew',pady=8);self.note.insert('1.0',self.sub['note'] if self.sub else '');r+=1
  ctk.CTkButton(b,text='保存',command=self.save).grid(row=r,column=0,sticky='ew',pady=(10,0))
 def switch(self,v):self.kind='main' if v=='新規メインタスク' else 'sub';self.main=None;self.draw()
 def open_calendar(self):
  if not self.dvar.get():self.dvar.set(date.today().isoformat())
  Cal(self,self.dvar.get(),self.dvar.set)
 def save(self):
  n=self.name.get().strip()
  if not n:return messagebox.showwarning('確認','タスク名を入力してください',parent=self)
  if self.kind=='main':self.app.db.edit_main(self.main['id'],n,self.cat.get(),self.pri.get(),self.dvar.get()) if self.edit else self.app.db.add_main(n,self.cat.get(),self.pri.get(),self.dvar.get())
  else:
   note=self.note.get('1.0','end').strip()
   if self.edit:self.app.db.edit_sub(self.sub['id'],n,self.pri.get(),self.dvar.get(),note)
   elif self.parent.get() in self.parents:self.app.db.add_sub(self.parents[self.parent.get()],n,self.pri.get(),self.dvar.get(),note)
   else:return messagebox.showwarning('確認','追加先がありません',parent=self)
  self.destroy();self.app.refresh()

class App(ctk.CTk):
 def __init__(self):
  super().__init__();ctk.set_appearance_mode('system');self.settings=load_settings();ctk.set_widget_scaling(self.settings['zoom']/100);self.db=TaskDatabase(base()/'tasks.db');self.tasks=[];self.page='dash';self.filter='全件';self.notes=set();self.title('タスク管理アプリ');self.geometry('1080x760');self.minsize(820,620);self.configure(fg_color=C['bg']);self.grid_columnconfigure(0,weight=1);self.grid_rowconfigure(1,weight=1);self.header();self.host=ctk.CTkFrame(self,fg_color='transparent');self.host.grid(row=1,column=0,sticky='nsew',padx=18,pady=(0,18));self.host.grid_columnconfigure(0,weight=1);self.host.grid_rowconfigure(0,weight=1);self.refresh()
 def header(self):
  h=ctk.CTkFrame(self,fg_color='transparent');h.grid(row=0,column=0,sticky='ew',padx=22,pady=14);h.grid_columnconfigure(1,weight=1);ctk.CTkLabel(h,text='タスク管理アプリ',font=ctk.CTkFont(size=24,weight='bold')).grid(row=0,column=0);n=ctk.CTkSegmentedButton(h,values=['ダッシュボード','タスク一覧','設定'],command=self.nav);n.set('ダッシュボード');n.grid(row=0,column=1);ctk.CTkButton(h,text='＋ タスク追加',command=lambda:Editor(self,'sub' if self.settings['add_default']=='既存メインへサブ追加' else 'main')).grid(row=0,column=2)
 def nav(self,v):self.page='dash' if v=='ダッシュボード' else ('list' if v=='タスク一覧' else 'settings');self.render()
 def refresh(self):self.tasks=self.db.all();self.render()
 def render(self):
  for w in self.host.winfo_children():w.destroy()
  self.dashboard() if self.page=='dash' else (self.listpage() if self.page=='list' else self.settingspage())
 def titleline(self,p,title,count,color):
  f=ctk.CTkFrame(p,height=38,fg_color='transparent',corner_radius=0);f.pack(fill='x');f.pack_propagate(False);ctk.CTkFrame(f,width=4,fg_color=color,corner_radius=3).pack(side='left',fill='y',pady=5);ctk.CTkLabel(f,text=title,text_color=color if title!='残件' else C['text'],font=ctk.CTkFont(size=14,weight='bold')).pack(side='left',padx=11);ctk.CTkLabel(f,text=f'{count}件',text_color=C['muted'],font=ctk.CTkFont(size=11)).pack(side='right',padx=8);ctk.CTkFrame(p,height=1,fg_color=C['line']).pack(fill='x')
 def pill(self,p,t,color):ctk.CTkLabel(p,text=t,text_color=color,fg_color=C['bg'],corner_radius=5,padx=6,pady=2,font=ctk.CTkFont(size=11,weight='bold')).pack(side='left',padx=(0,5))
 def dashboard(self):
  p=FastScroll(self.host,app=self,fg_color='transparent',corner_radius=0);p.grid(row=0,column=0,sticky='nsew');rows=[(m,s) for m in self.tasks if not m['completed'] for s in m['subs'] if not s['completed']];t=date.today();we=t+timedelta(days=6-t.weekday());ns=we+timedelta(days=1);ne=ns+timedelta(days=6)
  for title,color,pred in [('期限切れ',C['red'],lambda d:d is not None and d<t),('今週',C['green'],lambda d:d is not None and t<=d<=we),('来週',C['blue'],lambda d:d is not None and ns<=d<=ne),('残件',C['muted'],lambda d:True)]:
   a=[x for x in rows if pred(D(x[1]['due_date']))];self.titleline(p,title,len(a),color)
   if not a:ctk.CTkLabel(p,text='該当タスクはありません。',text_color=C['muted'],anchor='w').pack(fill='x',padx=15,pady=(9,16))
   for m,s in a:self.subrow(p,m,s,True)
   ctk.CTkFrame(p,height=14,fg_color='transparent').pack()
 def subrow(self,p,m,s,dash=False):
  f=ctk.CTkFrame(p,fg_color='transparent',corner_radius=0);f.pack(fill='x');f.grid_columnconfigure(0,weight=1);i=ctk.CTkFrame(f,fg_color='transparent');i.grid(row=0,column=0,sticky='ew',padx=14,pady={'コンパクト':7,'標準':12,'ゆったり':18}[self.settings['density']]);ctk.CTkLabel(i,text=s['name'],font=ctk.CTkFont(size=14,weight='bold')).pack(anchor='w')
  if dash:ctk.CTkLabel(i,text=f"メインタスク：{m['name']}",text_color=C['muted'],font=ctk.CTkFont(size=11)).pack(anchor='w')
  q=ctk.CTkFrame(i,fg_color='transparent');q.pack(anchor='w',pady=(5,0));self.pill(q,f"重要度 {s['priority']}",pcol(s['priority']));x,c=due(s['due_date']);self.pill(q,'完了済み' if s['completed'] else x,C['muted'] if s['completed'] else c)
  a=ctk.CTkFrame(f,fg_color='transparent');a.grid(row=0,column=1,padx=10,pady=10)
  if dash:ctk.CTkButton(a,text='備考',width=55,height=28,fg_color='transparent',border_width=1,command=lambda:self.toggle(s['id'])).pack(side='left',padx=2)
  ctk.CTkButton(a,text='編集',width=55,height=28,fg_color='transparent',border_width=1,command=lambda:Editor(self,'sub',m,s,False)).pack(side='left',padx=2);
  if not dash:ctk.CTkButton(a,text='削除',width=55,height=28,fg_color='transparent',border_width=1,text_color=C['red'],command=lambda:self.delete_sub(s)).pack(side='left',padx=2)
  ctk.CTkButton(a,text='戻す' if s['completed'] else '完了',width=55,height=28,fg_color='transparent' if s['completed'] else C['green'],border_width=1 if s['completed'] else 0,command=lambda:self.subact(m,s)).pack(side='left',padx=2)
  if dash and s['id'] in self.notes:ctk.CTkLabel(f,text=s['note'] or '備考はありません。',text_color=C['muted'],fg_color=C['card'],corner_radius=6,anchor='w').grid(row=1,column=0,columnspan=2,sticky='ew',padx=14,pady=(0,10))
  ctk.CTkFrame(p,height=1,fg_color=C['line']).pack(fill='x',padx=14)
 def toggle(self,i):self.notes.symmetric_difference_update({i});self.render()
 def subact(self,m,s):
  if messagebox.askyesno('確認',f"「{s['name']}」を{'未完了に戻し' if s['completed'] else '完了し'}ますか？",parent=self):self.db.restore_sub(m['id'],s['id']) if s['completed'] else self.db.sub_state(s['id'],1);self.refresh()
 def setting_row(self,p,title):
  f=ctk.CTkFrame(p,fg_color='transparent');f.pack(fill='x',padx=12,pady=8);ctk.CTkLabel(f,text=title,font=ctk.CTkFont(size=13,weight='bold')).pack(side='left');return f
 def update_setting(self,key,value,rerender=False):
  self.settings[key]=value;save_settings(self.settings)
  if key=='zoom':ctk.set_widget_scaling(int(value)/100)
  if rerender:self.render()
 def settingspage(self):
  p=FastScroll(self.host,app=self,fg_color='transparent',corner_radius=0);p.grid(row=0,column=0,sticky='nsew')
  ctk.CTkLabel(p,text='設定',font=ctk.CTkFont(size=22,weight='bold')).pack(anchor='w',pady=(4,12))
  ctk.CTkLabel(p,text='操作設定',text_color=C['blue'],font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w',pady=(8,2))
  f=self.setting_row(p,'スクロール速度');ctk.CTkLabel(f,text='ゆっくり',text_color=C['muted']).pack(side='left',padx=(20,6));num=ctk.CTkLabel(f,text=str(self.settings['scroll_speed']),width=26);num.pack(side='right');ctk.CTkLabel(f,text='速い',text_color=C['muted']).pack(side='right',padx=6)
  def speed(v): val=max(1,min(30,round(float(v))));num.configure(text=str(val));self.update_setting('scroll_speed',val)
  sl=ctk.CTkSlider(f,from_=1,to=30,number_of_steps=29,command=speed);sl.set(self.settings['scroll_speed']);sl.pack(side='left',fill='x',expand=True,padx=6)
  ctk.CTkLabel(p,text='表示設定',text_color=C['blue'],font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w',pady=(18,2))
  f=self.setting_row(p,'表示倍率');z=ctk.CTkSegmentedButton(f,values=['90%','100%','110%','120%'],command=lambda v:self.update_setting('zoom',int(v[:-1])));z.set(f"{self.settings['zoom']}%");z.pack(side='right')
  f=self.setting_row(p,'タスク表示密度');d=ctk.CTkSegmentedButton(f,values=['コンパクト','標準','ゆったり'],command=lambda v:self.update_setting('density',v,True));d.set(self.settings['density']);d.pack(side='right')
  ctk.CTkLabel(p,text='タスク設定',text_color=C['blue'],font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w',pady=(18,2))
  f=self.setting_row(p,'タスク追加時の初期選択');a=ctk.CTkSegmentedButton(f,values=['既存メインへサブ追加','新規メイン'],command=lambda v:self.update_setting('add_default',v));a.set(self.settings['add_default']);a.pack(side='right')
  f=self.setting_row(p,'標準期限');du=ctk.CTkOptionMenu(f,values=['今日','3日後','1週間後','2週間後','期限なし'],command=lambda v:self.update_setting('default_due',v));du.set(self.settings['default_due']);du.pack(side='right')
  f=self.setting_row(p,'標準重要度');pr=ctk.CTkSegmentedButton(f,values=PRI,command=lambda v:self.update_setting('default_priority',v));pr.set(self.settings['default_priority']);pr.pack(side='right')
  ctk.CTkLabel(p,text='動作設定',text_color=C['blue'],font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w',pady=(18,2))
  f=self.setting_row(p,'完了タスクを非表示');sw=ctk.CTkSwitch(f,text='ON / OFF',command=lambda:self.update_setting('hide_completed',bool(sw.get())));sw.pack(side='right');sw.select() if self.settings['hide_completed'] else sw.deselect()
  f=self.setting_row(p,'削除時に確認する');sw2=ctk.CTkSwitch(f,text='ON / OFF',command=lambda:self.update_setting('confirm_delete',bool(sw2.get())));sw2.pack(side='right');sw2.select() if self.settings['confirm_delete'] else sw2.deselect()
  ctk.CTkLabel(p,text='設定は変更時に自動保存されます。',text_color=C['muted']).pack(anchor='w',padx=12,pady=(20,30))
 def listpage(self):
  w=ctk.CTkFrame(self.host,fg_color='transparent');w.grid(row=0,column=0,sticky='nsew');w.grid_columnconfigure(0,weight=1);w.grid_rowconfigure(1,weight=1);z=ctk.CTkSegmentedButton(w,values=['全件','未完了','完了'],command=lambda v:(setattr(self,'filter',v),self.render()));z.set(self.filter);z.grid(row=0,column=0,sticky='w',pady=(0,8));p=FastScroll(w,app=self,fg_color='transparent');p.grid(row=1,column=0,sticky='nsew');arr=([m for m in self.tasks if not m['completed']] if self.settings['hide_completed'] else self.tasks) if self.filter=='全件' else [m for m in self.tasks if bool(m['completed'])==(self.filter=='完了')]
  for m in [x for x in arr if not x['completed']]+[x for x in arr if x['completed']]:self.mainrow(p,m)
 def mainrow(self,p,m):
  done=bool(m['completed']);f=ctk.CTkFrame(p,fg_color=C['done'] if done else C['card'],border_width=1,border_color=C['line']);f.pack(fill='x',pady=(0,8));f.grid_columnconfigure(0,weight=1);i=ctk.CTkFrame(f,fg_color='transparent');i.grid(row=0,column=0,sticky='ew',padx=13,pady=10);ctk.CTkLabel(i,text=m['name'],font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w');n=sum(s['completed'] for s in m['subs']);ctk.CTkLabel(i,text=f"{m['category']}  |  重要度 {m['priority']}  |  目標 {m['due_date']}  |  {n}/{len(m['subs'])} 完了",text_color=C['muted']).pack(anchor='w');a=ctk.CTkFrame(f,fg_color='transparent');a.grid(row=0,column=1,padx=10,pady=10);ctk.CTkButton(a,text='編集',width=55,height=28,fg_color='transparent',border_width=1,command=lambda:Editor(self,'main',m,None,False)).pack(side='left',padx=2);ctk.CTkButton(a,text='削除',width=55,height=28,fg_color='transparent',border_width=1,text_color=C['red'],command=lambda:self.delete_main(m)).pack(side='left',padx=2)
  if not done:ctk.CTkButton(a,text='＋サブ',width=62,height=28,fg_color='transparent',border_width=1,command=lambda:Editor(self,'sub',m,None,False)).pack(side='left',padx=2)
  ctk.CTkButton(a,text='戻す' if done else 'メイン完了',width=86,height=28,fg_color='transparent' if done else C['green'],border_width=1 if done else 0,command=lambda:self.mainact(m)).pack(side='left',padx=2);ctk.CTkButton(f,text=f'サブタスクを表示 {n}/{len(m["subs"])}',fg_color='transparent',text_color=C['muted'],anchor='w',command=lambda:self.expand(f,m)).grid(row=1,column=0,columnspan=2,sticky='ew')
 def expand(self,f,m):
  o=getattr(f,'detail',None)
  if o and o.winfo_exists():o.destroy();f.detail=None;return
  b=ctk.CTkFrame(f,fg_color='transparent');b.grid(row=2,column=0,columnspan=2,sticky='ew',padx=10,pady=8);f.detail=b
  for s in m['subs']:self.subrow(b,m,s)
 def delete_sub(self,s):
  if self.settings['confirm_delete'] and not messagebox.askyesno('削除確認',f"「{s['name']}」を削除しますか？",parent=self):return
  self.db.delete_sub(s['id']);self.refresh()
 def delete_main(self,m):
  if self.settings['confirm_delete'] and not messagebox.askyesno('削除確認',f"「{m['name']}」と配下のサブタスクを削除しますか？",parent=self):return
  self.db.delete_main(m['id']);self.refresh()
 def mainact(self,m):
  r=[s for s in m['subs'] if not s['completed']];txt=f'未完了サブが{len(r)}件あります。全件完了しますか？' if r else f"「{m['name']}」を完了しますか？"
  if messagebox.askyesno('確認',txt,parent=self):self.db.restore_main(m['id']) if m['completed'] else self.db.main_done(m['id'],bool(r));self.refresh()
if __name__=='__main__':App().mainloop()
