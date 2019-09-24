from    threading       import  Thread
from    os.path         import  getatime
from    time            import  sleep
from    importlib       import  reload

from    .               import  logging     as stl 
from    functools       import  total_ordering 

import  atexit
import  types
import  sys


#Frequency of monitoring thread in seconds
FREQUENCY   = 1

_THREAD     = None
_IS_ALIVE   = False
_ON_RELOAD  = {}
_MODULES    = {}
_EXCLUDE    = [
    '__main__'  ,
    __name__    ,
    'six.moves' ]

@total_ordering
class   SortableModule():
    def __init__(
        self    ,
        module  ,
        deps    ):
        self.module = module
        self.deps   = deps 
    def __eq__  (
        self, 
        o   ):
        return self.module == o.module
    def __gt__  (
        self,
        o   ):
        #If other depends on self
        return not (o.module in self.deps)
    def __hash__(
        self):
        return self.module

@stl.handle_exception(
    stl.Level.ERROR     ,
    log_params      = [],
    fall_back_value = [])
def _g_deps         (
    module  ):
    deps    = []
    for sys_module in list(sys.modules.values()):
        if      sys_module.__name__ in _EXCLUDE or  \
                sys_module == module                :
            continue
        for x in dir(sys_module)    :
            try                         :    
                val     = getattr(sys_module, x)
                if      type(val) == types.ModuleType           and \
                        val == module                               :
                    deps.append(sys_module)
                    break
                elif    hasattr(val, '__module__')              and \
                        sys.modules.get(val.__module__)== module    :
                    deps.append(sys_module)
                    break
            except ModuleNotFoundError  :
                pass

    return set(deps)      
def _reload         (
    modules ):
    r_modules   = {}
    s_modules   = list(modules)
    while s_modules :
        s_module            = s_modules.pop()
        if      s_module in r_modules   :
            continue
        deps                = _g_deps(s_module)
        r_modules[s_module] = SortableModule(s_module, deps)
        s_modules.extend(deps)
    
    for sorted_module in sorted(r_modules.values()):
        _reload_module(sorted_module.module)
def _reload_module  (
    module  ):
    if      module.__name__ in _EXCLUDE :
        return
    try                                 :
        reload(module)
    except                              :
        stl.MAIN_LOGGER.error(
                            {'Module failed to reload': '{} at {}'.format(module.__name__, module.__file__)})
        return
    else                                :
        stl.MAIN_LOGGER.info(
                            {'Module reloaded': '{} at {}'.format(module.__name__, module.__file__)})
    
    for action in _ON_RELOAD.get(module, []):
        action['action'](*action['args'], **action['kwargs'])
def _monitor        ():
    modules = {}
    while _IS_ALIVE  :
        new_modules = {}
        to_reload   = []
        for module in (_MODULES if _MODULES else list(sys.modules.values()))    :
            if      module.__name__ in _EXCLUDE                 :
                continue
            try                                                 :
                new_modules[module]   = getatime(module.__file__)
            except                                              :
                continue 
            if      not modules.get(module)                     :
                continue
            elif    modules.get(module) != new_modules[module]  :
                to_reload.append(module)
        _reload(set(to_reload))
        modules = new_modules
        sleep(FREQUENCY)
    stl.MAIN_LOGGER.info({'Autoreloader':    'Stopped'})

def register    (
    module):
    if      module not in _MODULES:
        _MODULES.append(module)
def on_reload   (
    module  , 
    action  ,
    *args   , 
    **kwargs):
    if      isinstance(module, str):
        module  = sys.modules[module]
    self._ON_RELOAD[module] = self._ON_RELOAD.get(module, [])
    self._ON_RELOAD[module].append(
        {
            'action': action,
            'args'  : args  ,
            'kwargs': kwargs,})
@atexit.register
def stop        ():
    global _IS_ALIVE
    _IS_ALIVE = False
def start       ():
    global _IS_ALIVE
    if      _IS_ALIVE:
        return
    _IS_ALIVE  = True
    global _THREAD
    _THREAD = Thread(target= _monitor, daemon= True)
    _THREAD.start()
    stl.MAIN_LOGGER.info({'Autoreloader':    'Started'})