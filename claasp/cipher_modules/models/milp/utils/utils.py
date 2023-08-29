# ****************************************************************************
# Copyright 2023 Technology Innovation Institute
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ****************************************************************************

import re, os

from claasp.cipher_modules.models.milp.utils.generate_inequalities_for_xor_with_n_input_bits import (
    output_dictionary_that_contains_xor_inequalities,
    update_dictionary_that_contains_xor_inequalities_between_n_input_bits)

from claasp.cipher_modules.models.milp.utils.config import EXTERNAL_MILP_SOLVERS, MODEL_DEFAULT_PATH, \
    SOLUTION_FILE_DEFAULT_NAME
from sage.numerical.mip import MIPSolverException


def _write_model_to_lp_file(model, model_type):
    mip = model._model
    model_file_path = os.path.join(MODEL_DEFAULT_PATH, f"{model.cipher_id}_{model_type}.lp")
    mip.write_lp(model_file_path)

    return model_file_path


def _get_data(data_keywords, lines):
    data_line = re.search(data_keywords, lines, re.DOTALL)
    if data_line is None:
        raise MIPSolverException("Solver seems installed but license file might be missing.")
    data = float(re.findall(data_keywords, data_line.group(0))[0])
    return data


def _get_variables_value(internal_variables, read_file):
    variables_value = {}
    for key in internal_variables.keys():
        index = int(re.search(r'\d+', str(internal_variables[key])).group()) + 1
        match = re.search(r'[xyz]_%s[\s]+[\*]?[\s]*([0-9]*[.]?[0-9]+)' % index, read_file)
        variables_value[key] = float(match.group(1)) if match else 0.0
    return variables_value


def _parse_external_solver_output(model, model_type, solver_name, solver_process):
    solver_specs = EXTERNAL_MILP_SOLVERS[solver_name]

    solve_time = _get_data(solver_specs['time'], str(solver_process))

    probability_variables = {}
    components_variables = {}
    status = 'UNSATISFIABLE'
    total_weight = None

    if solver_specs['unsat_condition'] not in str(solver_process):
        status = 'SATISFIABLE'

        solution_file_path = os.path.join(MODEL_DEFAULT_PATH, SOLUTION_FILE_DEFAULT_NAME)

        with open(solution_file_path, 'r') as lp_file:
            read_file = lp_file.read()

        components_variables = _get_variables_value(model.binary_variable, read_file)
        probability_variables = _get_variables_value(model.integer_variable, read_file)

        if "deterministic_truncated_xor_differential" not in model_type:
            total_weight = probability_variables["probability"] / 10.
        else:
            total_weight = probability_variables["probability"]

    return status, total_weight, probability_variables, components_variables, solve_time


def milp_less(model, a, b, bigM):
    """
    Returns constraints to determine whether a < b, where 'a' is an integer variables and 'b' is an integer variable or a constant.
    The binary variable a_less_b = 1 iff a < b

    EXAMPLES::

        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: x = M._integer_variable; d = M._binary_variable
        sage: mip.set_max(x,2); mip.set_min(x,0)
        sage: a = x[0]; b = x[1]; bigM = 4
        sage: dummy, constraints = M.milp_less(M, a, b, bigM)
        sage: for i in constraints:
        ....:     mip.add_constraint(i)
        ...
    """
    d = model.binary_variable
    a_less_b = d[str(a) + "_less_" + str(b) + "_dummy"]
    constraints = [a <= b - 1 + bigM * (1 - a_less_b),
                   a >= b - bigM * a_less_b]

    return a_less_b, constraints


def milp_leq(model, a, b, bigM):
    """
    Returns constraints to determine whether a <= b, where a and b are integer variables or constants.
    The binary variable a_leq_b = 1 iff a <= b
    """

    return milp_less(model, a, b + 1, bigM)


def milp_greater(model, a, b, bigM):
    """
    Returns constraints to determine whether a > b, where a and b are integer variables or constants.
    The binary variable a_greater_b = 1 iff a > b
    """

    return milp_less(model, b, a, bigM)


def milp_geq(model, a, b, bigM):
    """
    Returns constraints to determine whether a >= b, where a and b are integer variables or constants.
    The binary variable a_geq_b = 1 iff a >= b
    """

    return milp_less(model, b, a + 1, bigM)


def milp_and(model, a, b):
    """
    Returns constraints to model a and b, where a and b are binary variables.
    The binary variable a_and_b = 1 iff a == 1 and b == 1

    """
    d = model.binary_variable
    a_and_b = d[str(a) + "_and_" + str(b) + "_dummy"]

    constraint = [a + b - 1 <= a_and_b,
                  a_and_b <= a,
                  a_and_b <= b]

    return a_and_b, constraint


def milp_or(model, a, b):
    """
    Returns constraints to model a or b, where a and b are binary variables.
    The binary variable a_or_b = 1 iff a == 1 or b == 1

    """
    d = model.binary_variable
    a_or_b = d[str(a) + "_or_" + str(b) + "_dummy"]

    constraint = [a + b >= a_or_b,
                  a_or_b >= a,
                  a_or_b >= b]

    return a_or_b, constraint


def milp_generalized_and(model, var_list):
    """
    Returns constraints to model a_0 and a_1 and ... a_n-1, where a_i's are binary variables in var_list.
    The binary variable generalized_and = 1 iff a_i == 1 for all i.

    EXAMPLES::

        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: d = M._binary_variable
        sage: var_list = [d[i] for i in range(4)]
        sage: general_and, constraints = M.milp_generalized_and(var_list)
        sage: for i in constraints:
        ....:     mip.add_constraint(i)
        ...

    """
    d = model.binary_variable

    generalized_and_varname = ''
    for i in range(len(var_list)):
        generalized_and_varname += str(var_list[i]) + '{}'.format('_and_' if i < len(var_list) - 1 else '_dummy')

    generalized_and = d[generalized_and_varname]
    constraint = [sum(var_list) - len(var_list) + 1 <= generalized_and]
    for var in var_list:
        constraint.append(generalized_and <= var)

    return generalized_and, constraint


def milp_eq(model, a, b, bigM):
    """
    Returns constraints to determine whether a == b, where b is a constant.
    The binary variable a_eq_b = 1 iff a == b

    EXAMPLES::

        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: x = M._integer_variable; d = M._binary_variable
        sage: a = x[0]; b = 2; bigM = 4
        sage: dummy, constraints = M.milp_eq(M, a, b, bigM)
        sage: for i in constraints:
        ....:     mip.add_constraint(i)
        ...
    """
    constraints = []

    d_leq, c_leq = milp_leq(model, a, b, bigM)
    d_geq, c_geq = milp_geq(model, a, b, bigM)
    constraints += c_leq + c_geq

    a_eq_b, constraint = milp_and(model, d_leq, d_geq)
    constraints += constraint

    return a_eq_b, constraints


def milp_neq(model, a, b, bigM):
    """
    Returns constraints to determine whether a != b, where b is a constant.
    The binary variable a_neq_b = 1 iff a != b

    EXAMPLES::

        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: x = M._integer_variable; d = M._binary_variable
        sage: a = x[0]; b = 2; bigM = 4
        sage: dummy, constraints = M.milp_neq(M, a, b, bigM)
        sage: for i in constraints:
        ....:     mip.add_constraint(i)
    """
    constraints = []

    d_less, c_less = milp_less(model, a, b, bigM)
    d_greater, c_greater = milp_greater(model, a, b, bigM)
    constraints += c_less + c_greater

    a_neq_b, constraint = milp_or(model, d_less, d_greater)
    constraints += constraint

    return a_neq_b, constraints


def milp_xor(a, b, c):
    """
    Returns constraints to model a xor b = c for binary variables

    EXAMPLES::

        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: x = M._binary_variable
        sage: a = x[0]; b = x[1]; c = x[2]
        sage: for i in M.milp_xor(M,a,b,c):
        ....:     mip.add_constraint(i)
        ...
    """
    constraints = [a + b >= c,
                   a + c >= b,
                   b + c >= a,
                   a + b + c <= 2]

    return constraints


def milp_generalized_xor(input_var_list, output_bit):
    """
    Returns constraints to model a_0 xor a_1 xor ... xor a_{n-1} = output_bit for binary variables

    EXAMPLES::

        sage: from claasp.cipher_modules.models.milp.utils import utils
        sage: from claasp.ciphers.block_ciphers.simon_block_cipher import SimonBlockCipher
        sage: cipher = SimonBlockCipher(block_bit_size=32, key_bit_size=64, number_of_rounds=2)
        sage: from claasp.cipher_modules.models.milp.milp_model import MilpModel
        sage: M = MilpModel(cipher)
        sage: M.init_model_in_sage_milp_class()
        sage: mip = M._model
        sage: x = M._binary_variable
        sage: var_list = [x[i] for i in range(2)]; b = x[2]
        sage: for i in utils.milp_generalized_xor(M, var_list, b):
        ....:     mip.add_constraint(i)
        ...
    """
    constraints = []
    number_of_inputs = len(input_var_list)

    update_dictionary_that_contains_xor_inequalities_between_n_input_bits(number_of_inputs)
    dict_inequalities = output_dictionary_that_contains_xor_inequalities()
    inequalities = dict_inequalities[number_of_inputs]

    for ineq in inequalities:
        constraint = 0
        for var in range(number_of_inputs):
            char = ineq[var]
            if char == "1":
                constraint += 1 - input_var_list[var]
            elif char == "0":
                constraint += input_var_list[var]
            else:
                continue
        last_char = ineq[number_of_inputs]
        if last_char == "1":
            constraint += 1 - output_bit
        elif last_char == "0":
            constraint += output_bit
        else:
            continue
        constraints.append(constraint >= 1)

    return constraints


def milp_if_then(var_if, then_constraints, bigM):
    """
    Returns a list of variables and a list of constraints to model an if-then statement.
    When the binary variable var_if == 1, the set 'then_constraints' is applied.
    """

    constraints = []
    for constr in then_constraints:
        if constr.is_less_or_equal():
            for lhs, rhs in constr.inequalities():
                constraints.append(lhs <= rhs + bigM * (1 - var_if))
        else:
            for lhs, rhs in constr.equations():
                constraints.append(lhs <= rhs + bigM * (1 - var_if))
                constraints.append(rhs <= lhs + bigM * (1 - var_if))

    return constraints


def milp_if_then_else(var_if, then_constraints, else_constraints, bigM):
    """
    Returns a list of variables and a list of constraints to model an if-then-else statement.
    When the binary variable var_if == 1, the set 'then_constraints' is applied,
    when var_if == 0, the set 'else_constraints' is applied
    """

    constraints = milp_if_then(var_if, then_constraints, bigM)

    for constr in else_constraints:
        if constr.is_less_or_equal():
            for lhs, rhs in constr.inequalities():
                constraints.append(lhs <= rhs + bigM * var_if)
        else:
            for lhs, rhs in constr.equations():
                constraints.append(lhs <= rhs + bigM * var_if)
                constraints.append(rhs <= lhs + bigM * var_if)

    return constraints


def milp_if_elif_else(model, var_if_list, then_constraints_list, else_constraints, bigM):
    """
    Returns a list of variables and a list of constraints to model an if-elif...-elif-else statement.
    When the binary variable var_if[i] == 1, the set 'then_constraints[i]' is applied,
    when all var_if variables are 0, the set 'else_constraints' is applied

    https://stackoverflow.com/questions/41009196/if-then-elseif-then-in-mixed-integer-linear-programming
    """

    assert (len(var_if_list) == len(then_constraints_list))
    constraints = []
    num_cond = len(var_if_list)

    if num_cond == 1:
        return milp_if_then_else(var_if_list[0], then_constraints_list[0], else_constraints, bigM)

    else:
        d = model.binary_variable
        decision_varname = ''
        for i in range(num_cond):
            decision_varname += str(var_if_list[i]) + '{}'.format('_and_' if i < num_cond - 1 else '_dummy')

        decision_var = [d[decision_varname + '_' + str(i)] for i in range(num_cond)]

        for i in range(num_cond):
            decision_constraints = 0
            # for j in range(num_cond):
            #     if j == i:
            #         decision_constraints += var_if_list[j]
            #     else:
            #         decision_constraints += 1 - var_if_list[j]
            for j in range(i + 1):
                if j == i:
                    decision_constraints += var_if_list[j]
                else:
                    decision_constraints += 1 - var_if_list[j]
            constraints.append(decision_constraints <= decision_var[i] + num_cond - 1)
            constraints.append(1. / num_cond * decision_constraints >= decision_var[i])

            for constr in then_constraints_list[i]:
                if constr.is_less_or_equal():
                    for lhs, rhs in constr.inequalities():
                        constraints.append(lhs <= rhs + bigM * (1 - decision_var[i]))
                else:
                    for lhs, rhs in constr.equations():
                        constraints.append(lhs <= rhs + bigM * (1 - decision_var[i]))
                        constraints.append(rhs <= lhs + bigM * (1 - decision_var[i]))

        for constr in else_constraints:
            if constr.is_less_or_equal():
                for lhs, rhs in constr.inequalities():
                    constraints.append(lhs <= rhs + bigM * sum(decision_var))
            else:
                for lhs, rhs in constr.equations():
                    constraints.append(lhs <= rhs + bigM * sum(decision_var))
                    constraints.append(rhs <= lhs + bigM * sum(decision_var))

        return constraints

def milp_xor_truncated(model, input_1, input_2, output):
    """
    Returns a list of variables and a list of constraints for the XOR for two input bits
    in the deterministic truncated XOR differential model.

    This method uses a binary encoding (where each variable v is seen as a binary tuple (v0, v1), where v0 is the MSB) to
    model the result c of the truncated XOR between inputs a and b.

    _______________
     a  |  b  |  c
    _______________
     0  |  0  |  0
     0  |  1  |  1
     0  |  2  |  2
     1  |  0  |  1
     1  |  1  |  0
     1  |  2  |  2
     2  |  0  |  2
     2  |  1  |  2
     2  |  2  |  2
    _______________

    Espresso was used to reduce the number of constraints to 10 inequalities.
    """

    x = model.binary_variable
    espresso_inequalities = ['-1-000', '-0-100', '----11', '0-0-1-', '-0-0-1',
                             '-1-1-1', '11----', '--1-0-', '1---0-', '--11--']

    constraints = []
    all_vars = [x[i] for i in input_1 + input_2 + output]

    for ineq in espresso_inequalities:
        constraint = 0
        for pos, char in enumerate(ineq):
            if char == "1":
                constraint += 1 - all_vars[pos]
            elif char == "0":
                constraint += all_vars[pos]
        constraints.append(constraint >= 1)

    return constraints

def milp_xor_truncated_wordwise(model, input_1, input_2, output):
    """
    Returns a list of variables and a list of constraints for the XOR for two input words
    in deterministic truncated XOR differential model.

    This method uses a binary encoding (where each variable v is seen as a binary tuple (v0, v1), where v0 is the MSB) to
    model the result c of the truncated XOR between inputs a and b.

    _______________
     a  |  b  |  c
    _______________
     0  |  0  |  0
     0  |  1  |  1
     0  |  2  |  2
     0  |  3  |  3
     1  |  0  |  1
     1  |  1  |  0
     1  |  1  |  1
     1  |  2  |  3
     1  |  3  |  3
     2  |  0  |  2
     2  |  1  |  3
     2  |  2  |  3
     2  |  3  |  3
     3  |  0  |  3
     3  |  1  |  3
     3  |  2  |  3
     3  |  3  |  3
    _______________


    Espresso was used to reduce the number of constraints to 91 inequalities.
    """

    x = model.binary_variable

    espresso_inequalities = ['0-00000000-0---------1--------', '-0--------0-00000000-1--------',
                             '-1----------00000000-0--------', '--00000000-1---------0--------',
                             '---------------------01-------', '--------------------0100000000',
                             '---------------------0-1------', '--------------------1-1-------',
                             '---------------------0--1-----', '--------------------1--1------',
                             '---------------------0---1----', '--------------------1---1-----',
                             '---------------------0----1---', '--------------------1----1----',
                             '---------------------0-----1--', '--1---------0-------0-0-------',
                             '--0---------1-------0-0-------', '---------------------0------1-',
                             '---1---------0------0--0------', '---0---------1------0--0------',
                             '----1---------0-----0---0-----', '----0---------1-----0---0-----',
                             '--------------------1-----1---', '-----1---------0----0----0----',
                             '-----0---------1----0----0----', '------1---------0---0-----0---',
                             '------0---------1---0-----0---', '-------1---------0--0------0--',
                             '-------0---------1--0------0--', '--------1---------0-0-------0-',
                             '--------0---------1-0-------0-', '---------1---------00--------0',
                             '---------0---------10--------0', '---------------------0-------1',
                             '--------------------1------1--', '--------------------1-------1-',
                             '--------------------1--------1', '0100000000--------------------',
                             '----------0100000000----------', '---------0---------0---------1',
                             '---------1---------1---------1', '1---------1----------0--------',
                             '0---------0---------1---------', '-------0---------0---------1--',
                             '------0---------0---------1---', '-----0---------0---------1----',
                             '----0---------0---------1-----', '---0---------0---------1------',
                             '--0---------0---------1-------', '--------0---------0---------1-',
                             '--------1---------1---------1-', '--1---------1---------1-------',
                             '------1---------1---------1---', '-----1---------1---------1----',
                             '----1---------1---------1-----', '---1---------1---------1------',
                             '-------1---------1---------1--', '----------1---------0---------',
                             '1-------------------0---------', '-----------0------1-----------',
                             '----------1-------1-----------', '-----------01-----------------',
                             '----------1-1-----------------', '-----------0----1-------------',
                             '----------1-----1-------------', '-----------0---1--------------',
                             '----------1----1--------------', '-----------0--1---------------',
                             '----------1---1---------------', '-----------0-1----------------',
                             '----------1--1----------------', '-0------1---------------------',
                             '-0-----1----------------------', '-0----1-----------------------',
                             '-0---1------------------------', '-0--1-------------------------',
                             '-0-1--------------------------', '-01---------------------------',
                             '-----------0-----1------------', '----------1------1------------',
                             '1-------1---------------------', '1------1----------------------',
                             '1-----1-----------------------', '1----1------------------------',
                             '1---1-------------------------', '1--1--------------------------',
                             '1-1---------------------------', '-----------0-------1----------',
                             '----------1--------1----------', '-0-------1--------------------',
                             '1--------1--------------------']


    constraints = []
    all_vars = [x[i] for i in input_1 + input_2 + output]

    for ineq in espresso_inequalities:
        constraint = 0
        for pos, char in enumerate(ineq):
            if char == "1":
                constraint += 1 - all_vars[pos]
            elif char == "0":
                constraint += all_vars[pos]
        constraints.append(constraint >= 1)

    return constraints
