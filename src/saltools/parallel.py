from    .common             import  EasyObj
from    collections.abc     import  Iterable        , Callable
from    collections         import  OrderedDict
from    sqlalchemy          import  create_engine
from    multiprocessing     import  Process         , Queue
from    threading           import  Thread          , Condition
from    enum                import  Enum
from    datetime            import  datetime
from    time                import  sleep
from    .                   import  logging         as stl 

import  atexit
import  queue
 
class Signal    (Enum):
    STOP        = 0
    SUSPEND     = 1
    RESUME      = 2
class ExitStauts(Enum):
    NORMAL  = 0
    STOPPED = 1
    ERROR   = 2
class State     (Enum):
    RUNNING     = 0
    STOPPING    = 1
    IDLE        = 2
    SUSPENDED   = 3 
    SUSPENDING  = 4

class NiceTQueue    ():
    def __init__(
        self    ):
        self._list      = []
        self.condition  = Condition() 

    def insert  (
        self    ,
        index   , 
        item    ):
        with self.condition :
            self._list.insert(index, item)
            self.condition.notifyAll()
    def put     (
        self    ,
        item    ):
        with self.condition :
            self._list.append(item)
            self.condition.notifyAll()
    def pop     (
        self            ,
        index           ,
        timeout = None  ):
        if not len(self._list):
            with self.condition :
                self.condition.wait(timeout)
        if      len(self._list) < index+ 1  :
            raise queue.Empty()
        return self._list.pop(index)
    def get     (
        self            ,
        timeout = None  ):
        return self.pop(0, timeout)
    def qsize   (
        self    ):
        return len(self._list)
    def clear   (
        self    ):
        self._list.clear()

class FactoryTask(EasyObj):
      
    EasyObj_PARAMS  = OrderedDict((
        ('target'       , {
            'type'      : Callable  }),
        ('id_'          , {
            'type'      : str           ,
            'default'   : 'factory_task'}),
        ('args'         , {
            'type'      : list  ,
            'default'   : []    }),
        ('kwargs'       , {
            'type'      : dict  ,
            'default'   : {}    }),
        ('is_process'   , {
            'default'   : False }),))
        
    def _on_init(self):
        self.last_start         = None 
        self.last_stop          = None 
        self.last_stop_status   = None
class NiceFactory(EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('start_tasks'          , {
            'type'      : [FactoryTask] ,
            'default'   : []            },),
        ('id_'                  , {
            'type'      : str           ,
            'default'   : 'nice_factory'},),
        ('logger'               , {
            'default'   : stl.ConsoleLogger(id_='factory')  },),
        ('manager'              , {
            'default'   : None  },),
        ('manager_frequency'    , {
            'default'   : 5.0   ,
            'type'      : float },),
        ('n_workers'            , {
            'type'      : int   ,
            'default'   : 1     },),
        ('does_done'            , {
            'default'   : None  },),
        ('is_no_tasks_stop'     , {
            'type'      : bool  ,
            'default'   : False },),
        ('max_tasks'            , {
            'type'      : int   ,
            'default'   : None  },),
        ('on_stop'              , {
            'default'   : None      , 
            'type'      : Callable  },),
        ('on_start'             , {
            'default'   : None      , 
            'type'      : Callable  },),))
    LIVE_FACTORIES  = []
    
    @classmethod
    def _run_task_target(
        cls         ,
        fn          ,
        args        , 
        kwargs      ,
        id_         ,
        status_queue):
        try :
            exec_report = {}
            fn(*args, **kwargs)
            exec_report['status']   = ExitStauts.NORMAL
        except:
            exec_report['status']   = ExitStauts.ERROR
        finally:
            exec_report['id_']      = id_
            exec_report['last_stop']= datetime.utcnow()
            status_queue.put(exec_report)
    
    @classmethod
    def stop_all(
        cls ):
        '''Stop all live factories.

            Stops all factories regestered at LIVE_FACTORIES.
        '''
        for fn in cls.LIVE_FACTORIES.copy():
            fn.stop()
            fn.join()
        stl.Logger.stop_all()

    def _on_init            (
        self    ):
        self.state          = State.IDLE
        self.exit_status    = None
        self.working        = {}
        self.id__cpt        = 0
        self.n_tasks        = 0

        self.tasks_queue    = NiceTQueue()
        self.workers_queue  = queue.Queue()
        self.signals_queue  = queue.Queue()
        
        self.process_status_queue   = Queue()
        self.thread_status_queue    = queue.Queue()

        if      self.n_workers != None  :
            for i in range(self.n_workers)  :
                self.workers_queue.put('Worker {}'.format(i+ 1))   
    def _does_done          (
        self    ):
        '''Is it time to call it a day?.

            The factory should close if on of the following is true:
                - Factory is stopping.
                - External condition (custom logic) defined by `does_done` returns `True`.
                - Number of executed tasks equals `max_tasks`.
                - The `boolean` `is_no_tasks_stop` is set to `True`, all worksers are waiting and no tasks are available.
        '''
        if      self.state == State.STOPPING                            \
                or (
                    self.does_done != None                              \
                    and self.does_done                                  (
                        self.tasks_queue        ,
                        self.workers_queue      ,
                        self.n_workers          ,
                        self.max_tasks          ,
                        self.n_tasks            )                       )\
                or (
                    self.max_tasks != None                              \
                    and self.n_tasks >= self.max_tasks                  )\
                or (
                    self.is_no_tasks_stop                               \
                    and self.workers_queue.qsize()   == self.n_workers  \
                    and self.tasks_queue.qsize()     == 0               ):
            self.state  = State.STOPPING
            return True 
        return  False 
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = [
            'task.id_'  ,
            'name'      ])
    def _run_task           (
        self    , 
        task    ,
        name    ):
        self.id__cpt     +=1
        id_             = self.id__cpt
        start           = datetime.utcnow()
        task.last_start = start

        worker              = (Process if task.is_process else Thread)(
                    target  = self._run_task_target ,
                    name    = name                  ,
                    args    = (
                        task.target                                                                 , 
                        task.args                                                                   ,
                        task.kwargs                                                                 ,
                        id_                                                                         ,
                        self.process_status_queue if task.is_process else self.thread_status_queue  ))
        self.working[id_]   = {
            'task'  : task  ,
            'start' : start ,
            'worker': worker}
        worker.start()
    def _check_status       (
        self    ):
        def __check_status(status_queue):
            while status_queue.qsize():
                exec_report = status_queue.get()
                task        = self.working[exec_report['id_']]['task']
                worker      = self.working[exec_report['id_']]['worker']

                task.last_stop         = exec_report['last_stop']
                task.last_stop_status  = exec_report['status']

                del self.working[exec_report['id_']]
                if      self.n_workers != None  :
                    self.workers_queue.put(worker.name)
                self.n_tasks    +=1
        __check_status(self.process_status_queue)
        __check_status(self.thread_status_queue )
    def _check_signal       (
        self            ,
        signal_or_task  ):
        result  = True
        if      self.state  == State.STOPPING       :
            result = False
        elif    signal_or_task == Signal.STOP       :
            self.logger.info({'Signal received': 'STOP'})
            result  = False 
        elif    signal_or_task == Signal.SUSPEND    :
            self.logger.info({'Signal received': 'SUSPEND'})
            self.state  = State.SUSPENDED
            signal  = self.signals_queue.get()
            if      signal  == Signal.STOP  :
                self.logger.info({'Signal received': 'STOP'})
                result  = False 
            elif    signal  == Signal.RESUME:
                self.logger.info({'Signal received': 'RESUME'})
                self.state  = State.RUNNING
                result  = True 
        return result
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  ,
        is_log_end      = True  )
    def _task_loop          (
        self    ):
        '''Factory loop, manages tasks and worksers.

            - While factory not done, do the following
                - Wait for a task or signal.
                - If a task is received, execute.
                - If a signal is received, check the signal and act accordingly.

        '''
        while not self._does_done() :
            try     :
                signal_or_task  = self.tasks_queue.get(timeout= 1)
            except  queue.Empty :
                continue 
            if      isinstance(signal_or_task, FactoryTask) :
                if          self.n_workers != None  :
                    worker_name = self.workers_queue.get()
                    self._run_task(signal_or_task, worker_name)
                else                                :
                    self._run_task(task, 'Worker {}'.format(self.id__cpt+1))
            elif    self._check_signal(signal_or_task)      :
                continue
            else                                            :
                break
        self._manager_thread.join()
        self.tasks_queue.clear()
        self.n_tasks    = 0
        self.state = State.IDLE
        if      self.on_stop != None    :
            self.on_stop(self)
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  ,
        is_log_end      = True  )
    def _manager_loop       (
        self    ):
        while   \
                self.state not in [
                        State.IDLE      ,
                        State.STOPPING  ]           \
                or (
                    self.state == State.STOPPING    \
                    and len(self.working) != 0      ):
            self._check_status()
            if      self.manager    != None         \
                    and self.state == State.RUNNING :
                try                     :
                    tasks   = self.manager()
                except  Exception as e  :
                    self.logger.error({'Manager': f'Error at manager, {e}'})
                    tasks   = None
                if      tasks: 
                    for task in tasks   :
                        self.tasks_queue.put(task)
            sleep(self.manager_frequency)
    
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def start               (
        self    ):
        if      self.state  != State.IDLE       :
            return
        for task in self.start_tasks :
            self.tasks_queue.put(task)
        self._task_thread   = Thread(
            name    = '{}: task_thread'.format(self.id_)    ,
            target  = self._task_loop                       ,
            daemon  = True                                  )
        self._manager_thread= Thread(
            name    = '{}: manager_thread'.format(self.id_) ,
            target  = self._manager_loop                    ,
            daemon  = True                                  )
        if      self.on_start != None   :
            self.on_start(self)
        self.state          = State.RUNNING
        self.LIVE_FACTORIES.append(self)
        self.logger.start()
        self._manager_thread.start()
        self._task_thread.start()    
        
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def stop                (
        self            ,
        force   = False ):
        if      self.state  in  [
            State.IDLE          ,
            State.STOPPING      ]:
            return

        self.state  = State.STOPPING
        self.tasks_queue.insert(0, Signal.STOP)
        self.signals_queue.put(Signal.STOP)

        if      force   :
            for k, v in self.working    :
                self.terminate_worker(k)
        self.LIVE_FACTORIES.remove(self)
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def resume              (
        self    ):
        if  self.state != State.SUSPENDED   :
            return
        self.signals_queue.put(Signal.RESUME)
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def suspend             (
        self    ):
        if      self.state      != State.RUNNING:
            return
        self.state  = State.SUSPENDING
        self.tasks_queue.insert(0, Signal.SUSPEND)
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def terminate_worker    (
        self,
        id_ ):
        task_dict   = self.working.get(id_)
        if      task_dict                       \
                and task_dict['task'].is_process:
                task_dict['worker'].terminate()
                del self.working[id_]
                task_dict['task'].last_stop_status   = ExitStauts.STOPPED
                task_dict['task'].last_stop          = datetime.utcnow()
    def does_task_running   (
        self    ,
        task    ):
        return task.id_ in [x['task'].id_ for x in self.working.values()]
    def join                (
        self    ):
        self._task_thread.join()
    def join_exit           (
        self    ):
        print('Press CTRL+C to stop the script!')
        while self.state != State.IDLE :
            try :
                sleep(1)
            except KeyboardInterrupt:
                self.logger.info({'User action': 'Keyboard interrupt'})
                break
        print('Stopping ...')
        if      self.state != State.IDLE    :
            self.stop()
            self.join()
            self.logger.stop()

atexit.unregister(stl.Logger.stop_all)  
atexit.register(NiceFactory.stop_all)