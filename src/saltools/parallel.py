from    .common             import  EasyObj
from    collections.abc     import  Iterable        , Callable
from    collections         import  OrderedDict
from    sqlalchemy          import  create_engine
from    multiprocessing     import  Process         , Queue
from    threading           import  Thread
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

class FactoryTask(EasyObj):
      
    EasyObj_PARAMS  = OrderedDict((
        ('target'       , {
            'type'      : Callable  }),
        ('_id'          , {
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
            'type'      : FactoryTask   ,
            'default'   : []    },),
        ('_id'                  , {
            'type'      : str           ,
            'default'   : 'nice_factory'},),
        ('logger'               , {
            'default'   : stl.ConsoleLogger()   },),
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
            'default'   : None  },),))
    LIVE_FACTORIES  = []
    
    @classmethod
    def _run_task_target(
        cls         ,
        fn          ,
        args        , 
        kwargs      ,
        _id         ,
        status_queue):
        try :
            exec_report = {}
            fn(*args, **kwargs)
            exec_report['status']   = ExitStauts.NORMAL
        except:
            exec_report['status']   = ExitStauts.ERROR
        finally:
            exec_report['_id']      = _id
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
            fn._task_thread.join()
        stl.Logger.stop_all()

    def _on_init            (
        self    ):
        self.state          = State.IDLE
        self.exit_status    = None
        self.working        = {}
        self._id_cpt        = 0
        self.n_tasks        = 0

        self.tasks_queue    = queue.Queue()
        self.workers_queue  = queue.Queue()
        self.signals_queue  = queue.Queue()
        
        self.process_status_queue   = Queue()
        self.thread_status_queue    = queue.Queue()

        for task in self.start_tasks :
            self.tasks_queue.put(task)
        if      self.n_workers != None  :
            for i in range(self.n_workers)  :
                self.workers_queue.put('Worker {}'.format(i+ 1))   
    def _is_done            (
        self    ):
        '''Is it time to call it a day?.

            The factory should close if:
            - If external condition (custom logic) defined by `does_done` returns `True`.
            - If number of executed tasks equals `max_tasks`.
            - The `boolean` `is_no_tasks_stop` is set to `True`, all worksers are waiting and no tasks are available.
        '''
        if      \
                (
                    self.does_done != None                              \
                    and self.does_done                                  (
                        self.tasks_queue        ,
                        self.workers_queue      ,
                        self.n_workers          ,
                        self.max_tasks          ,
                        self.n_tasks            )                       )\
                or (
                    self.max_tasks != None                              \
                    and self.n_tasks == self.max_tasks                  )\
                or (
                    self.is_no_tasks_stop                               \
                    and self.workers_queue.qsize()   == self.n_workers  \
                    and self.tasks_queue.qsize()     == 0               ):
            return True 
        return  False 
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = [
            'task._id'  ,
            'name'      ])
    def _run_task           (
        self    , 
        task    ,
        name    ):
        self._id_cpt     +=1
        _id             = self._id_cpt
        start           = datetime.utcnow()
        task.last_start = start

        worker              = (Process if task.is_process else Thread)(
                    target  = self._run_task_target ,
                    args    = (
                        task.target                                                                 , 
                        task.args                                                                   ,
                        task.kwargs                                                                 ,
                        _id                                                                         ,
                        self.process_status_queue if task.is_process else self.thread_status_queue  ))
        self.working[_id]   = {
            'task'  : task  ,
            'start' : start ,
            'worker': worker}
        worker.start()
    def _check_status       (
        self    ):
        def __check_status(status_queue):
            while status_queue.qsize():
                exec_report = status_queue.get()
                task        = self.working[exec_report['_id']]['task']
                worker      = self.working[exec_report['_id']]['worker']

                task.last_stop         = exec_report['last_stop']
                task.last_stop_status  = exec_report['status']

                del self.working[exec_report['_id']]
                if      self.n_workers != None  :
                    self.workers_queue.put(worker.name)
                self.n_tasks    +=1
        __check_status(self.process_status_queue)
        __check_status(self.thread_status_queue )
    def _check_signal       (
        self            ,
        signal_or_task  ):
        result  = True
        if      self.state  == State.STOPPING      :
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
            if      signal  == Signal.RESUME:
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

            - Checks for exit condition on every iteration/task.
            - Waits for a task or a `STOP`/`SUSPEND` signal.
            - If a `STOP` signal is received, waits for all workers to finish and break.
            - If a `SUSPEND` signal is received, wait for a new signal.
                - If a `STOP` signal is received, waits for all workers to finish and break.
                - If a `RESUME` signal is received, continue the loop.
            - If a `task` is received, wait for a worker and make it work.
        '''
        while not self._is_done() :
            signal_or_task  = self.tasks_queue.get()
            if      isinstance(signal_or_task, FactoryTask):
                if          self.n_workers != None  :
                    worker_name = self.workers_queue.get()
                    if      self.state == State.RUNNING :
                        self._run_task(signal_or_task, worker_name)
                else                                :
                    self._run_task(task, 'Worker {}'.format(self._id_cpt+1))
            elif    self._check_signal(signal_or_task)  :
                continue
            else                                        :
                break
        self._manager_thread.join()
        self.state = State.IDLE
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  ,
        is_log_end      = True  )
    def _manager_loop       (
        self    ):
        while   len(self.working) != 0  \
                or self.state not in    [
            State.STOPPING  ,
            State.IDLE      ]:
            self._check_status()
            if      self.manager    != None         \
                    and self.state == State.RUNNING :
                try     :
                    tasks   = self.manager()
                except  :
                    self.logger.error({'Manager': 'Error at manager.'})
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
        self._task_thread   = Thread(
            name    = '{}: task_thread'.format(self._id)    ,
            target  = self._task_loop                       ,
            daemon  = True                                  )
        self._manager_thread= Thread(
            name    = '{}: manager_thread'.format(self._id) ,
            target  = self._manager_loop                    ,
            daemon  = True                                  )
        self.state          = State.RUNNING
        self.LIVE_FACTORIES.append(self)
        self.logger.start()
        self._task_thread.start()    
        self._manager_thread.start()   
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
        self.tasks_queue.put(Signal.STOP)
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
        self.tasks_queue.put(Signal.SUSPEND)
    @stl.handle_exception   (
        is_log_start    = True  ,
        params_start    = None  )
    def terminate_worker    (
        self,
        _id ):
        task_dict   = self.working.get(_id)
        if      task_dict                       \
                and task_dict['task'].is_process:
                task_dict['worker'].terminate()
                del self.working[_id]
                task_dict['task'].last_stop_status   = ExitStauts.STOPPED
                task_dict['task'].last_stop          = datetime.utcnow()
    def does_task_running   (
        self    ,
        task    ):
        return task._id in [x['task']._id for x in self.working.values()]
    def join                (
        self    ):
        self._task_thread.join()
    def join_exit           (
        self    ):
        while True :
            try :
                input()
            except KeyboardInterrupt:
                self.logger.info({'User action': 'Keyboard interrupt'})
                break
        self.stop()
        self.join()
        self.logger.stop()
atexit.unregister(stl.Logger.stop_all)  
atexit.register(NiceFactory.stop_all)