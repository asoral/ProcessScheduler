"""Solver definition and related classes/functions."""

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

import multiprocessing
import random
import time
from typing import Optional
import uuid
import warnings

from z3 import (Solver, SolverFor, Sum, unsat, sat,
                ArithRef, unknown, Optimize, set_option,
                Xor, Distinct)

from processscheduler.task import VariableDurationTask
from processscheduler.objective import MaximizeObjective, MinimizeObjective
from processscheduler.solution import SchedulingSolution, TaskSolution, ResourceSolution

#
# Solver class definition
#
class SchedulingSolver:
    """ A solver class """
    def __init__(self, problem,
                 debug: Optional[bool] = False,
                 max_time: Optional[int] = 10,
                 optimize_priority = 'lex',
                 parallel: Optional[bool] = False,
                 random_seed = False,
                 logics="QF_IDL"):
        """ Scheduling Solver

        debug: True or False, False by default
        max_time: time in seconds, 60 by default
        optimize_priority: one of 'lex', 'box', 'pareto'
        parallel: True to enable mutlthreading, False by default
        """
        self._problem = problem
        self.problem_context = problem.context
        self.debug = debug
        # objectives list
        self.optimize_priority = optimize_priority
        self.objectives = []  # the list of all objectives defined in this problem

        if debug:
            set_option("verbose", 2)

        if random_seed:
            set_option('sat.random_seed', random.randint(1, 1e4))
            set_option('smt.random_seed', random.randint(1, 1e4))
        else:
            set_option('sat.random_seed', 0)
            set_option('smt.random_seed', 0)

        # set timeout
        self.max_time = max_time  # in seconds
        set_option("timeout", int(self.max_time * 1000))  # in milliseconds

        # create the solver
        print('Solver type:\n===========')

        # check if the problem is an optimization problem
        self.is_not_optimization_problem = len(self.problem_context.objectives) == 0
        self.is_multi_objective_optimization_problem = len(self.problem_context.objectives) > 1
        self.is_single_objective_optimization_problem = len(self.problem_context.objectives) == 1

        # the Optimize() solver is used only in the case of a mutli-optimization
        # problem. This enables to choose the priority method.
        # in the case of a single objective optimization, the Optimize() solver
        # apperas to be less robust than the basic Solver(). The
        # incremental solver is then used.
        if self.is_multi_objective_optimization_problem:
            self._solver = Optimize()  # Solver with optimization
            self._solver.set(priority=self.optimize_priority)
            print("\t-> Solver with optimization enabled")
        else:
            # see this url for a documentation about logics
            # http://smtlib.cs.uiowa.edu/logics.shtml
            if logics is None:
                self._solver = Solver()
                print("\t-> Standard SAT/SMT solver")
            else:
                # the default logics should be QF_IDL, the fastest
                # Before that, we check if ever there are cost functions
                # indeed cost functions involve Real numbers ad cannot be handled by
                # the QF_IDL (Integer Difference Logics), we have to choose QF_LIRA
                if self._problem.has_cost_function():
                    self._solver = SolverFor("QF_LIRA")
                else:
                    self._solver = SolverFor(logics)
                print("\t-> SMT solver using logics", logics)
            if debug:
                set_option(unsat_core=True)

        if parallel:
            set_option("parallel.enable", True)  # enable parallel computation
            n_cpus = multiprocessing.cpu_count()
            set_option("sat.threads", n_cpus)  # enable parallel computation
            set_option("smt.threads", n_cpus)  # enable parallel computation

        # add all tasks assertions to the solver
        for task in self.problem_context.tasks:
            self.add_constraint(task.get_assertions())
            self.add_constraint(task.end <= self._problem.horizon)

        # then process tasks constraints
        for constraint in self.problem_context.constraints:
            self.add_constraint(constraint)

        # process resources requirements
        for ress in self.problem_context.resources:
            self.add_constraint(ress.get_assertions())

        # process resource intervals
        # First, we check all tasks to find if ever one of them
        # is a VariableDurationTask. In this case, we have to
        # use the brute force Xor for the non overlapping constraint.
        # in the other case, the Distinc constraint over start times is
        # enough
        problem_has_variable_duration_task = False
        for task in self.problem_context.tasks:
            if isinstance(task, VariableDurationTask):
                problem_has_variable_duration_task = True
                break
        if problem_has_variable_duration_task:
            overlap_mode = 'brute_xor'
        else:
            overlap_mode = 'distinct'
        # then process the non overlap constraints
        for ress in self.problem_context.resources:
            busy_intervals = ress.get_busy_intervals()
            nb_intervals = len(busy_intervals)
            if overlap_mode == 'brute_xor':  # brute force Xor, works in any case
                for i in range(nb_intervals):
                    start_task_i, end_task_i = busy_intervals[i]
                    for k in range(i + 1, nb_intervals):
                        start_task_k, end_task_k = busy_intervals[k]
                        self.add_constraint(Xor(start_task_k >= end_task_i, start_task_i >= end_task_k))
            # other algorithm, better for task durations that are not big
            elif overlap_mode == 'distinct':
                all_starts = []
                for task in ress.busy_intervals:  # look over tasks
                    start_task_i, end_task_i = ress.busy_intervals[task]
                    for idx in range(task.duration):
                        all_starts.append(start_task_i + idx)
                # add the constraint that tells they are distinct
                self.add_constraint(Distinct(all_starts))

        # process indicators
        for indic in self.problem_context.indicators:
            self.add_constraint(indic.get_assertions())

        self.process_work_amount()

        if self.is_multi_objective_optimization_problem:
            self.create_objectives()

        # each time the solver is called, the current_solution is stored
        self.current_solution = None

    def add_constraint(self, cstr) -> bool:
        # set the method to use to add constraints
        # in debug mode this is assert_and_track, to be able to trace
        # unsat core, in regular mode this is the add function
        if self.debug:
            if isinstance(cstr, list):
                for c in cstr:
                    self._solver.assert_and_track(c, 'asst_%s' % uuid.uuid4().hex[:8])
            else:
                self._solver.assert_and_track(cstr, 'asst_%s' % uuid.uuid4().hex[:8])
        else:
            self._solver.add(cstr)

    def create_objectives(self) -> None:
        """ create optimization objectives """
        # in case of a single value to optimize
        for obj in self.problem_context.objectives:
            if isinstance(obj, MaximizeObjective):
                # look for the minimum horizon, i.e. the shortest
                # time horizon to complete all tasks
                new_max = self._solver.maximize(obj.target)
                self.objectives.append(['%s(max objective)' % obj.target, new_max])
            elif isinstance(obj, MinimizeObjective):
                new_min = self._solver.minimize(obj.target)
                self.objectives.append(['%s(min objective)' % obj.target, new_min])

    def process_work_amount(self) -> None:
        """ for each task, compute the total work for all required resources """
        for task in self.problem_context.tasks:
            if task.work_amount > 0.:
                work_total_for_all_resources = []
                for required_resource in task.required_resources:
                    # work contribution for the resource
                    interv_low, interv_up = required_resource.busy_intervals[task]
                    work_contribution = required_resource.productivity * (interv_up - interv_low)
                    work_total_for_all_resources.append(work_contribution)
                self.add_constraint(Sum(work_total_for_all_resources) >= task.work_amount)

    def check_sat(self):
        """ check satisfiability. Returns resulta as True (sat) or False (unsat, unknown).
        The computation time.
        """
        init_time = time.perf_counter()
        sat_result  = self._solver.check()
        check_sat_time = time.perf_counter() - init_time
        return sat_result, check_sat_time

    def build_solution(self, z3_sol):
        """create and return a SchedulingSolution instance"""
        solution = SchedulingSolution(self._problem)

        # set the horizon solution
        solution.horizon = z3_sol[self._problem.horizon].as_long()

        # process tasks
        for task in self._problem.context.tasks:
            # for each task, create a TaskSolution instance
            new_task_solution = TaskSolution(task.name)
            new_task_solution.type = type(task).__name__
            new_task_solution.start = z3_sol[task.start].as_long()
            new_task_solution.end = z3_sol[task.end].as_long()
            if isinstance(task.duration, int):  # a FixedDurationTask
                new_task_solution.duration = task.duration
            else:
                new_task_solution.duration = z3_sol[task.duration].as_long()
            new_task_solution.optional = task.optional

            # times, if ever delta_time and start_time are defined
            if self._problem.delta_time is not None:
                new_task_solution.duration_time = new_task_solution.duration * self._problem.delta_time
                if self._problem.start_time is not None:
                    new_task_solution.start_time = self._problem.start_time + new_task_solution.start * self._problem.delta_time
                    new_task_solution.end_time = new_task_solution.start_time + new_task_solution.duration_time
                else:
                    new_task_solution.start_time = new_task_solution.start * self._problem.delta_time
                    new_task_solution.end_time = new_task_solution.start_time + new_task_solution.duration_time

            if task.optional:
                # ugly hack, necessary because there's no as_bool()
                # method for Bool objects
                new_task_solution.scheduled = ("%s" % z3_sol[task.scheduled] == 'True')
            else:
                new_task_solution.scheduled = True

            # process resource assignments
            for req_res in task.required_resources:
                # by default, resource_should_be_assigned is set to True
                # if will be set to False if the resource is an alternative worker
                resource_is_assigned = True
                # among those workers, some of them
                # are busy "in the past", that is to say they
                # should not be assigned to the related task
                # for each interval
                lower_bound, _ = req_res.busy_intervals[task]
                if z3_sol[lower_bound].as_long() < 0:
                    # should not be scheduled
                    resource_is_assigned = False
                # add this resource to assigned resources, anytime
                if resource_is_assigned and (req_res.name not in new_task_solution.assigned_resources):
                    # if it is a cumulative resource, then we transform the resource name
                    resource_name = req_res.name.split('_CumulativeWorker_')[0]
                    if resource_name not in new_task_solution.assigned_resources:
                        new_task_solution.assigned_resources.append(resource_name)

            solution.add_task_solution(new_task_solution)

        # process resources
        for resource in self._problem.context.resources:
            # for each task, create a TaskSolution instance
            # for cumulative workers, we append the current work
            if '_CumulativeWorker_' in resource.name:
                cumulative_worker_name = resource.name.split('_CumulativeWorker_')[0]
                if cumulative_worker_name not in solution.resources:
                    new_resource_solution = ResourceSolution(cumulative_worker_name)
                else:
                    new_resource_solution = solution.resources[cumulative_worker_name]
            else:
                new_resource_solution = ResourceSolution(resource.name)
            new_resource_solution.type = type(resource).__name__
            # check for task processed by this resource
            for task in resource.busy_intervals.keys():
                task_name = task.name
                st_var, end_var = resource.busy_intervals[task]
                start = z3_sol[st_var].as_long()
                end = z3_sol[end_var].as_long()
                if start >= 0 and end >= 0 and (task_name, start, end) not in new_resource_solution.assignments:
                    new_resource_solution.assignments.append((task_name, start, end))

            if '_CumulativeWorker_' in resource.name:
                cumulative_worker_name = resource.name.split('_CumulativeWorker_')[0]
                if cumulative_worker_name not in solution.resources:
                    solution.add_resource_solution(new_resource_solution)
            else:
                solution.add_resource_solution(new_resource_solution)

        # process indicators
        for indicator in self._problem.context.indicators:
            indicator_name = indicator.name
            indicator_value = z3_sol[indicator.indicator_variable].as_long()
            solution.add_indicator_solution(indicator_name, indicator_value)

        return solution

    def solve(self) -> bool:
        """ call the solver and returns the solution, if ever """
        # for all cases
        if self.debug:
            self.print_assertions()

        if self.is_single_objective_optimization_problem:
            # in this case, use the incremental solver
            objective = self.problem_context.objectives[0]
            if isinstance(objective, MinimizeObjective):
                dd = 'min'
            elif isinstance(objective, MaximizeObjective):
                dd = 'max'
            # print(dir(objective))
            # print(objective.target)
            solution = self.solve_optimize_incremental(objective.target, kind=dd)
            if not solution:
                #raise ('No Solution')
                return False
        else:
            # first check satisfiability
            sat_result, sat_computation_time = self.check_sat()
            if self.is_multi_objective_optimization_problem:
                print('\tObjectives:\n\t======')
                for obj in self._solver.objectives():
                    print('\t', obj)

            print('Total computation time:\n=====================')
            print('\t%s satisfiability checked in %.2fs' % (self._problem.name, sat_computation_time))

            if sat_result == unsat:
                print("SAT result:\n===========")
                print("\tNo solution exists for problem %s." % self._problem.name)
                if self.debug:
                    unsat_core = self._solver.unsat_core()
                    print('\t%i unsatisfied assertion(s) (probable conflict):' % len(unsat_core))
                    for c in unsat_core:
                        print('\t->%s' % c)
                return False

            if sat_result == unknown:
                reason = self._solver.reason_unknown()
                print("\tNo solution can be found for problem %s because: %s" % (self._problem.name,
                                                                                 reason))
                return False

            # then get the solution
            solution = self._solver.model()

            if self.objectives:
                print('Optimization results:\n=====================')
                print('\t->Objective priority specification: %s' % self.optimize_priority)
                print('\t->Objective values:')
                for objective_name, objective_value in self.objectives:  # if ever no objectives, this line will do nothing
                    print('\t\t->%s: %s' % (objective_name, objective_value.value()))

        self.current_solution = solution
        sol = self.build_solution(solution)

        if self.debug:
            self.print_statistics()
            self.print_solution()

        return sol

    def solve_optimize_incremental(self,
                                   variable: ArithRef,
                                   max_recursion_depth=None,
                                   kind='min') -> int:
        """ target a min or max for a variable, without the Optimize solver.
        The loop continues ever and ever until the next value is more than 90%"""
        if kind not in ['min', 'max']:
            raise ValueError("choose either 'min' or 'max'")
        depth = 0
        solution = False
        total_time = 0
        print('Incremental optimizer:\n============================')

        while True:  # infinite loop, break if unsat of max_depth
            depth += 1
            if max_recursion_depth is not None:
                if depth > max_recursion_depth:
                    warnings.warn('maximum recursion depth exceeded. There might be a better solution.')
                    break

            is_sat, sat_computation_time = self.check_sat()
            if is_sat != sat:
                break
            solution = self._solver.model()
            total_time += sat_computation_time
            if total_time > self.max_time:
                warnings.warn('max time exceeded')
                break
            current_variable_value = solution[variable].as_long()
            print(f'\tvalue:{current_variable_value}, elapsed time(s):{total_time}')
            self._solver.push()
            if kind == 'min':
                self.add_constraint(variable < current_variable_value)
            else:
                self.add_constraint(variable > current_variable_value)
        if not solution:
            return False

        print('\ttotal number of iterations: %i' % depth)
        print('\tvalue: %i' %current_variable_value)
        print('\t%s satisfiability checked in %.2fs' % (self._problem.name, total_time))

        return solution

    def print_assertions(self):
        """A utility method to display solver assertions"""
        print('Assertions:\n===========')
        for assertion in self._solver.assertions():
            print('\t->', assertion)

    def print_statistics(self):
        """A utility method that displays solver statistics"""
        print('Solver satistics:')
        for key, value in self._solver.statistics():
            print('\t%s: %s' % (key, value))

    def print_solution(self):
        """A utility method that displays all internal variables for the current solution"""
        print('Solution:')
        for decl in self.current_solution.decls():
            var_name = decl.name()
            var_value = self.current_solution[decl]
            print("\t-> %s=%s" %(var_name, var_value))

    def find_another_solution(self, variable: ArithRef) -> bool:
        """ let the solver find another solution for the variable """
        if self.current_solution is None:
            warnings.warn('No current solution. First call the solve() method.')
            return False
        current_variable_value = self.current_solution[variable].as_long()
        self.add_constraint(variable != current_variable_value)
        return self.solve()

    def export_to_smt2(self, smt_filename):
        """ export the model to a smt file to be processed by another SMT solver """
        with open(smt_filename, 'w') as outfile:
            outfile.write(self._solver.to_smt2())
