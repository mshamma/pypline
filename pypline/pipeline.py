from threading import Event, Thread


class ModifiableMixin(object):
    def add_task(self, task):
        self._tasks.append(task)

    def add_task_after(self, task, cls):
        try:
            index = next(i for (i, x) in enumerate(self._tasks)
                    if x.__class__ == cls)
        except StopIteration:
            raise ValueError("Class %s not found in pipeline."
                    % cls.__name__)
        self._tasks.insert(task, index + 1)

    def add_task_before(self, task, cls):
        try:
            index = next(i for (i, x) in enumerate(self._tasks)
                    if x.__class__ == cls)
        except StopIteration:
            raise ValueError("Class %s not found in pipeline."
                    % cls.__name__)
        self._tasks.insert(task, index)

    def remove_task(self, cls):
        while  True:
            try:
                self._tasks.remove(cls)
            except ValueError:
                break


class PipelineRunner(object):
    def __init__(self, tasks):
        super(PipelineRunner, self).__init__()
        self._tasks = tasks
        self._event = Event()

    def run(self, message):
        return self.execute(message, self._tasks)

    def execute(self, message, tasks):
        self.message = message
        for task in iter(tasks):
            if hasattr(task.__class__, "_async_flag"):
                task(self.message, self, self.resume)
                self._event.wait()
            else:
                self.message = task(self.message, self)
        return self.message

    def resume(self, message):
        self.message = message
        self._event.set()


class RepeatingPipelineRunner(PipelineRunner):
    def __init__(self, controller, initialisers,
                tasks, finalisers):
        super(RepeatingPipelineRunner, self).__init__(tasks)
        self._controller = controller
        self._initialisers = initialisers
        self._finalisers = finalisers

    def run(self, message):
        self.message = self.execute(message, self._initialisers)
        while not self._controller(self.message):
            self.message = self.execute(self.message, self._tasks)
        self.message = self.execute(self.message, self._finalisers)
        return self.message


class AsyncMixin(object):
    def execute(self, callback, message=None):
        def run_in_thread():
            result = super(AsyncMixin, self).execute(message)
            callback(result)
        Thread(run_in_thread).start()


class Pipeline(object):
    def __init__(self, tasks=[]):
        self._tasks = tasks[:]
        self._validate()

    def _validate(self):
        for task in self._tasks:
            if not callable(task):
                raise TypeError("Task: %s is not callable" % str(task))

    def execute(self, message=None):
        advancer = PipelineRunner(self._tasks)
        return advancer.run(message)


class RepeatingPipeline(Pipeline):
    def __init__(self, controller=None,
                initialisers=[], tasks=[], finalisers=[]):
        self._controller = controller
        self._initialisers = initialisers
        self._finalisers = finalisers
        Pipeline.__init__(self, tasks)

    def _validate(self):
        for task in self._initialisers + self._tasks + self._finalisers:
            if not callable(task):
                raise TypeError("Task: %s is not callable" % str(task))

    def execute(self, message=None):
        advancer = RepeatingPipelineRunner(self._controller, \
                    self._initialisers[:], self._tasks[:], \
                    self._finalisers[:])
        return advancer.run(message)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
