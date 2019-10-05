'''Simple Scheduling tool.
'''
from    dateutil.parser         import  parse   as  date_parse

from    dateutil.relativedelta  import  relativedelta
from    datetime                import  datetime        , timedelta
from    collections             import  OrderedDict
from    enum                    import  Enum
from    threading               import  Thread
from    time                    import  sleep
from    collections.abc         import  Callable

from    .                       import  parallel    as stp
from    .                       import  common      as stc
from    .                       import  logging     as stl
from    .                       import  misc        as stm

import  os

class TimeType      (Enum):
    OFFSET      = 0
    LAST_START  = 1
    LAST_STOP   = 2
class TimeRangeType (Enum):
    OK      = 0
    NOT_OK  = 1

class ScheduledTask (stp.FactoryTask):
    EasyObj_PARAMS  = OrderedDict((
        ('is_parallel'  , {
            'default'   : False ,
            'type'      : bool  }),))
    
    def _on_init(self):
        self.next_times         = [] 

class Time      (stl.EasyObj):
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
    DEFAULTS        = OrderedDict((
            ('second'    , 0 ),
            ('minute'    , 0 ),
            ('hour'      , 0 ),
            ('day'       , 1 ),
            ('month'     , 1 ),))
    
    def _on_init        (
        self    ):
        if      self.type != TimeType.OFFSET    :
            kwargs  = {
                k+'s': v  for k,v in vars(self).items() if v!= None and k not in ['type']}
            self.sleep_time = relativedelta(**kwargs)
    def _g_next_offset  (
        self        , 
        current_dt  ):
        offest_kwargs   = OrderedDict()
        time_units_names= list(reversed(self.DEFAULTS.keys()))
        
        for unit_name in time_units_names :
            unit_value = getattr(self, unit_name)
            if      len(offest_kwargs) == 0 \
                    and unit_value == None  :
                continue
            elif    unit_value == None      :
                offest_kwargs[unit_name]   = self.DEFAULTS[unit_name]
            else                            :
                offest_kwargs[unit_name]   = unit_value
        
        biggest_unit            = list(offest_kwargs.keys())[0]
        next_biggest_unit_index = time_units_names.index(biggest_unit)-1
        next_biggest_unit       = time_units_names[next_biggest_unit_index] if   \
            next_biggest_unit_index >= 0                                         \
            else 'year'

        next_biggest_unit               = {next_biggest_unit+'s': 1}
        offest_kwargs['microsecond']    = 0
        next_dt                         = current_dt.replace(**offest_kwargs)

        if      next_dt < current_dt:
            next_dt += relativedelta(**next_biggest_unit)
        return next_dt
    def _g_next_relative(
        self        ,
        current_dt  ,
        last        ):
        if      not last   :
            return current_dt
        kwargs  = {
            unit_name+'s'   : getattr(self, unit_name) if                   \
                getattr(self, unit_name) != None                            \
                else 0                                                      \
                for unit_name, unit_default_value in self.DEFAULTS.items()  }
        return last+ relativedelta(**kwargs)
    
    def g_next_time(
        self        , 
        current_dt  , 
        last_start  , 
        last_stop   ):
        if      self.type == TimeType.OFFSET    :
            return self._g_next_offset(current_dt)
        elif    self.type == TimeType.LAST_START:
            return self._g_next_relative(current_dt, last_start)
        elif    self.type == TimeType.LAST_STOP :
            return self._g_next_relative(current_dt, last_stop)
class TimeRange (stl.EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('is_ok'    , {
            'default'   : True  ,
            'type'      : bool  }),
        ('second'   , {
            'default'   : [0,30]    ,
            'type'      : int       }),
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
            'type'      : int   }),
        ('weekday'      , {
            'default'   : None  ,
            'type'      : int   },),))
        
    def __contains__(
        self        , 
        date        ):
        for time_unit in self.EasyObj_PARAMS.keys():
            unit_range  = getattr(self, time_unit)
            if      time_unit == 'is_ok'                \
                    or unit_range == None               :
                continue
            if      time_unit == 'weekday'              :
                value   = date.weekday()
            else                                        :
                value   = getattr(date, time_unit)
            if      not isinstance(unit_range, list)    \
                    or  len(unit_range) == 1            :
                    is_in_range     = value == stm.g_path(unit_range , 0)
            else                                        :
                    is_in_range = unit_range[0] <= value and unit_range[1] >= value
            if      self.is_ok and not is_in_range      \
                    or not self.is_ok and is_in_range   :
                    return False
        return True
class Schedule  (stl.EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('tasks'        , {
            'type'      : ScheduledTask }),
        ('dates'        , {
            'default'   : []            ,
            'type'      : datetime      ,
            'parser'    : date_parse    }),
        ('times'        , {
            'default'   : [Time()]          ,
            'type'      : Time              }),
        ('ranges'       , {
            'default'   : []                ,
            'type'      : TimeRange         }),))

    def _on_init        (
        self    ):
        self.consumed_dates = []
    def _does_in_ranges (
        self    ,
        date    ):
        for range_ in self.ranges :
            if      date not in range_  :
                return False 
        return True
    
    def g_next_times(
        self        , 
        current_dt  ):
        '''Get next running times
        '''
        for task in self.tasks   :
            task.next_times.clear()
            for t in self.times :
                next_time   = t.g_next_time(
                    current_dt      , 
                    task.last_start ,
                    task.last_stop  ) 
                if      next_time                           \
                        and self._does_in_ranges(next_time) :
                    task.next_times.append(next_time)
            for date in self.dates  :
                if      current_dt > date                   \
                        and date not in self.consumed_dates \
                        and self._does_in_ranges(date)      :
                    self.consumed_dates.append(date)
                    task.next_times.append(date)
        return self.tasks

class Scheduler (stp.NiceFactory):
    EasyObj_PARAMS  = OrderedDict((
        ('schedules'        , {
            'type'      : Schedule  ,
            'default'   : []        }),
        ('reporters'        , {
            'type'      : Callable  ,
            'default'   : []        }),
        ('is_print_report'  , {
            'type'      : bool      ,
            'default'   : True      }),))

    def _on_init        (
        self    ):
        self.awaiting   = []
        self.manager    = self._g_pending

    def _g_next_times   (
        self        , 
        current_dt  ):
        '''Gets the schedules times
        '''
        tasks = []
        for sch in self.schedules   :
            tasks   +=sch.g_next_times(current_dt)
        return tasks
    def _report         (
        self        ,
        current_dt  ):
        for reporter in self.reporters:
            reporter(
                self.state      ,
                current_dt      ,
                self.working    ,
                self.awaiting   )
    def _g_pending      (
        self    ):
        current_dt      = datetime.utcnow()
        self.pending    = [task for task, time in self.awaiting if current_dt>= time]
        self.awaiting   = []
        
        for task in self._g_next_times(current_dt)  :
            for time in task.next_times :
                if      current_dt < time                   \
                        and not (                           \
                            not task.is_parallel            \
                            and self.is_task_running(task)) :
                    self.awaiting.append([task, time])
        
        self._report(current_dt)
        if      self.is_print_report    :
            os.system('clear')
            print(self._g_nice_report(current_dt))
        
        return self.pending 
    def _g_nice_report  (
        self                            ,
        current_dt  = datetime.utcnow() ):
        state       = self.state 
        running     = self.working
        awaiting    = self.awaiting
        p_format = '\n'.join([
            '{state:<5}:{current_dt}'   ,
            'RUNNING'                   ,
            '----------'                ,
            '{running_hdr}'             ,
            '{running_str}'             ,
            '\n'                        ,
            'AWAITING'                  ,
            '----------'                ,
            '{awaiting_hdr}'            ,
            '{awaiting_str}'            ])
        a_format = '{t_id:<20}|{prl:<8}|{nxt:<26}|{rem:>25}|{lst:<26}|{lsp:<26}|{ls:<12}'
        ah_format= '{t_id:<20}|{prl:<8}|{nxt:<26}|{rem:<25}|{lst:<26}|{lsp:<26}|{ls:<12}'
        r_format = '{t_id:<20}|{prl:<8}|{lst:<26}|{_id}'

        g_rem   = lambda t, current_dt : str(t - current_dt)  
        awaiting_str    = '\n'.join([
            a_format.format(
                t_id    = task._id                                  ,
                prl     = str(task.is_parallel)                     ,
                nxt     = time.isoformat()                          ,
                rem     = g_rem(time, current_dt)                   ,
                lst     = str(task.last_start)                      ,
                lsp     = str(task.last_stop)                       ,
                ls      = task.last_stop_status.name                \
                    if task.last_stop_status != None else 'None'    )\
                    for task, time in awaiting  ])
        running_str     = '\n'.join([
            r_format.format(
                t_id     = d['task']._id            ,
                prl     = str(d['task'].is_parallel),
                lst     = d['start'].isoformat()    ,                          
                _id     = _id                       ) for _id, d in running.items() ])

        awaiting_hdr    = ah_format.format(
            t_id    = 'TID'         , 
            prl     = 'PARALLEL'    , 
            nxt     = 'NEXT RUN'    , 
            rem     = 'REMAINING'   , 
            lst     = 'LAST START'  , 
            lsp     = 'LAST STOP'   , 
            ls      = 'LAST STATUS' )
        running_hdr     = r_format.format(
            t_id    = 'TID'         ,
            prl     = 'PARALLEL'    , 
            lst     = 'LAST START'  , 
            _id     = 'ID'          )
        awaiting_hdr    +='\n'+ '-'*len(awaiting_hdr)
        running_hdr     +='\n'+ '-'*len(running_hdr)

        return p_format.format(
            state       = state.name    ,
            current_dt  = current_dt    ,
            running_hdr = running_hdr   ,
            running_str = running_str   ,
            awaiting_hdr= awaiting_hdr  ,
            awaiting_str= awaiting_str  )
    
    
def task_fn(name, iter, s):
    for i in range(iter):
        with open(name+'.csv', 'a') as f:
            f.write('{}\n'.format(i))
        sleep(s)

   
def x():
    tk1 =   ScheduledTask(
        task_fn             ,
        'task_1'            ,
        ['1', 20, 2]        ,
        is_parallel   = True)
    return Scheduler(schedules= [Schedule([tk1])])
'''
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

tk1  = ScheduledTask(
    task_fn     ,
    'task_1'    ,
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

schr    = Scheduler([sch_1, sch_2], frequency= 5.0)'''