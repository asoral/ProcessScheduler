Task Constraints
================

ProcessScheduler provides a set of ready-to-use temporal task constraints. They allow expressing common rules such as "the task A must start exactly at the instant 4", "the task B must end at the same time than the task C ends", "the task C must be scheduled exactly 3 periods after the task D is completed" etc.

.. note::

    Naming convention: if the class name starts with *Task** then the constraint applies to one single task, if the class name starts with *Tasks** it applies to 2 or more task instances.

Time constraints
----------------
- :class:`TaskPrecedence`: takes two parameters :attr:`task_1` and :attr:`task_2` and constraints :attr:`task_2` to be scheduled after :attr:`task_1` is completed. The precedence type can either be :const:`'lax'` (default, :attr:`task_2.start` >= :attr:`task_1.end`)), :const:`'strict'` (:attr:`task_2.start` >= :attr:`task_1.end`)) or :const:`'tight'` (:attr:`task_2.start` >= :attr:`task_1.end`, task_2 starts immediately after task_1 is completed). An optional parameter :attr:`offset` can be additionally set.

.. code-block:: python

    task_1 = ps.FixedDurationTask('Task1', duration=3)
    task_2 = ps.FixedVariableTask('Task2')
    pc = TaskPrecedence(task1, task2, kind='tight', offset=2)

constraints the solver to schedule task_2 start exactly 2 periods after task_1 is completed.

- :class:`TasksStartSynced`: takes two parameters :attr:`task_1` and :attr:`task_2` such as the schedule must satisfy the constraint :math:`task_1.start = task_2.start`

.. image:: img/TasksStartSynced.svg
    :align: center
    :width: 90%

- :class:`TasksEndSynced`: takes two parameters :attr:`task_1` and :attr:`task_2` such as the schedule must satisfy the constraint :math:`task_1.end = task_2.end`

.. image:: img/TasksEndSynced.svg
    :align: center
    :width: 90%

- :class:`TasksDontOverlap`: takes two parameters :attr:`task_1` and :attr:`task_2` such as the task_1 ends before the task_2 is started or the opposite (task_2 ends before task_1 is started)

.. image:: img/TasksDontOverlap.svg
    :align: center
    :width: 90%

- :class:`TaskStartAt`: takes two parameters :attr:`task` and :attr:`value` such as the task starts exactly at the instant :math:`task.start = value`

- :class:`TaskStartAfterStrict`: the constraint  :math:`task.start > value`

- :class:`TaskStartAfterLax`: the constraint :math:`task.start >= value`

- :class:`TaskEndAt`: takes two parameters :attr:`task` and :attr:`value` such as the task ends exactly at the instant *value* :math:`task.end = value`

- :class:`TaskEndBeforeStrict`: the constraint :math:`task.end < value`

- :class:`TaskEndBeforeLax`: the constraint :math:`task.end <= value`

- :class:`TasksContiguous`: take a liste of tasks, force the schedule so that tasks are contiguous

- :class:`ScheduleNTasksInTimeIntervals`: given a set of :math:`m` different tasks, and a list of time intervals, schedule :math:`N` tasks among :math:`m` in this time interval.

- :class:`ResourceTasksDistance`: take a mandatory attribute :attr:`distance` (integer), an optional :attr:`time_periods` (list of couples of integers e.g. [[0, 1], [5, 19]]). All tasks, that use the given resource, scheduled within the :attr:`time_periods` must have a maximal distance of :attr:`distance` (distance being considered as the time between two consecutive tasks).

.. note::

    If the task(s) is (are) optional(s), all these constraints apply only if the task is scheduled. If the solver does not schedule the task, these constraints does not apply.
    

Optional tasks constraints
--------------------------

Following constraints apply to optional tasks only.

- :class:`OptionalTaskConditionSchedule` creates a constraint that adds a condition for the task to be scheduled. The condition is a z3 BoolRef

- the :class:`OptionalTasksDependency` takes two optional tasks :attr:`task_1` and :attr:`task_2`, and ensures that task_1 is schdeuld implies that task_2 is scheduled as well.

- the :class:`ForceScheduleNOptionalTasks` forces :math:`m` optional tasks among :math:`n` to be scheduled, with :math:`m \leq n`.


.. note::

    All the Task constraints may be defined as **optional**. This parameter is set to ``False`` by default, which means the task constraint is mandatory. If you set the attribute ``optional`` to ``True`` the the constraint becomes optional, and may/may not apply according to the solver. You can force the schedule to schedule an optional constraint:

    .. code:: python

        pb.add_constraint([task.applied == True])

