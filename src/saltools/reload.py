from    os.path         import  getatime
from    time            import  sleep
from    importlib       import  reload
from    functools       import  total_ordering 

from    .               import  logging     as stl 
from    .               import  parallel    as stp

import  atexit
import  types
import  sys

@total_ordering
class   SortableModule  ():
    def __init__(
        self        ,
        module      ,
        depending   ):
        self.module     = module
        self.depending  = depending 
    def __eq__  (
        self, 
        o   ):
        return self.module == o.module
    def __gt__  (
        self,
        o   ):
        #If other depends on self
        return not (o.module in self.depending)
    def __hash__(
        self):
        return self.module
class   AutoReloader    ():
    
    def __init__(
        self    ):
        self.logger         = stl.ConsoleLogger (id_ = 'reloader')
        self.factory        = stp.NiceFactory(
            id_                 = 'reloader'        ,
            logger              = self.logger           ,
            manager             = self._g_reload_modules,
            manager_frequency   = 5.0                   ,
            n_workers           = 1                     )
        
        self._last_atime    = {}
        
        self._on_reload          = {}
        self._monitored_modules  = {}
        self._exclude            = [
            '__main__'  ,
            __name__    ,
            'six.moves' ]

    def _g_depending        (
        self    ,
        module  ):
        depending_list  = []
        for sys_module in list(sys.modules.values()):
            if      sys_module.__name__ in self._exclude or \
                    sys_module == module                    :
                continue
            for global_attr in dir(sys_module)    :
                try                         :    
                    val     = getattr(sys_module, global_attr)
                    if      type(val) == types.ModuleType           and \
                            val == module                               :
                        depending_list.append(sys_module)
                        break
                    elif    hasattr(val, '__module__')              and \
                            sys.modules.get(val.__module__)== module    :
                        depending_list.append(sys_module)
                        break
                except ModuleNotFoundError  :
                    pass

        return set(depending_list)      
    def _reload_all         (
        self    ,
        modules ):
        to_reload_modules   = {}
        changed_modules     = list(modules)
        while len(changed_modules) > 0 :
            changed_module      = changed_modules.pop()
            if      changed_module in to_reload_modules :
                continue

            depending_modules                   = self._g_depending(changed_module)
            to_reload_modules[changed_module]   = SortableModule(
                changed_module      , 
                depending_modules   )
            changed_modules.extend(depending_modules)
        
        for sorted_module in sorted(to_reload_modules.values()):
            self._reload_module(sorted_module.module)
    @stl.handle_exception   (
        stl.Level.ERROR         ,
        is_log_start    = True  ,
        params_start    = [
            'module.__name__'   ],
        params_exc      = [
            'module.__name__'   ])
    def _reload_module      (
        self    ,
        module  ):
        if      module.__name__ in self._exclude :
            return                   
        reload(module)
        for action in self._on_reload.get(module, []):
            action['action'](*action['args'], **action['kwargs'])
    def _g_reload_modules   (
        self    ):
        modules_to_check    = self._monitored_modules if \
            len(self._monitored_modules)>0          else \
            list(sys.modules.values())
        current_atime       = {}
        modules_to_reload   = set()
        
        for module in modules_to_check  : 
            if      module.__name__ in self._exclude                            :
                continue
            try                                                                 :
                current_atime[module]   = getatime(module.__file__)
            except                                                              :
                continue 
            if      self._last_atime.get(module) != None                        \
                    and self._last_atime.get(module) != current_atime[module]   :
                modules_to_reload.add(module)
        self._reload_all(modules_to_reload)
        self._last_atime    = current_atime

    
    def register    (
        self    ,
        module  ):
        if      module not in self._monitored_modules:
            self._monitored_modules.append(module)
    def on_reload   (
        self    ,
        module  , 
        action  ,
        *args   , 
        **kwargs):
        if      isinstance(module, str):
            module  = sys.modules[module]
        self._on_reload[module] = self._on_reload.get(module, [])
        self._on_reload[module].append(
            {
                'action': action,
                'args'  : args  ,
                'kwargs': kwargs,})
    def exclude     (
        self    ,
        module  ):
        if      not isinstance(module, str) :
            module  = module.__name__
        if      module not in self._exclude : 
            self._exclude.append(module)
    def include     (
        self    ,
        module  ):
        if      not isinstance(module, str) :
            module  = module.__name__
        if      module in self._exclude     :
            self._exclude.remove(module)

RELOADER    = AutoReloader()
RELOADER.factory.start()