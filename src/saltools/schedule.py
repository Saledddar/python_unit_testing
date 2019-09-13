'''Simple Scheduling tool.
'''
from    dateutil.parser         import  parse   as  date_parse

from    dateutil.relativedelta  import  relativedelta
from    datetime                import  datetime        , timedelta
from    .common                 import  EasyObj
from    .logging                import  handle_exception 
from    .misc                   import  g_safe
from    collections             import  OrderedDict
from    enum                    import  Enum
from    threading               import  Thread
from    time                    import  sleep
from    collections.abc         import  Callable
from    multiprocessing         import  Process     , Queue
from    threading               import  Thread

import  os

class ExceptionThreadTerminate  (Exception):
    pass
class ExceptionNoId             (Exception):
    pass

class TimeType  (Enum):
    OFFSET      = 0
    LAST_START  = 1
    LAST_STOP   = 2
class StopStatus(Enum):
    NORMAL      = 0
    ERROR       = 1
    TERMINATED  = 2

class Task      (EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('name'         , {
            'type'      : str   }),
        ('target'       , {
            'type'      : Callable  }),
        ('args'         , {
            'type'      : list  ,
            'default'   : []    }),
        ('kwargs'       , {
            'type'      : dict  ,
            'default'   : {}    }),
        ('is_parallel'  , {
            'default'   : False ,
            'type'      : bool  }),
        ('is_thread'    , {
            'default'   : False }),))
    
    def _on_init(self):
        self.last_start         = None 
        self.last_stop          = None 
        self.last_stop_status   = None 
        self.next_times         = [] 
class Time      (EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('type'     , {
            'default'   : TimeType.OFFSET   ,
            'type'      : TimeType          }),
        ('second'   , {
            'default'   : 5     ,
            'type'      : int   }),
        ('minute'   , {
            'default'   : None  ,
            'type'      : int   }),
        ('hour'     , {
            'default'   : None  ,
            'type'      : int   }),
        ('day'      , {
            'default'   : None  ,
            'type'      : int   }),
        ('month'    , {
            'default'   : None  ,
            'type'      : int   }),))
    DEFAULTS        = {
            'second'    : 0 ,
            'minute'    : 0 ,
            'hour'      : 0 ,
            'day'       : 1 ,
            'month'     : 1 }
    
    def _on_init(self):
        if      self.type != TimeType.OFFSET    :
            kwargs  = {
                k+'s': v  for k,v in vars(self).items() if v!= None and k not in ['type']}
            self.sleep_time = relativedelta(**kwargs)

    def _g_next_offset(
        self    , 
        dt      ):
        kwargs                  = OrderedDict()
        frames                  = list(self.EasyObj_PARAMS.keys())[:0:-1]
        
        for k in frames :
            v = getattr(self, k)
            if      not len(kwargs) and v == None   :
                continue
            elif    v == None                       :
                kwargs[k]   = self.DEFAULTS[k]
            else                                    :
                kwargs[k]   = v
        
        minor   = list(kwargs.keys())[0]
        major   = frames.index(minor)-1
        major   = frames[major] if major >= 0 else 'year'
        major   = {major+'s': 1}
        
        kwargs['microsecond']   = 0
        dt                      = dt.replace(**kwargs)

        if dt- datetime.utcnow() < timedelta(0) :
            dt += relativedelta(**major)
        return dt
    def _g_next_relative(
        self,
        dt  ,
        last):
        if      not last   :
            return dt
        kwargs  = {
            k+'s'   : getattr(self, k) if   \
                k in self.EasyObj_PARAMS and\
                getattr(self, k)    else 0
                for k, v in self.DEFAULTS.items()  }
        return last+ relativedelta(**kwargs)    
    
    def g_next_time(
        self        , 
        dt          , 
        last_start  , 
        last_stop   ):
        if      self.type == TimeType.OFFSET    :
            return self._g_next_offset(dt)
        elif    self.type == TimeType.LAST_START:
            return self._g_next_relative(dt, last_start)
        elif    self.type == TimeType.LAST_STOP :
            return self._g_next_relative(dt, last_stop)
class Schedule  (EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('tasks'        , {
            'type'      : Task  }),
        ('dates'        , {
            'default'   : []            ,
            'type'      : datetime      ,
            'parser'    : date_parse    }),
        ('times'        , {
            'default'   : [Time()]          ,
            'type'      : Time              }),))

    def _on_init(
        self    ):
        self.consumed_dates = []
        
    def g_next_times(
        self    , 
        dt      ):
        '''Get next running times
        '''
        for task in self.tasks   :
            task.next_times.clear()
            for t in self.times :
                next_time   = t.g_next_time(
                    dt              , 
                    task.last_start ,
                    task.last_stop  ) 
                if      next_time    :
                    task.next_times.append(next_time)
            for date in self.dates  :
                if dt > date and date not in self.consumed_dates:
                    self.consumed_dates.append(date)
                    task.next_times.append(date)
        return self.tasks
class Scheduler (EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('schedules'        , {
            'type'      : Schedule  }),
        ('reporters'        , {
            'type'      : Callable  ,
            'default'   : []        }),
        ('frequency'        , {
            'type'      : float     ,
            'default'   : 1.0       }),
        ('is_report_console', {
            'default'   : True  ,
            'type'      : bool  }),))
    
    @staticmethod
    def _run_task_target(
        fn          ,
        args        , 
        kwargs      ,
        _id         ,
        queue       ):
        try :
            exec_report = {}
            fn(*args, **kwargs)
            exec_report['status']   = StopStatus.NORMAL
        except:
            exec_report['status']   = StopStatus.ERROR
        finally:
            exec_report['_id']      = _id
            exec_report['last_stop']= datetime.utcnow()
            queue.put(exec_report)

    def _on_init(
        self    ):
        self.alive      = False
        self.running    = {}
        self.id_cpt     = 0 
        self.threads    = {}
        self.pending    = {}
        self.awaiting   = {}
        self.queue      = Queue()
    
    def _g_next_times(
        self    , 
        dt      ):
        '''Gets the schedules times
        '''
        tasks = []
        for sch in self.schedules   :
            tasks   +=sch.g_next_times(dt)
        return tasks
    def _g_pending(
        self        ,
        dt          ,
        tasks_times , 
        awaiting    ):
        pending     = [task for task, time in awaiting if dt>= time]
        awaiting    = []
        for task in tasks_times:
            for time in task.next_times:
                if dt < time:
                    awaiting.append([task, time])
        return pending, awaiting  
    def _run_task(
        self    , 
        task    ):
        self.id_cpt +=1
        _id         = self.id_cpt
        start                   = datetime.utcnow()
        task.last_start         = start
        self.running[_id]= {
            'task'  : task  ,
            'start' : start }
        thread      = (Thread if task.is_thread else Process)(
                    target  = self._run_task_target ,
                    args    = (
                        task.target , 
                        task.args   ,
                        task.kwargs ,
                        _id         ,
                        self.queue  )   )
        self.threads[_id]   = thread
        thread.start()
    def _check_done(
        self    ):
        while self.queue.qsize():
            exec_report = self.queue.get(block= True)
            task        = self.running[exec_report['_id']]['task']

            task.last_stop         = exec_report['last_stop']
            task.last_stop_status  = exec_report['status']

            del self.running[exec_report['_id']]
            del self.threads[exec_report['_id']]
    @handle_exception(log_start= True, log_end= True)
    def _loop(
        self    ):
        started     = True
        awaiting    = []
        while self.alive or len(self.running):
            started             = False
            dt                  = datetime.utcnow()
            tasks_times         = self._g_next_times(dt) 
            pending, awaiting   = self._g_pending(dt, tasks_times, awaiting)
            
            if      len(self.reporters)     :
                for reporter in self.reporters:
                    reporter(
                        self.alive  ,
                        dt          ,
                        awaiting    ,
                        self.running)
            if      self.is_report_console  :
                self.report_to_console(
                    dt          ,
                    self.alive  ,
                    awaiting    ,
                    self.running)       
            if      self.alive              :
                for pending_task in pending :
                    self._run_task(pending_task)

            self._check_done()
            
            sleep(self.frequency)
    
    @handle_exception(log_start= True)
    def start(self):
        self.main_thread    = Thread(target= self._loop)
        self.alive          = True
        self.main_thread.start()   
    @handle_exception(log_start= True)
    def stop(
        self            , 
        force   = False ):
        self.alive          = False
        if force    :
            try :
                for _id in list(self.running.keys()) :
                    self.terminate(_id)
            except ExceptionThreadTerminate:
                pass 
    def terminate(
        self, 
        _id ):
        task_info   = self.running.get(_id)
        if      not task_info        :
            raise ExceptionNoId('No task found for id :{}.'.format(_id))
        task        = task_info['task']
        if      task.is_thread  :
            raise ExceptionThreadTerminate('Can\'t terminate threads, only processes.')
        self.threads[_id].terminate()
        del self.threads[_id]
        del self.running[_id]
        task.last_stop_status   = StopStatus.TERMINATED
        task.last_stop          = datetime.utcnow()
    def report_to_console(
        self            ,
        dt              ,
        alive           ,
        awaiting        ,
        running         ,
        clear   = True  ):
        if      clear    :
            os.system('clear')
        p_format = '\n'.join([
            '{alive:<5}:{dt}'   ,
            'RUNNING'           ,
            '----------'        ,
            '{running_hdr}'     ,
            '{running_str}'     ,
            '\n'                ,
            'AWAITING'          ,
            '----------'        ,
            '{awaiting_hdr}'    ,
            '{awaiting_str}'    ])
        a_format = '{name:<20}|{prl:<8}|{nxt:<26}|{rem:>25}|{lst:<26}|{lsp:<26}|{ls:<20}'
        r_format = '{name:<20}|{prl:<8}|{lst:<26}|{_id}'

        g_rem   = lambda t, dt : str(t - dt)  
        awaiting_str    = '\n'.join([
            a_format.format(
                name    = task.name                 ,
                prl     = str(task.is_parallel)     ,
                nxt     = time.isoformat()          ,
                rem     = g_rem(time, dt)           ,
                lst     = str(task.last_start)      ,
                lsp     = str(task.last_stop)       ,
                ls      = task.last_stop_status.name
                    if task.last_stop_status else 'None') for task, time in awaiting])
        running_str     = '\n'.join([
            r_format.format(
                name    = d['task'].name            ,
                prl     = str(d['task'].is_parallel),
                lst     = d['start'].isoformat()    ,                          
                _id     = _id                       ) for _id, d in running.items() ])

        a_format = '{name:<20}|{prl:<8}|{nxt:<26}|{rem:<25}|{lst:<26}|{lsp:<26}|{ls:<20}'
        awaiting_hdr    = a_format.format(
            name    = 'NAME'        , 
            prl     = 'PARALLEL'    , 
            nxt     = 'NEXT RUN'    , 
            rem     = 'REMAINING'   , 
            lst     = 'LAST START'  , 
            lsp     = 'LAST STOP'   , 
            ls      = 'LAST STATUS' )
        running_hdr     = r_format.format(
            name    = 'NAME'        ,
            prl     = 'PARALLEL'    , 
            lst     = 'LAST START'  , 
            _id     = 'ID'          )
        awaiting_hdr    +='\n'+ '-'*len(awaiting_hdr)
        running_hdr     +='\n'+ '-'*len(running_hdr)

        print(p_format.format(
            alive       = 'ON' if alive else 'OFF'  ,
            dt          = dt            ,
            running_hdr = running_hdr   ,
            running_str = running_str   ,
            awaiting_hdr= awaiting_hdr  ,
            awaiting_str= awaiting_str  ))
    
def task_fn(name, iter, s):
    for i in range(iter):
        with open(name+'.csv', 'a') as f:
            f.write('{}\n'.format(i))
        sleep(s)

dt      = datetime.utcnow()
date_1  = dt+ timedelta(seconds= 30)
date_2  = dt+ timedelta(minutes= 1)

time_1  = Time(
    'OFFSET'        ,
    second      = 0 )
time_2  = Time(
    'OFFSET'                   ,
    second     = 5             ,
    minute     = dt.minute+1   ,
    hour       = dt.hour       )
time_3  = Time(
    'LAST_START'               ,
    second     = 5             ,
    minute     = 1             )
time_4  = Time(
    'LAST_STOP'                 ,
    minute     = 2             )

task_1  = Task(
    'task_1'    ,
    task_fn     ,
    ['1', 20, 2],
    is_parallel   = True ,    
    )

task_2  = Task(
    'task_2'    ,
    task_fn     ,
    ['2', 20, 2],
    is_parallel   = True ,    
    )
sch_1   = Schedule(tasks=[task_1])
sch_2   = Schedule(tasks=[task_2], times= [time_1, time_2,time_3])

schr    = Scheduler([sch_1, sch_2], frequency= 5.0)