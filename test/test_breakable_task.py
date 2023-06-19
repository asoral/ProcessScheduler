# Copyright (c) 2020-2021 Thomas Paviot (tpaviot@gmail.com)
#
# This file is part of ProcessScheduler.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import unittest

import processscheduler as ps
import processscheduler.context as ps_context


def new_problem_or_clear() -> None:
    """clear the current context. If no context is defined,
    create a SchedulingProject object"""
    if ps_context.main_context is None:
        ps.SchedulingProblem("NewProblem")
    else:
        ps_context.main_context.clear()


class TestBreakableTask(unittest.TestCase):
    def test_create_breakable_task_fixed_duration_1(self) -> None:
        pb = ps.SchedulingProblem("CreateBreakableFixedDurationTask1")

        task_1 = ps.BreakableFixedDurationTask("Task1", duration=3)
        pb.add_objective_makespan()
        solver = ps.SchedulingSolver(pb)

        solution = solver.solve()

        self.assertTrue(solution)

        self.assertTrue(solution.tasks[task_1.subtasks[0].name].duration == 1)
        self.assertTrue(solution.tasks[task_1.subtasks[1].name].duration == 1)
        self.assertTrue(solution.tasks[task_1.subtasks[2].name].duration == 1)
        self.assertTrue(solution.tasks[task_1.subtasks[0].name].start == 0)
        self.assertTrue(solution.tasks[task_1.subtasks[2].name].end == 3)

    def test_operator_carry_fixed_duration_representation(self) -> None:
        pb = ps.SchedulingProblem("OperatorCarryFixedRepresentation")

        task_1 = ps.FixedDurationTask("Carry", duration=6)
        operator_bob = ps.Worker("OperatorBob")
        lunch = ps.FixedDurationTask("Lunch", duration=1)

        lunch.add_required_resource(operator_bob)
        task_1.add_required_resource(operator_bob)
        ps.TaskStartAt(lunch, 4)  # lunch starts at 4, and ends at 5
        pb.add_objective_makespan()
        solver = ps.SchedulingSolver(pb)

        solution = solver.solve()

        self.assertTrue(solution)

        self.assertTrue(solution.tasks[lunch.name].start == 4)
        self.assertTrue(solution.tasks[lunch.name].end == 5)
        self.assertTrue(solution.tasks[task_1.name].start == 5)
        self.assertTrue(solution.tasks[task_1.name].end == 11)

    def test_operator_carry_breakable_fixed_duration_representation(self) -> None:
        """The same problem than before except the task is brealable"""
        pb = ps.SchedulingProblem("OperatorCarryBreakableFixedRepresentation")

        task_1 = ps.BreakableFixedDurationTask("Carry", duration=6)
        operator_bob = ps.Worker("OperatorBob")
        lunch = ps.FixedDurationTask("Lunch", duration=1)

        lunch.add_required_resource(operator_bob)
        task_1.add_required_resource(operator_bob)
        ps.TaskStartAt(lunch, 4)  # lunch starts at 4, and ends at 5
        pb.add_objective_makespan()
        solver = ps.SchedulingSolver(pb)

        solution = solver.solve()

        self.assertTrue(solution)

        self.assertTrue(solution.tasks[lunch.name].start == 4)
        self.assertTrue(solution.tasks[lunch.name].end == 5)
        self.assertTrue(solution.tasks[task_1.subtasks[0].name].start == 0)
        self.assertTrue(solution.tasks[task_1.subtasks[5].name].end == 7)

    # def test_create_task_variable_duration_from_list(self) -> None:
    #     pb = ps.SchedulingProblem("CreateVariableDurationTaskFromList")

    #     vdt_1 = ps.VariableDurationTask("vdt1", allowed_durations=[3, 4])
    #     vdt_2 = ps.VariableDurationTask("vdt2", allowed_durations=[5, 6])
    #     vdt_3 = ps.VariableDurationTask("vdt3", allowed_durations=[7, 8])

    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()

    #     self.assertTrue(solution)
    #     self.assertTrue(solution.tasks[vdt_1.name].duration in [3, 4])
    #     self.assertTrue(solution.tasks[vdt_2.name].duration in [5, 6])
    #     self.assertTrue(solution.tasks[vdt_3.name].duration in [7, 8])

    # #
    # # Single task constraints
    # #
    # def test_create_task_start_at(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     c = ps.TaskStartAt(task, 1)
    #     self.assertIsInstance(c, ps.TaskStartAt)
    #     self.assertEqual(c.value, 1)

    # def test_create_task_start_after_strict(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     c = ps.TaskStartAfterStrict(task, 3)
    #     self.assertIsInstance(c, ps.TaskStartAfterStrict)
    #     self.assertEqual(c.value, 3)

    # def test_create_task_start_after_lax(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     c = ps.TaskStartAfterLax(task, 3)
    #     self.assertIsInstance(c, ps.TaskStartAfterLax)
    #     self.assertEqual(c.value, 3)

    # def test_create_task_end_at(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     c = ps.TaskEndAt(task, 3)
    #     self.assertIsInstance(c, ps.TaskEndAt)
    #     self.assertEqual(c.value, 3)

    # def test_create_task_before_strict(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     c = ps.TaskEndBeforeStrict(task, 3)
    #     self.assertIsInstance(c, ps.TaskEndBeforeStrict)
    #     self.assertEqual(c.value, 3)

    # def test_create_task_before_lax(self) -> None:
    #     new_problem_or_clear()
    #     task = ps.FixedDurationTask("task", 2)
    #     constraint = ps.TaskEndBeforeLax(task, 3)
    #     self.assertIsInstance(constraint, ps.TaskEndBeforeLax)
    #     self.assertEqual(constraint.value, 3)

    # def test_task_duration_depend_on_start(self) -> None:
    #     pb = ps.SchedulingProblem("TaskDurationDependsOnStart", horizon=30)

    #     task_1 = ps.VariableDurationTask("Task1")
    #     task_2 = ps.VariableDurationTask("Task2")

    #     ps.TaskStartAt(task_1, 5)
    #     pb.add_constraint(task_1.duration == task_1.start * 3)

    #     ps.TaskStartAt(task_2, 11)
    #     pb.add_constraint(
    #         ps.if_then_else(
    #             task_2.start < 10, [task_2.duration == 3], [task_2.duration == 1]
    #         )
    #     )

    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(solution.tasks["Task1"].duration, 15)
    #     self.assertEqual(solution.tasks["Task2"].duration, 1)

    # #
    # # Two tasks constraints
    # #
    # def test_create_task_precedence_lax(self) -> None:
    #     new_problem_or_clear()
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     precedence_constraint = ps.TaskPrecedence(t_1, t_2, offset=1, kind="lax")
    #     self.assertIsInstance(precedence_constraint, ps.TaskPrecedence)

    # def test_create_task_precedence_tight(self) -> None:
    #     new_problem_or_clear()
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     precedence_constraint = ps.TaskPrecedence(t_1, t_2, offset=1, kind="tight")
    #     self.assertIsInstance(precedence_constraint, ps.TaskPrecedence)

    # def test_create_task_precedence_strict(self) -> None:
    #     pb = ps.SchedulingProblem("TaskPrecedenceStrict")
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     ps.TaskPrecedence(t_1, t_2, offset=1, kind="strict")
    #     pb.add_objective_makespan()
    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(
    #         solution.tasks[t_2.name].start, solution.tasks[t_1.name].end + 2
    #     )

    # def test_create_task_precedence_raise_exception_kind(self) -> None:
    #     new_problem_or_clear()
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     with self.assertRaises(ValueError):
    #         ps.TaskPrecedence(t_1, t_2, offset=1, kind="foo")

    # def test_create_task_precedence_raise_exception_offset_int(self) -> None:
    #     new_problem_or_clear()
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     with self.assertRaises(ValueError):
    #         ps.TaskPrecedence(t_1, t_2, offset=1.5, kind="lax")  # should be int

    # def test_tasks_dont_overlap(self) -> None:
    #     pb = ps.SchedulingProblem("TasksDontOverlap")
    #     t_1 = ps.FixedDurationTask("t1", duration=7)
    #     t_2 = ps.FixedDurationTask("t2", duration=11)
    #     ps.TasksDontOverlap(t_1, t_2)
    #     pb.add_objective_makespan()
    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(solution.horizon, 18)

    # def test_tasks_start_sync(self) -> None:
    #     pb = ps.SchedulingProblem("TasksStartSync")
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     ps.TaskStartAt(t_1, 7)
    #     ps.TasksStartSynced(t_1, t_2)
    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(solution.tasks[t_1.name].start, solution.tasks[t_2.name].start)

    # def test_tasks_end_sync(self) -> None:
    #     pb = ps.SchedulingProblem("TasksEndSync")
    #     t_1 = ps.FixedDurationTask("t1", duration=2)
    #     t_2 = ps.FixedDurationTask("t2", duration=3)
    #     ps.TasksEndSynced(t_1, t_2)
    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(solution.tasks[t_1.name].end, solution.tasks[t_2.name].end)

    # def test_schedule_n_task_raise_exception(self) -> None:
    #     new_problem_or_clear()
    #     with self.assertRaises(TypeError):
    #         ps.ScheduleNTasksInTimeIntervals(
    #             "list_of_tasks", 1, "list_of_time_intervals"
    #         )
    #     with self.assertRaises(TypeError):
    #         ps.ScheduleNTasksInTimeIntervals([], 1, "list_of_time_intervals")

    # #
    # # List of tasks constraints
    # #
    # def test_tasks_contiguous(self) -> None:
    #     pb = ps.SchedulingProblem("TasksContiguous")
    #     n = 7
    #     tasks_w1 = [ps.FixedDurationTask("t_w1_%i" % i, duration=3) for i in range(n)]
    #     tasks_w2 = [ps.FixedDurationTask("t_w2_%i" % i, duration=5) for i in range(n)]
    #     worker_1 = ps.Worker("Worker1")
    #     worker_2 = ps.Worker("Worker2")
    #     for t in tasks_w1:
    #         t.add_required_resource(worker_1)
    #     for t in tasks_w2:
    #         t.add_required_resource(worker_2)

    #     ps.TasksContiguous(tasks_w1 + tasks_w2)

    #     pb.add_objective_makespan()

    #     solver = ps.SchedulingSolver(pb)
    #     solution = solver.solve()
    #     self.assertTrue(solution)
    #     self.assertEqual(solution.horizon, 56)


if __name__ == "__main__":
    unittest.main()
